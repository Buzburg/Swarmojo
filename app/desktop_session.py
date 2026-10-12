"""One desktop server per state directory, with an OS-released lifetime lock."""
from contextlib import contextmanager
import os


@contextmanager
def desktop_lock(directory):
    path = directory / 'server.lock'
    if path.is_symlink():
        raise ValueError('Desktop lock must not be a symbolic link')
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    handle = os.fdopen(fd, 'r+b')
    locked = False
    try:
        if os.name == 'nt':
            import msvcrt
            if not path.stat().st_size:
                handle.write(b'0'); handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise RuntimeError('Another desktop is already using this state directory') from error
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise RuntimeError('Another desktop is already using this state directory') from error
        locked = True
        yield
    finally:
        if locked:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
