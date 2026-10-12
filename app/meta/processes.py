"""Owned process trees with bounded output and explicit cancellation."""
import os
import signal
import subprocess
import threading
import time


def windows_job():
    """Attach this worker to a kill-on-close job before it can launch children."""
    if os.name != 'nt':
        os.setsid()
        return None
    import ctypes as c
    from ctypes import wintypes as w
    class Basic(c.Structure):
        _fields_ = [('process_time', c.c_longlong), ('job_time', c.c_longlong), ('flags', w.DWORD),
                    ('min_ws', c.c_size_t), ('max_ws', c.c_size_t), ('active', w.DWORD),
                    ('affinity', c.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
    class IO(c.Structure):
        _fields_ = [(n, c.c_ulonglong) for n in ('read_ops', 'write_ops', 'other_ops', 'read', 'write', 'other')]
    class Extended(c.Structure):
        _fields_ = [('basic', Basic), ('io', IO), ('process_memory', c.c_size_t),
                    ('job_memory', c.c_size_t), ('peak_process', c.c_size_t), ('peak_job', c.c_size_t)]
    kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
    kernel.CreateJobObjectW.restype = w.HANDLE
    kernel.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    kernel.GetCurrentProcess.restype = w.HANDLE
    job = kernel.CreateJobObjectW(None, None)
    info = Extended(); info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not job or not kernel.SetInformationJobObject(job, 9, c.byref(info), c.sizeof(info)):
        raise c.WinError(c.get_last_error())
    if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        raise c.WinError(c.get_last_error())
    return job  # Deliberately retain until worker exit; the OS closes it and kills descendants.


def stop_worker(process):
    if os.name != 'nt':
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.is_alive():
        process.kill()
    process.join(timeout=3)
    if process.is_alive():
        raise RuntimeError('Owned worker could not be reaped')


def run_command(argv, cwd, timeout=30, cancelled=None, limit=65536):
    """Bounded command in an already owned worker or sandbox."""
    env = {k: os.environ[k] for k in ('PATH', 'SYSTEMROOT', 'WINDIR', 'LANG', 'TMP', 'TEMP') if k in os.environ}
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False,
                            start_new_session=os.name != 'nt')
    output = bytearray(); overflow = threading.Event()
    def drain():
        while chunk := proc.stdout.read(4096):
            remaining = max(0, limit - len(output))
            if len(chunk) > remaining:
                overflow.set()
            output.extend(chunk[:remaining])
    reader = threading.Thread(target=drain, daemon=True); reader.start()
    deadline = time.monotonic() + timeout
    reason = None
    try:
        while proc.poll() is None:
            if cancelled is not None and cancelled.is_set(): reason = 'cancelled'
            elif overflow.is_set(): reason = 'output_limit'
            elif time.monotonic() >= deadline: reason = 'timeout'
            if reason: break
            time.sleep(.01)
    finally:
        if os.name != 'nt':
            try: os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError: pass
        elif proc.poll() is None:
            proc.kill()
        proc.wait(timeout=3); reader.join(timeout=3)
        if reader.is_alive(): raise RuntimeError('Output collector did not stop')
        proc.stdout.close()
    if overflow.is_set(): reason = reason or 'output_limit'
    return {'ok': proc.returncode == 0 and reason is None, 'returncode': proc.returncode,
            'output': output.decode('utf-8', errors='replace'), 'status': reason or 'completed',
            'truncated': overflow.is_set()}
