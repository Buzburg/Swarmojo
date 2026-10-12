"""Model-independent execution boundary with exact approvals and confined commands.

Reuses Aeon's bounded file tools; mutations require an operator-approved receipt.
Commands run only when the platform supplies the configured OS sandbox.
"""
from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import sys

from aeon.tools import Tools, validate_action
from app.engines import RewindEngine, PathAuditResult, audit_filename, HorizonManager, compact_text
from app.control_store import ControlStore, digest
from app.meta.processes import run_command


class ExecutionEnvironment:
    def __init__(self, config, *, state_dir=None, scope='default'):
        self.config = config
        self.root_path = Path(config.root_path).resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)
        self.tools = Tools(self.root_path)
        self.store = ControlStore(self.root_path, state_dir)
        self.scope = scope
        self.rewind = RewindEngine(root=str(self.root_path)) if config.snapshot_on_action else None
        self.horizon = (HorizonManager(root=str(self.store.directory / digest(scope)))
                        if config.circuit_breaker_enabled else None)
        if self.rewind: self.rewind.init()

    def audit_path_safety(self, rel_path):
        if Path(rel_path).parts and Path(rel_path).parts[0] == "secrets":
            raise ValueError("Protected path")
        self.tools.path(rel_path)
        result = PathAuditResult()
        for part in Path(rel_path).parts:
            audit_filename(part, rel_path, result)
        return result

    def read_file(self, rel_path):
        try:
            value = self.tools.read(rel_path)
            return {**value, 'success': value['ok'], 'content': value['text'], 'size': len(value['text'])}
        except (ValueError, OSError) as exc:
            return {'ok': False, 'error': str(exc), 'path': rel_path}

    def submit(self, action, *, request_id=None, timeout=30, cancelled=None, checkpoint_msg=None, input_paths=()):
        validate_action(action)
        if action["tool"] not in {"write_file", "edit_file", "run_command"}:
            raise ValueError("Unsupported execution boundary action")
        if self.config.allowed_tools and action['tool'] not in self.config.allowed_tools:
            raise ValueError('Tool not allowed by this environment')
        if not 0 < timeout <= 300:
            raise ValueError('Action timeout must be between 0 and 300 seconds')
        binding = None
        envelope = {'action': action, 'timeout': timeout, 'sandbox': 'workspace-no-network'}
        prior = None
        if request_id:
            try:
                prior = self.store.inspect(request_id)
            except ValueError:
                pass  # A caller may supply a new idempotency ID; it still needs approval.
        if prior:
            if prior['action'] != envelope or prior['scope'] != self.scope:
                raise ValueError('Request ID does not match this action and scope')
            original_inputs = prior['binding'].get('input_sha256', {})
            if input_paths and set(input_paths) != set(original_inputs):
                raise ValueError('Request inputs changed')
            input_paths = tuple(original_inputs)
            if {p: self.tools.read(p)['sha256'] for p in input_paths} != original_inputs:
                raise ValueError('Request inputs changed')
            # Completed retries use the original observed target, not post-mutation bytes.
            if prior['status'] in {'complete', 'running', 'uncertain'}:
                binding = prior['binding']
        def prepare():
            observed = self.tools.prepare(action)
            if input_paths:
                observed = {**observed, 'input_sha256': {p: self.tools.read(p)['sha256'] for p in input_paths}}
            return observed
        if binding is None:
            binding = prepare()
        report = self.store.propose(envelope, binding, self.scope, request_id)
        if report['status'] == 'pending':
            return {**report, 'ok': False, 'success': False, 'error': 'Operator approval required'}

        def operate():
            if cancelled is not None and cancelled.is_set():
                return {'ok': False, 'status': 'cancelled'}
            if prepare() != binding:
                return {'ok': False, 'error': 'Observed target changed after approval'}
            if action['tool'] == 'run_command':
                argv = action['args']['argv']
                description = shlex.join(argv)
                if self.horizon:
                    with self.store.transaction():
                        if self.horizon.record_action(description)['is_loop']:
                            return {'ok': False, 'is_loop': True, 'error': 'Repeated failed command blocked'}
                result = run_command(self._sandbox(argv), self.root_path, timeout=timeout, cancelled=cancelled)
                if self.horizon and not result['ok']:
                    with self.store.transaction():
                        self.horizon.record_action(description, success=False)
                if self.config.log_compaction and len(result['output'].splitlines()) > 40:
                    result['output'] = compact_text(result['output'], context_window=2, max_lines=40)['text']
                return result
            snapshot = self.rewind.snapshot(message=checkpoint_msg or 'Approved write') if self.rewind else None
            return {**self.tools.execute(action, binding), 'snapshot': snapshot}

        result = self.store.execute(report['request_id'], envelope, binding, self.scope, operate)
        return {**result, 'success': result.get('ok', False)}

    def write_file(self, rel_path, content, checkpoint_msg=None, *, request_id=None, expected_sha256=None):
        try:
            audit = self.audit_path_safety(rel_path)
            if not audit.is_clean: raise ValueError('PathCarry rejected the file path')
            target = self.tools.path(rel_path)
            if request_id:
                previous = self.store.inspect(request_id)['action']['action']['args']
                expected_sha256 = expected_sha256 or previous.get('expected_sha256')
            observed = expected_sha256 or (self.tools.read(rel_path)['sha256'] if target.exists() else 'missing')
            return self.submit({'tool': 'write_file', 'args': {'path': rel_path, 'content': content,
                                'expected_sha256': observed}}, request_id=request_id, checkpoint_msg=checkpoint_msg)
        except (ValueError, OSError) as exc:
            return {'ok': False, 'success': False, 'error': str(exc)}

    def execute_command(self, cmd, timeout=30, *, request_id=None, cancelled=None, input_paths=()):
        # Strings are parsed as argv, never interpreted as shell programs.
        argv = shlex.split(cmd, posix=os.name != 'nt') if isinstance(cmd, str) else list(cmd)
        if os.name == 'nt': argv = [arg.strip('"') for arg in argv]
        return self.submit({'tool': 'run_command', 'args': {'argv': argv}}, request_id=request_id,
                           timeout=timeout, cancelled=cancelled, input_paths=input_paths)

    def _sandbox(self, argv):
        binary = shutil.which('bwrap') if sys.platform == 'linux' else None
        if not binary:
            raise RuntimeError('Workspace command sandbox unavailable; command was not executed')
        command = [binary, '--unshare-all', '--die-with-parent', '--new-session']
        for path in ('/usr', '/bin', '/lib', '/lib64', '/sbin'):
            if Path(path).exists(): command += ['--ro-bind', path, path]
        for path in ('/etc/ld.so.cache', '/etc/ssl', '/etc/localtime'):
            if Path(path).exists(): command += ['--ro-bind', path, path]
        # Permit the operator's Python installation, without exposing home or control state.
        for path in {Path(sys.base_prefix).resolve(), Path(sys.prefix).resolve()}:
            if not path.is_relative_to('/usr') and not path.is_relative_to(self.root_path):
                if self.store.directory.is_relative_to(path):
                    raise ValueError('Runtime mount would expose control state')
                command += ['--ro-bind', str(path), str(path)]
        command += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
                    '--bind', str(self.root_path), '/workspace', '--chdir', '/workspace',
                    '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'HOME', '/tmp']
        executable = shutil.which(argv[0]) if not Path(argv[0]).is_absolute() else argv[0]
        if executable:
            argv = [str(Path(executable).resolve()), *argv[1:]]
        return [*command, '--', *argv]

    def to_dict(self):
        return {'config': self.config.to_dict(), 'root_path': str(self.root_path),
                'snapshots_active': self.rewind is not None, 'horizon_active': self.horizon is not None,
                'approval_required': True,
                'command_sandbox': 'bubblewrap' if sys.platform == 'linux' else 'unavailable'}
