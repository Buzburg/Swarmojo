"""Operator-owned SQLite ledger shared by model-independent meta-harness actions."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid


def packed(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(packed(value).encode()).hexdigest()


class ControlStore:
    def __init__(self, workspace, state_dir=None):
        self.workspace = Path(workspace).resolve()
        base = Path(state_dir or os.environ.get('SWARMOJO_CONTROL_DIR',
                    Path.home() / '.local/state/swarmojo/control')).expanduser().absolute()
        if base.resolve().is_relative_to(self.workspace):
            raise ValueError('Control state must be outside the model workspace')
        for part in (base, *base.parents):
            if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
                raise ValueError('Control state must not traverse links')
        self.directory = base / hashlib.sha256(str(self.workspace).encode()).hexdigest()
        if self.directory.is_symlink() or getattr(self.directory, 'is_junction', lambda: False)():
            raise ValueError('Control workspace directory must not be a link')
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.directory / 'control.sqlite3'
        if self.path.is_symlink():
            raise ValueError('Control database must not be a link')
        with self.transaction() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS state (name TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, scope TEXT NOT NULL,
                    action TEXT NOT NULL, binding TEXT NOT NULL, status TEXT NOT NULL,
                    result TEXT, created REAL NOT NULL, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS facts (
                    scope TEXT NOT NULL, receipt TEXT NOT NULL, content TEXT NOT NULL,
                    PRIMARY KEY(scope, receipt));
            ''')
        if os.name != 'nt':
            self.path.chmod(0o600)

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA busy_timeout=10000')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def propose(self, action, binding, scope='default', request_id=None, lifetime=900):
        identity = {'action': action, 'binding': binding, 'scope': scope,
                    'workspace': str(self.workspace)}
        fingerprint = digest(identity)
        request_id = request_id or uuid.uuid4().hex
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
            raise ValueError('Request ID must be bounded text')
        with self.transaction() as db:
            row = db.execute('SELECT * FROM requests WHERE id=?', (request_id,)).fetchone()
            if row:
                if row['fingerprint'] != fingerprint:
                    raise ValueError('Request ID already binds a different action, scope or target')
                return self._report(row)
            now = time.time()
            db.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?)',
                       (request_id, fingerprint, scope, packed(action), packed(binding),
                        'pending', None, now, now + lifetime))
            return self._report(db.execute('SELECT * FROM requests WHERE id=?', (request_id,)).fetchone())

    @staticmethod
    def _report(row):
        return {'request_id': row['id'], 'status': row['status'],
                'action': json.loads(row['action']), 'binding': json.loads(row['binding']),
                'scope': row['scope'], 'fingerprint': row['fingerprint'], 'expires': row['expires'],
                'approval_required': row['status'] == 'pending',
                'result': json.loads(row['result']) if row['result'] else None}

    def inspect(self, request_id):
        with self.transaction() as db:
            row = db.execute('SELECT * FROM requests WHERE id=?', (request_id,)).fetchone()
            if row is None:
                raise ValueError('Unknown request')
            return self._report(row)

    def approve(self, request_id, fingerprint):
        """Operator API only; never register this as a model-callable tool."""
        with self.transaction() as db:
            row = db.execute('SELECT * FROM requests WHERE id=?', (request_id,)).fetchone()
            if not row or row['fingerprint'] != fingerprint or row['expires'] <= time.time():
                raise ValueError('Approval must match a current reviewed fingerprint')
            if row['status'] != 'pending':
                raise ValueError('Request is no longer pending')
            db.execute("UPDATE requests SET status='approved' WHERE id=?", (request_id,))
        return self.inspect(request_id)

    def execute(self, request_id, action, binding, scope, operation):
        with self.transaction() as db:
            row = db.execute('SELECT * FROM requests WHERE id=?', (request_id,)).fetchone()
            fingerprint = digest({'action': action, 'binding': binding, 'scope': scope,
                                  'workspace': str(self.workspace)})
            if not row or row['fingerprint'] != fingerprint:
                raise ValueError('Approval does not match this action and observed target')
            if row['status'] == 'complete':
                return {**json.loads(row['result']), 'replayed': True, 'receipt_id': request_id}
            if row['status'] in {'running', 'uncertain'}:
                return {'ok': False, 'status': 'uncertain', 'request_id': request_id,
                        'error': 'An earlier dispatch may have taken effect; never retry it automatically'}
            if row['status'] != 'approved' or row['expires'] <= time.time():
                return {**self._report(row), 'ok': False, 'error': 'Current operator approval required'}
            db.execute("UPDATE requests SET status='running' WHERE id=?", (request_id,))
        # The durable intent is committed before any external effect. Crashes leave an uncertain request.
        try:
            result = operation()
        except Exception as exc:
            result = {'ok': False, 'status': 'uncertain', 'error': type(exc).__name__}
        with self.transaction() as db:
            db.execute('UPDATE requests SET status=?, result=? WHERE id=?',
                       ('uncertain' if result.get('status') == 'uncertain' else 'complete', packed(result), request_id))
        return {**result, 'receipt_id': request_id, 'replayed': False}

    def record_fact(self, scope, receipt_id):
        """Store receipt contents, never a caller's unsupported factual claim."""
        with self.transaction() as db:
            row = db.execute('SELECT * FROM requests WHERE id=?', (receipt_id,)).fetchone()
            if not row or row['scope'] != scope or row['status'] != 'complete':
                raise ValueError('A completed receipt in this agent/run scope is required')
            result = json.loads(row['result'])
            if result.get('ok') is not True:
                raise ValueError('Failed operations cannot become verified facts')
            content = packed({'action': json.loads(row['action']), 'result': result})
            db.execute('INSERT OR IGNORE INTO facts VALUES (?,?,?)', (scope, receipt_id, content))
            return content

    def facts(self, scope):
        with self.transaction() as db:
            return [dict(r) for r in db.execute('SELECT receipt,content FROM facts WHERE scope=?', (scope,))]


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Review and approve an exact meta-harness action locally')
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--state-dir')
    parser.add_argument('command', choices=['inspect', 'approve'])
    parser.add_argument('request_id')
    parser.add_argument('--fingerprint')
    args = parser.parse_args()
    store = ControlStore(args.workspace, args.state_dir)
    report = (store.approve(args.request_id, args.fingerprint) if args.command == 'approve'
              else store.inspect(args.request_id))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
