import threading
from pathlib import Path

import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache
from poetry.locations import CACHE_DIR

_global_sessions = threading.local()
_persistent_cache = FileCache(str(Path(CACHE_DIR) / "http"))


def session() -> requests.Session:
    try:
        return _global_sessions.session
    except AttributeError:
        result = requests.Session()
        _global_sessions.session = result
        return result


def cached_session(persistent: bool = False) -> requests.Session:
    attr = "pcsession" if persistent else "mcsession"
    try:
        return getattr(_global_sessions, attr)
    except AttributeError:
        result = CacheControl(requests.Session(), _persistent_cache) if persistent else CacheControl(requests.Session())
        setattr(_global_sessions, attr, result)
        return result


def remove_persistent_cache(url: str):
    _persistent_cache.delete(url)
