from pathlib import Path
from typing import List, Union, MutableMapping
from typing import TYPE_CHECKING, Iterator, Optional

from cleo.io.outputs.output import Verbosity
from poetry.core.masonry.utils.module import ModuleOrPackageNotFound
from poetry.core.packages.dependency import Dependency
from poetry.core.poetry import Poetry as BasePoetry
from poetry.core.pyproject.profiles import ProfilesActivationRequest
from poetry.core.pyproject.project import Project
from poetry.core.pyproject.tables import DEPENDENCIES_TABLE
from poetry.core.utils.collections import nested_dict_get, nested_dict_set
from poetry.core.utils.props_ext import cached_property

from poetry.__version__ import __version__
from poetry.config.source import Source
from .console import console
from .installation import Installer
from .installation.operations import Uninstall
from .masonry.builders import EditableBuilder
from .utils.authenticator import Authenticator

if TYPE_CHECKING:
    from poetry.core.packages.project_package import ProjectPackage

    from .config.config import Config
    from .packages.locker import Locker
    from .repositories.pool import Pool
    from .utils.env import Env


class ManagedProject(BasePoetry):
    VERSION = __version__

    def __init__(
            self,
            pyproject: Project,
            package: "ProjectPackage",
            locker: "Locker",
            config: "Config",
            env: Optional["Env"] = None,
    ):
        from .repositories.pool import Pool  # noqa

        super(ManagedProject, self).__init__(pyproject, package)

        self._locker = locker
        self._config = config
        self._pool = Pool()  # TODO: do we really needs that?
        self._env = env
        self._installed_repository = None

    def __str__(self):
        return f"ManagedProject(name={self.pyproject.name}, path={self.path})"

    def __repr__(self):
        return str(self)

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

    def _load_related_project(self, pyprj: Project) -> "ManagedProject":
        from poetry.factory import Factory
        return Factory().create_poetry_for_pyproject(pyprj)

    def projects_graph(self) -> Iterator["ManagedProject"]:
        if self.pyproject.is_parent():
            for subproject in self.pyproject.sub_projects.values():
                yield from self._load_related_project(subproject).projects_graph()

        yield self

    @cached_property
    def parent(self) -> Optional["ManagedProject"]:
        parent = self.pyproject.parent
        if parent:
            return self._load_related_project(parent)
        return None

    @property
    def installed_repository(self):
        if not self._installed_repository:
            from .repositories.installed_repository import InstalledRepository
            self._installed_repository = InstalledRepository.load(self.env)

        return self._installed_repository

    def remove_dependencies(
            self, names: List[str], *,
            dry_run: bool = False, include_deps: bool = True):

        modified_package = self.package.clone()

        for name in names:
            modified_package.remove_dependency(name)

        installer = self._create_installer(modified_package)
        installer.dry_run(dry_run)
        installer.verbose(True)

        if include_deps:
            installer.update(True)
            installer.whitelist(names)

            installer.run()
        else:
            executor = installer.executor
            installed = self.installed_repository

            installed_packages = {p.name: p for p in installed.packages}
            ops = [Uninstall(installed_packages[name]) for name in names if name in installed_packages]

            executor.execute(ops)

        if not dry_run:  # update pyproject
            with self.pyproject.edit() as data:
                dependencies = nested_dict_get(data, DEPENDENCIES_TABLE)
                if isinstance(dependencies, MutableMapping):
                    for name in names:
                        dependencies.pop(name, None)

        # drop installed repository so that it will get reloaded if anyone needs it
        self._installed_repository = None

    def install(
            self, dependencies: List[str], *, synchronize: bool = False, lock_only: bool = False, update: bool = False,
            dry_run: bool = False, allow_prereleases: bool = False, source: Optional[str] = None,
            optional: bool = False, extras_strings: Optional[List[str]] = None,
            editable: bool = False, python: Optional[str] = None, platform: Optional[str] = None):

        kwargs = {
            "allow_prereleases": allow_prereleases, "source": source, "optional": optional,
            "extras_strings": extras_strings, "editable": editable, "python": python, "platform": platform,
        }

        from .dependencies.dependency_parser import DependencyParser

        modified_package: ProjectPackage = self.package.clone()

        dparser = DependencyParser(self)
        parsed_deps = [dparser.parse(dependency, **kwargs) for dependency in dependencies]

        existing_dependencies = {dependency.name: dependency for dependency in modified_package.all_requires}
        for parsed_dep in parsed_deps:
            if parsed_dep.dependency.name in existing_dependencies:
                if update:
                    existing_dependency: Dependency = existing_dependencies[parsed_dep.dependency.name]
                    modified_package.remove_dependency(existing_dependency.name)
                else:
                    if parsed_dep.spec != '*':
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
        repo = installer.run()

        if not dry_run:
            try:
                builder = EditableBuilder(self, self.env, console.io)
                console.println(
                    f"<b>Installing</> the current project: <c1>{self.package.pretty_name}</c1> "
                    f"(<c2>{self.package.pretty_version}</c2>)"
                )
                builder.build()
            except ModuleOrPackageNotFound:
                # This is likely due to the fact that the project is an application
                # not following the structure expected by Poetry
                # If this is a true error it will be picked up later by build anyway.
                pass


            with self.pyproject.edit() as data:

                dependencies = nested_dict_get(data, DEPENDENCIES_TABLE)
                if not dependencies:
                    dependencies = {}
                    nested_dict_set(data, DEPENDENCIES_TABLE, dependencies)

                for parsed_dep in parsed_deps:
                    if not parsed_dep.version_specified:
                        required_version = f"^{repo.find_packages(parsed_dep.dependency)[0].version}"
                        if isinstance(parsed_dep.spec, str):
                            parsed_dep.spec = required_version
                        else:
                            parsed_dep.spec['version'] = required_version

                    dependencies[parsed_dep.dependency.name] = parsed_dep.spec

            # reload package to reflect changes
            from poetry.factory import Factory
            self._package = Factory().create_poetry_for_pyproject(self.pyproject, env=self._env).package
            self.installer.set_package(self._package)

            # drop installed repository so that it will get reloaded if anyone needs it
            self._installed_repository = None

    @classmethod
    def load(cls, project_dir: Union[str, Path], profiles: Optional[ProfilesActivationRequest] = None):
        project_dir = Path(project_dir)
        from poetry.factory import Factory
        # TODO: remove the "factory" class and scatter operations into their appropriate place
        return Factory().create_poetry(project_dir, profiles=profiles)
