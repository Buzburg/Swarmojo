"""Concurrent trusted callables in owned, killable processes; never model-supplied code."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import multiprocessing
import time
from typing import Any
import cloudpickle

from app.meta.processes import stop_worker, windows_job


@dataclass
class TaskExecutionResult:
    task_id: str
    status: str
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0

    def to_dict(self):
        return asdict(self)


def _worker(payload, channel):
    job = windows_job()
    try:
        fn = cloudpickle.loads(payload)
        start = time.monotonic()
        try:
            result = {'status': 'completed', 'result': fn(), 'error': None}
        except Exception as exc:
            result = {'status': 'error', 'result': None, 'error': str(exc)}
        result['duration_ms'] = (time.monotonic() - start) * 1000
        encoded = cloudpickle.dumps(result)
        if len(encoded) > 1024 * 1024:
            encoded = cloudpickle.dumps({'status': 'error', 'error': 'Result exceeds 1 MiB', 'result': None,
                                         'duration_ms': result['duration_ms']})
        channel.send_bytes(encoded)
    finally:
        channel.close()


class ParallelToolDispatcher:
    """Process isolation: task mutations of parent Python objects are not shared."""
    def __init__(self, max_workers=8, default_timeout_s=10.0):
        if type(max_workers) is not int or not 1 <= max_workers <= 64:
            raise ValueError('Worker count must be 1..64')
        self.max_workers = max_workers
        self.default_timeout_s = default_timeout_s

    def execute_batch(self, tasks, timeout_s=None, cancelled=None):
        timeout = self.default_timeout_s if timeout_s is None else timeout_s
        if not 0 < timeout <= 3600 or len(tasks) > 256:
            raise ValueError('Invalid bounded batch or deadline')
        if len({k for k, _ in tasks}) != len(tasks):
            raise ValueError('Task IDs must be unique')
        pending = []
        for name, fn in tasks:
            if not isinstance(name, str) or not callable(fn): raise ValueError('Expected named callables')
            payload = cloudpickle.dumps(fn)
            if len(payload) > 1024 * 1024: raise ValueError('Callable exceeds 1 MiB')
            pending.append((name, payload))
        context = multiprocessing.get_context('spawn')
        start = time.monotonic(); deadline = start + timeout
        active = {}; results = {}
        try:
            while pending or active:
                stopped = cancelled is not None and cancelled.is_set()
                expired = time.monotonic() >= deadline
                if stopped or expired:
                    status = 'cancelled' if stopped else 'timeout'
                    for name, _ in pending:
                        results[name] = TaskExecutionResult(name, status).to_dict()
                    pending.clear()
                    for name, (proc, pipe) in list(active.items()):
                        stop_worker(proc); pipe.close(); del active[name]
                        results[name] = TaskExecutionResult(name, status).to_dict()
                    break
                while pending and len(active) < self.max_workers:
                    name, payload = pending.pop(0)
                    receive, send = context.Pipe(duplex=False)
                    proc = context.Process(target=_worker, args=(payload, send))
                    proc.start(); send.close()
                    active[name] = (proc, receive)
                for name, (proc, pipe) in list(active.items()):
                    if pipe.poll() or not proc.is_alive():
                        try:
                            value = cloudpickle.loads(pipe.recv_bytes(1024 * 1024))
                        except (EOFError, OSError):
                            value = {'status': 'error', 'error': 'Worker exited without a result'}
                        results[name] = {'task_id': name, **value}
                        stop_worker(proc); pipe.close(); del active[name]
                if active: time.sleep(.005)
        finally:
            for proc, pipe in active.values():
                stop_worker(proc); pipe.close()
        wall = (time.monotonic() - start) * 1000
        total = sum(v.get('duration_ms', 0) for v in results.values())
        return {'total_tasks': len(tasks), 'completed': sum(v['status'] == 'completed' for v in results.values()),
                'failed': sum(v['status'] != 'completed' for v in results.values()),
                'wall_clock_ms': round(wall, 2), 'sequential_estimate_ms': round(total, 2),
                'speedup_factor': round(total / max(wall, .001), 2), 'results': results}
