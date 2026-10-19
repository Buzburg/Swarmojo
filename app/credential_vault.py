"""Authenticated local credential storage with a key outside project snapshots."""
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time

from cryptography.fernet import Fernet
from app.control_store import ControlStore

_LOCK = threading.RLock()


class EncryptedVault:
    def __init__(self, workspace, path):
        self.workspace, self.path = Path(workspace), Path(path)

    def _cipher(self, *, create):
        key_path = ControlStore(self.workspace).directory / 'assistant-vault.key'
        if key_path.is_symlink():
            raise ValueError('Vault key links are not allowed')
        if create and not key_path.exists():
            try:
                fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(Fernet.generate_key())
                    stream.flush()
                    os.fsync(stream.fileno())
        if not key_path.is_file():
            raise ValueError('Vault encryption key is missing; restore it from your private backup')
        fd = os.open(key_path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'rb') as stream:
            if os.name != 'nt' and os.fstat(stream.fileno()).st_mode & 0o077:
                raise ValueError('Vault key must be private to its owner (mode 0600)')
            return Fernet(stream.read())

    def _read(self):
        if self.path.parent.is_symlink() or self.path.is_symlink():
            raise ValueError('Vault links are not allowed')
        if not self.path.exists():
            return {}
        # A corrupt vault must not be treated as empty and overwritten.
        data = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('Invalid vault contents')
        return data

    def _save(self, data):
        if self.path.parent.is_symlink() or self.path.is_symlink():
            raise ValueError('Vault links are not allowed')
        fd, temp = tempfile.mkstemp(prefix='.vault-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(data, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.path)
        finally:
            Path(temp).unlink(missing_ok=True)

    def _load_encrypted(self):
        data = self._read()
        # Never replace a lost key when encrypted records already exist.
        cipher = self._cipher(create=not any('ciphertext' in v for v in data.values()))
        changed = False
        for key, entry in data.items():
            if 'ciphertext' in entry:
                cipher.decrypt(entry['ciphertext'].encode('ascii'))
            elif 'payload' in entry:
                raw = base64.b64decode(entry['payload'], validate=True)
                if hashlib.sha256(raw).hexdigest() != entry.get('sha256'):
                    raise ValueError('Legacy credential fingerprint does not match')
                token = cipher.encrypt(raw).decode('ascii')
                data[key] = {'ciphertext': token, 'version': 2, 'updated_at': entry.get('updated_at', time.time())}
                changed = True
            else:
                raise ValueError('Unknown credential format')
        if changed:
            self._save(data)
        return data, cipher

    def set(self, key, value):
        with _LOCK:
            data, cipher = self._load_encrypted()
            data[key] = {'ciphertext': cipher.encrypt(value.encode('utf-8')).decode('ascii'),
                         'version': 2, 'updated_at': time.time()}
            self._save(data)

    def get(self, key):
        with _LOCK:
            data, cipher = self._load_encrypted()
            entry = data.get(key)
            return cipher.decrypt(entry['ciphertext'].encode('ascii')).decode('utf-8') if entry else None

    def records(self):
        with _LOCK:
            data, _ = self._load_encrypted()
            return data
