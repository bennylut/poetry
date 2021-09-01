from concurrent.futures._base import Future
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Dict, Optional, List, Any

from poetry.core.packages.dependency import Dependency

from poetry.mixology import VersionSolver
from poetry.packages import DependencyPackage

class VersionPrefetcher:

    def __init__(self, version_solver: VersionSolver, max_workers=6):
        self._vsolver = version_solver
        self._prefetched: Dict[str, Future] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def prefetched(self, d: Dependency) -> Optional[DependencyPackage]:
        future = self._prefetched.get(str(d))
        return future.result() if future else None

    def shutdown(self):
        for prefetching in self._prefetched.values():
            prefetching.cancel()

        self._executor.shutdown(False)

    def prefetch(self):
        pending: List[Dependency] = [d for d in self._vsolver.solution.unsatisfied if str(d) not in self._prefetched]
        vsolver = self._vsolver

        def fetch(dependency):
            version = vsolver._get_locked(dependency)
            if version is None or not dependency.constraint.allows(version.version):
                try:
                    packages = vsolver._provider.search_for(dependency)
                    version = packages[0]
                except ValueError:
                    pass
                except IndexError:
                    pass

            if version:
                result = vsolver._provider.complete_package(version)
                self._prefetched[str(version.dependency)] = _FakeFuture(result)
                return result

            return None

        for dependency in pending:
            version = self._executor.submit(fetch, dependency)
            if version:
                self._prefetched[str(dependency)] = version


class _FakeFuture:
    def __init__(self, r: Any):
        self._result = r

    def result(self) -> Any:
        return self._result

    def cancel(self):
        pass