from functools import reduce
from typing import TypeVar, Dict, Union, Optional, List

K = TypeVar("K")
V = TypeVar("V")


def nesteddict_lookup(d: Dict, path: List[K], default: Optional[V] = None) -> Union[Dict, V, None]:
    try:
        return reduce(dict.get, path, d)
    except KeyError:
        return default


def nesteddict_put(d: Dict, path: List[K], value: V):
    r = d
    for p in path[:-1]:
        try:
            r = r[p]
        except KeyError:
            r[p] = {}
            r = r[p]

    r[path[-1]] = value


def nesteddict_put_if_absent(d: Dict, path: List[K], value: V) -> V:
    r = d
    for p in path[:-1]:
        try:
            r = r[p]
        except KeyError:
            r[p] = {}
            r = r[p]

    lp = path[-1]
    if lp not in r:
        r[lp] = value

    return r[lp]




if __name__ == '__main__':
    x = {}
    nesteddict_put(x, ["a", "b", "c"], 7)
    print(x)
