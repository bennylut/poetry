from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Optional, Union
from typing import List

from cleo.io.outputs.output import Verbosity
from poetry.core._vendor.tomlkit import inline_table
from poetry.core.packages.dependency import Dependency
from poetry.core.pyproject.profiles import ProfilesActivationData
from poetry.core.pyproject.toml import PyProject
from poetry.core.utils.props_ext import cached_property

from poetry.__version__ import __version__
from poetry.config.source import Source
from poetry.core.poetry import Poetry as BasePoetry

from .console import console
from .installation import Installer
from .utils.authenticator import Authenticator

if TYPE_CHECKING:
    from poetry.core.packages.project_package import ProjectPackage

    from .config.config import Config
    from .packages.locker import Locker
    from .plugins.plugin_manager import PluginManager
    from .repositories.pool import Pool
    from .utils.env import Env


class ManagedProject(BasePoetry):
    VERSION = __version__

    def __init__(
            self,
            pyproject: PyProject,
            package: "ProjectPackage",
            locker: "Locker",
            config: "Config",
            env: Optional["Env"] = None,
    ):
        from .repositories.pool import Pool  # noqa

        super(ManagedProject, self).__init__(pyproject, package)

        self._locker = locker
        self._config = config
        self._pool = Pool()
        self._env = env

    @property
    def path(self) -> Path:
        return self.pyproject.path.parent

    @property
    def locker(self) -> "Locker":
        return self._locker

    @property
    def pool(self) -> "Pool":
        return self._pool

    @property
    def config(self) -> "Config":
        return self._config

    @property
    def env(self) -> Optional["Env"]:
        if not self.pyproject.requires_python:
            return None

        if not self._env:

            if not self.pyproject.is_stored():
                return None

            from .utils.env import EnvManager

            env_manager = EnvManager(self)
            env = env_manager.create_venv(ignore_activated_env=True)

            console.println(f"Using virtualenv: <comment>{env.path}</>", Verbosity.VERBOSE)
            self._env = env

        return self._env

    @cached_property
    def authenticator(self) -> Authenticator:
        return Authenticator(self.config, console.io)

    def _create_installer(self, package: "ProjectPackage") -> Optional["Installer"]:
        if self.env is None:
            return None

        installer = Installer(self, package=package)

        installer.use_executor(self.config.get("experimental.new-installer", False))
        return installer

    @cached_property
    def installer(self) -> Optional["Installer"]:
        return self._create_installer(self.package)

    def set_locker(self, locker: "Locker") -> "ManagedProject":
        self._locker = locker

        return self

    def set_pool(self, pool: "Pool") -> "ManagedProject":
        self._pool = pool

        return self

    def set_config(self, config: "Config") -> "ManagedProject":
        self._config = config

        return self

    def get_sources(self) -> List[Source]:
        return [
            Source(**source)
            for source in self.pyproject.poetry_config.get("source", [])
        ]

    def _load_related_project(self, pyprj: PyProject) -> "ManagedProject":
        from poetry.factory import Factory
        return Factory().create_poetry_for_pyproject(pyprj)

    def sub_projects(self) -> Iterator["ManagedProject"]:
        if self.pyproject.is_parent():
            for subproject in self.pyproject.sub_projects.values():
                yield from self._load_related_project(subproject).sub_projects()

        yield self

    @cached_property
    def parent(self) -> Optional["ManagedProject"]:
        parent = self.pyproject.parent
        if parent:
            return self._load_related_project(parent)
        return None

    def install_dependencies(
            self, dependencies: List[str], *, with_groups: Optional[List[str]] = None, synchronize: bool = False,
            lock_only: bool = False, update: bool = False, dry_run: bool = False, allow_prereleases: bool = False,
            source: Optional[str] = None, optional: bool = False, extras_strings: Optional[List[str]] = None,
            editable: bool = False, python: Optional[str] = None, platform: Optional[str] = None,
            group: str = "default"):

        kwargs = {
            "allow_prereleases": allow_prereleases, "source": source, "optional": optional,
            "extras_strings": extras_strings, "editable": editable, "python": python, "platform": platform,
            "group": group
        }

        from .dependencies.dependency_parser import DependencyParser

        modified_package = self.package.clone()

        dparser = DependencyParser(self)
        parsed_deps = [dparser.parse(dependency, **kwargs) for dependency in dependencies]

        existing_dependencies = {dependency.name: dependency for dependency in modified_package.all_requires}
        for parsed_dep in parsed_deps:
            if parsed_dep.dependency.name in existing_dependencies:
                if update:
                    existing_dependency: Dependency = existing_dependencies[parsed_dep.dependency.name]
                    for group in existing_dependency.groups:
                        modified_package.dependency_group(group).remove_dependency(existing_dependency.name)
                else:
                    if parsed_dep.constraint != '*':
                        raise ValueError(
                            f"dependency {parsed_dep.dependency.name} already exists in pyproject, if you want to change it re-run with --update")
                    continue  # dont add the dependency - it is already set

            modified_package.add_dependency(parsed_dep.dependency)

        installer = self._create_installer(modified_package)
        installer.dry_run(dry_run)
        if lock_only:
            installer.lock(update)
        else:
            installer.update(update)

        if len(dependencies) == 0 and extras_strings:
            installer.extras(extras_strings)

        installer.requires_synchronization(synchronize)
        if with_groups:
            installer.with_groups(with_groups)

        repo = installer.run()

        if not dry_run:

            pyprj_deps = self.pyproject.dependencies
            for parsed_dep in parsed_deps:
                if isinstance(parsed_dep.constraint, str):
                    constraint = parsed_dep.constraint
                    if not parsed_dep.version_specified:
                        constraint = f"^{repo.find_packages(parsed_dep.dependency)[0].version}"
                else:
                    constraint = inline_table()
                    constraint.update(parsed_dep.constraint)
                    if not parsed_dep.version_specified:
                        constraint['version'] = f"^{repo.find_packages(parsed_dep.dependency)[0].version}"

                pyprj_deps[parsed_dep.dependency.name] = constraint

            self.pyproject.save()

            # reload package to reflect changes
            from poetry.factory import Factory
            self._package = Factory().create_poetry_for_pyproject(self.pyproject, env=self._env).package
            self.installer.set_package(self._package)

    @classmethod
    def load(cls, project_dir: Path, profiles: Optional[ProfilesActivationData] = None):
        from poetry.factory import Factory
        # TODO: remove the "factory" class and scatter operations into their appropriate place
        return Factory().create_poetry(project_dir, profiles=profiles)
