"""Source reads must reject link traversal on native and portable paths."""
import os

import pytest

from app.patch_tasks import read_file


@pytest.fixture(params=[False, True], ids=['native', 'portable'])
def reader(request, monkeypatch):
    if request.param:
        monkeypatch.setattr(os, 'supports_dir_fd', set())
    return read_file


def test_regular_and_missing_source(reader, tmp_path):
    (tmp_path / 'source.py').write_bytes(b'VALUE = 1\n')
    assert reader(tmp_path, 'source.py') == b'VALUE = 1\n'
    assert reader(tmp_path, 'missing.py') is None


@pytest.mark.parametrize('relative', ['../outside.py', '/outside.py', 'nested/../../outside.py'])
def test_parent_and_absolute_paths_are_rejected(reader, tmp_path, relative):
    with pytest.raises(ValueError):
        reader(tmp_path, relative)


@pytest.mark.parametrize('inside', [False, True])
@pytest.mark.parametrize('directory', [False, True])
def test_links_never_become_source_files(reader, tmp_path, inside, directory):
    root = tmp_path / 'source'
    root.mkdir()
    target = root / 'real' if inside else tmp_path / 'source-neighbor'
    target.mkdir()
    (target / 'module.py').write_bytes(b'private source\n')
    link = root / ('linked' if directory else 'linked.py')
    try:
        link.symlink_to(target if directory else target / 'module.py', target_is_directory=directory)
    except OSError:
        pytest.skip('Host does not permit symlink creation')
    with pytest.raises((ValueError, OSError)):
        reader(root, 'linked/module.py' if directory else 'linked.py')
