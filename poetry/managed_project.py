from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Optional
from typing import List

from cleo.io.outputs.output import Verbosity
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
        self._plugin_manager: Optional["PluginManager"] = None
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

    @cached_property
    def installer(self) -> Optional["Installer"]:

        if self.env is None:
            return None

        installer = Installer(self)

        installer.use_executor(self.config.get("experimental.new-installer", False))
        return installer

    def set_locker(self, locker: "Locker") -> "ManagedProject":
        self._locker = locker

        return self

    def set_pool(self, pool: "Pool") -> "ManagedProject":
        self._pool = pool

        return self

    def set_config(self, config: "Config") -> "ManagedProject":
        self._config = config

        return self

    def set_plugin_manager(self, plugin_manager: "PluginManager") -> "ManagedProject":
        self._plugin_manager = plugin_manager

        return self

    def get_sources(self) -> List[Source]:
        return [
            Source(**source)
            for source in self.pyproject.poetry_config.get("source", [])
        ]

    def _load_related_project(self, pyprj: PyProject) -> "ManagedProject":
        from poetry.factory import Factory
        plugins_disabled = self._plugin_manager.is_plugins_disabled() if self._plugin_manager else True
        return Factory().create_poetry_for_pyproject(pyprj, disable_plugins=plugins_disabled)

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
