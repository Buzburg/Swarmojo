"""Load the prebuilt Mojo kernels; never compile or download during a search."""
from functools import lru_cache
import importlib
import os
import sys
import sysconfig
import threading
from pathlib import Path

_import_lock = threading.Lock()


@lru_cache(maxsize=1)
def _load():
    if importlib.util.find_spec('app.roms_search_native') is None:
        return None
    try:
        # Mojo initializes Python runtime variables in the C environment. Keep
        # subprocesses attached to this interpreter, then restore the caller's env.
        with _import_lock:
            values = {'PYTHONEXECUTABLE': sys.executable,
                      'MOJO_PYTHON_LIBRARY': str(Path(sysconfig.get_config_var('LIBDIR')) / sysconfig.get_config_var('LDLIBRARY')),
                      'PYTHONPATH': os.environ.get('PYTHONPATH', '')}
            previous = {key: os.environ.get(key) for key in values}
            try:
                os.environ.update(values)
                return importlib.import_module('app.roms_search_native')
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                        os.unsetenv(key)
                    else:
                        os.environ[key] = value
    except ModuleNotFoundError as exc:
        if exc.name != 'app.roms_search_native':
            raise
        return None


def kernels():
    native = _load()
    if native is None or not all(hasattr(native, name) for name in ('expand', 'fuse', 'clean', 'passages')):
        raise RuntimeError('Build the required Mojo search module with scripts/build_search_native.py and restart ROMS')
    return native


def kernel_name():
    kernels()
    return 'mojo'
