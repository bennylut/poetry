from contextlib import contextmanager
from threading import Lock


@contextmanager
def locked(lock: Lock, blocking=True, timeout=-1):
    success = lock.acquire(blocking, timeout)
    if not success:
        yield False

    try:
        yield True
    finally:
        lock.release()
