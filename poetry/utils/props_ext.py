from threading import Lock

from poetry.utils.sync_ext import locked

try:
    from functools import cached_property
except ImportError:

    from typing import TypeVar, Callable, Any

    _T = TypeVar("_T")

    class cached_property:  # noqa

        def __init__(self, func: Callable[[Any], _T]):
            self._func = func
            self._attr = None
            self.__doc__ = func.__doc__
            self._mutation_lock = Lock()

        def __set_name__(self, owner, name):
            self._attr = f"_lazy_{name}"

        def __get__(self, instance, owner) -> _T:
            if instance is None:
                return self

            while True:
                try:
                    return getattr(instance, self._attr)
                except AttributeError:
                    with locked(self._mutation_lock):
                        if not hasattr(instance, self._attr):
                            setattr(instance, self._attr, self._func(instance))

        def __set__(self, instance, value: _T):
            setattr(instance, self._attr, value)
