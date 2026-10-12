"""Optional PolyHarness must not make a public clone depend on private code."""
import os
from pathlib import Path
import subprocess
import sys

from app import polyharness


def test_missing_optional_checkout_has_actionable_error(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / 'swarmmojo.py'), 'polyharness', '--help'],
        cwd=tmp_path, env={**os.environ, 'SWARMOJO_POLYHARNESS_ROOT': str(tmp_path / 'missing')},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 1
    assert 'optional PolyHarness' in result.stderr
    assert 'SWARMOJO_POLYHARNESS_ROOT' in result.stderr
    assert not (tmp_path / 'missing').exists()


def test_available_checkout_receives_literal_arguments(tmp_path, monkeypatch):
    binary = tmp_path / 'private checkout' / 'bin' / 'polyharness.js'
    binary.parent.mkdir(parents=True)
    binary.write_text('// fixture', encoding='utf-8')
    monkeypatch.setattr(polyharness, 'POLYHARNESS_BIN', binary)
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 7)

    monkeypatch.setattr(polyharness.subprocess, 'run', run)
    assert polyharness.run_polyharness(['check', 'path with spaces']) == 7
    assert calls == [(['node', str(binary), 'check', 'path with spaces'], {'check': False})]
