"""Durable, scoped command requests; only operator-approved actions execute.

A request ID gives at-most-once dispatch across retries and restarts. A crashed
in-flight request is uncertain and is never silently executed again.
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class DedupEntry:
    key_hash: str
    command: str
    cwd: str
    stdout: str
    stderr: str
    exit_code: int
    executed_at: float
    ttl_seconds: float
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.executed_at) > self.ttl_seconds

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Backward-compatible alias
OnceEntry = DedupEntry




from app.control_store import digest, packed
from app.meta.environment import ExecutionEnvironment
from app.meta.manifest import EnvironmentConfig


class DeduplicatedExecutionCache:
    def __init__(self, default_ttl_seconds=60.0, *, workspace_root='.', state_dir=None):
        self.default_ttl = default_ttl_seconds
        self.root = Path(workspace_root).resolve()
        self.state_dir = state_dir

    def get_or_run(self, command, cwd='.', ttl_seconds=None, tenant_id='default', force_refresh=False,
                   *, request_id=None, input_paths=()):
        cwd = self.root if cwd == '.' else Path(cwd).resolve()
        if cwd != self.root:
            raise ValueError('Command workspace is fixed by the operator')
        if not isinstance(tenant_id, str) or not 1 <= len(tenant_id) <= 128:
            raise ValueError('Invalid execution scope')
        ttl = self.default_ttl if ttl_seconds is None else ttl_seconds
        if not 0 < ttl <= 86400: raise ValueError('TTL must be 0..86400 seconds')
        env = ExecutionEnvironment(EnvironmentConfig(id='dedup', name='Deduplicated execution',
                    root_path=str(self.root), snapshot_on_action=False), state_dir=self.state_dir, scope=tenant_id)
        inputs = {name: env.tools.read(name)['sha256'] for name in input_paths}
        key = 'dedup:' + digest({'command': command, 'scope': tenant_id, 'inputs': inputs})
        if request_id is None:
            with env.store.transaction() as db:
                row = db.execute('SELECT value FROM state WHERE name=?', (key,)).fetchone()
                import json
                value = json.loads(row['value']) if row else None
                if not value or value['expires'] < time.time() or force_refresh:
                    value = {'id': uuid.uuid4().hex, 'expires': time.time() + ttl}
                    db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', (key, packed(value)))
                request_id = value['id']
        result = env.execute_command(command, request_id=request_id, input_paths=input_paths)
        return {**result, 'request_id': request_id, 'from_cache': result.get('replayed', False),
                'stdout': result.get('output', ''), 'stderr': result.get('error', ''),
                'exit_code': result.get('returncode', -1), 'hits': int(result.get('replayed', False))}

    def run_batch(self, commands, cwd='.', ttl_seconds=None):
        return [self.get_or_run(cmd, cwd=cwd, ttl_seconds=ttl_seconds) for cmd in commands]

    def purge_expired(self):
        # Request receipts and uncertain effects must outlive cache expiry.
        return 0

    def stats(self):
        env = ExecutionEnvironment(EnvironmentConfig(id='cache', name='Cache', root_path=str(self.root),
                                   snapshot_on_action=False), state_dir=self.state_dir)
        with env.store.transaction() as db:
            return {'total_entries': db.execute('SELECT count(*) FROM requests').fetchone()[0],
                    'durable': True}


OnceExecutionCache = DeduplicatedExecutionCache
