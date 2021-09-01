from functools import cmp_to_key
from importlib.util import find_spec
from pathlib import Path
from typing import List, Optional
import sys

from poetry.core.packages.package import Package

from poetry.__version__ import __version__
from poetry.core.packages.dependency import Dependency
from poetry.core.semver.version import Version

from poetry.console import console
from poetry.console.exceptions import PoetrySimpleConsoleException
from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.pool import Pool
from poetry.repositories.pypi_repository import PyPiRepository
from poetry.utils.props_ext import cached_property


class RpInstallation:
    def __init__(self):
        self._version = Version.parse(__version__)
        self._data_dir = None

    @cached_property
    def _installation_env(self):
        from poetry.utils.env import EnvManager
        return EnvManager.get_system_env(naive=False)

    @cached_property
    def _pool(self) -> Pool:
        pool = Pool()
        pool.add_repository(PyPiRepository())
        return pool

    @cached_property
    def data_dir(self) -> Path:
        from poetry.locations import data_dir
        return data_dir()

    @cached_property
    def _installed_repository(self) -> InstalledRepository:
        return InstalledRepository.load(self._installation_env)

    def is_installed_using_recommended_installer(self) -> bool:
        from poetry.utils.env import EnvManager

        env = EnvManager.get_system_env(naive=True)

        # We can't use is_relative_to() since it's only available in Python 3.9+
        try:
            env.path.relative_to(self.data_dir)
            return True
        except ValueError:
            return False

    def _find_update_version(self, version: Optional[str]) -> Optional[Package]:
        if not version:
            version = ">=" + __version__

        repo = self._pool.repositories[0]
        packages = repo.find_packages(
            Dependency("relaxed-poetry", version)
        )

        if not packages:
            raise PoetrySimpleConsoleException(f"No release found for version '{version}'")

        packages.sort(
            key=cmp_to_key(
                lambda x, y: 0
                if x.version == y.version
                else int(x.version < y.version or -1)
            )
        )

        return packages[0] if len(packages) > 0 else None

    def update(self, version: Optional[str]) -> bool:
        if not self.is_installed_using_recommended_installer():
            raise PoetrySimpleConsoleException(
                "Poetry was not installed with the recommended installer, "
                "so it cannot be updated automatically."
            )

        release = self._find_update_version(version)

        if release is None:
            console.println("No new release found")
            return False

        console.println(f"Updating <c1>Relaxed-Poetry</c1> to <c2>{release.version}</c2>")
        console.println()

        release.version

        self.update(release)

        console.println(f"<c1>Relaxed-Poetry</c1> (<c2>{release.version}</c2>) is installed now. Great!")
        console.println()

        return True

    def add_packages(self, *packages: str, dry_run: bool = False):
        from poetry.config.config import Config
        from poetry.core.packages.dependency import Dependency
        from poetry.core.packages.project_package import ProjectPackage
        from poetry.installation.installer import Installer
        from poetry.packages.locker import NullLocker
        from poetry.repositories.installed_repository import InstalledRepository

        env = self._installation_env
        installed = InstalledRepository.load(env)

        root = ProjectPackage("rp-add-packages", "0.0.0")
        root.python_versions = ".".join(str(c) for c in env.version_info[:3])
        for package in packages:
            root.add_dependency(Dependency.create_from_pep_508(package))

        installer = Installer(
            console.io,
            env,
            root,
            NullLocker(self.data_dir.joinpath("poetry.lock"), {}),
            self._pool,
            Config(),
            installed=installed,
        )

        installer.update(True)
        installer.dry_run(dry_run)
        installer.run()

    def has_package(self, package: str, constraint: str = "*") -> bool:
        ir : InstalledRepository = self._installed_repository
        return len(ir.find_packages(Dependency(package, constraint))) > 0

installation = RpInstallation()