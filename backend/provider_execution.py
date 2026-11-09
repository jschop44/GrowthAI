"""Process-wide bounded provider execution with in-flight request sharing."""
from concurrent.futures import Future, ThreadPoolExecutor
from threading import RLock

_POOL = ThreadPoolExecutor(max_workers=5, thread_name_prefix="public-intel")
_LOCK = RLock()
_PENDING = {}
_CAPACITY = 10


def submit_provider(subject, engine, worker, args):
    key = (subject, engine)
    with _LOCK:
        if key in _PENDING:
            return _PENDING[key]
        if len(_PENDING) >= _CAPACITY:
            future = Future()
            future.set_result({"status": "unavailable", "source": engine,
                               "reason": "Provider capacity reached; retry shortly"})
            return future
        future = _POOL.submit(worker, *args)
        _PENDING[key] = future

        def completed(_):
            with _LOCK:
                if _PENDING.get(key) is future:
                    del _PENDING[key]

        future.add_done_callback(completed)
        return future
