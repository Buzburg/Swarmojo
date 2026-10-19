"""Credential confidentiality, migration, and failure preservation."""
import base64
import hashlib
import json
import os

import pytest
from app.engines.personal_assistant import AssistantVault
from app.control_store import ControlStore


@pytest.fixture
def vault(tmp_path,monkeypatch):
    monkeypatch.setenv('SWARMOJO_CONTROL_DIR',str(tmp_path/'private-control'))
    root=tmp_path/'workspace';root.mkdir()
    return AssistantVault(str(root)),root


def test_secret_is_encrypted_and_survives_restart(vault):
    v,root=vault
    v.set_secret('example','test-only-secret')
    data=v.vault_file.read_text()
    assert 'test-only-secret' not in data
    assert base64.b64encode(b'test-only-secret').decode() not in data
    assert 'payload' not in data
    assert AssistantVault(str(root)).get_secret('example')=='test-only-secret'
    key=ControlStore(root).directory/'assistant-vault.key'
    assert not key.is_relative_to(root)
    if os.name!='nt':
        assert key.stat().st_mode & 0o777==0o600
        assert v.vault_file.stat().st_mode & 0o777==0o600


def test_legacy_credentials_migrate_together_without_plaintext_backup(vault):
    v,root=vault
    old={key:{'payload':base64.b64encode(value.encode()).decode(),'sha256':hashlib.sha256(value.encode()).hexdigest()} for key,value in [('one','secret-one'),('two','secret-two')]}
    v.vault_file.write_text(json.dumps(old))
    assert v.get_secret('one')=='secret-one'
    assert v.get_secret('two')=='secret-two'
    updated=json.loads(v.vault_file.read_text())
    assert all(record['version']==2 and 'payload' not in record for record in updated.values())
    assert sorted(p.name for p in v.state_dir.iterdir())==['preferences.json','vault.json']


def test_lost_key_and_corrupt_vault_fail_without_overwriting(vault):
    v,root=vault;v.set_secret('example','secret')
    original=v.vault_file.read_bytes()
    key=ControlStore(root).directory/'assistant-vault.key';key.unlink()
    with pytest.raises(ValueError,match='key is missing'):v.set_secret('other','replacement')
    assert v.vault_file.read_bytes()==original and not key.exists()
    v.vault_file.write_text('{broken')
    with pytest.raises(ValueError):v.set_secret('other','replacement')
    assert v.vault_file.read_text()=='{broken'


def test_tampered_ciphertext_and_symlinks_fail_closed(vault,tmp_path):
    v,root=vault;v.set_secret('example','secret')
    data=json.loads(v.vault_file.read_text());data['example']['ciphertext']='invalid'
    v.vault_file.write_text(json.dumps(data));before=v.vault_file.read_bytes()
    with pytest.raises(Exception):v.set_secret('example','replacement')
    assert v.vault_file.read_bytes()==before
    v.vault_file.unlink();outside=tmp_path/'untouched';outside.write_text('untouched')
    try:v.vault_file.symlink_to(outside)
    except OSError:pytest.skip('Host does not permit symlinks')
    with pytest.raises(ValueError,match='links'):v.set_secret('example','replacement')
    assert outside.read_text()=='untouched'
