from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Optional
from typing import List

from poetry.core.pyproject.toml import PyProject
from poetry.core.utils.props_ext import cached_property

from poetry.__version__ import __version__
from poetry.config.source import Source
from poetry.core.poetry import Poetry as BasePoetry

from .console import console
from .installation import Installer


if TYPE_CHECKING:
    from poetry.core.packages.project_package import ProjectPackage

    from .config.config import Config
    from .packages.locker import Locker
    from .plugins.plugin_manager import PluginManager
    from .repositories.pool import Pool
    from .utils.env import Env


class Poetry(BasePoetry):
    VERSION = __version__

    def __init__(
            self,
            file: Path,
            pyproject: PyProject,
            package: "ProjectPackage",
            locker: "Locker",
            config: "Config",
    ):
        from .repositories.pool import Pool  # noqa

        super(Poetry, self).__init__(file, pyproject, package)

        self._locker = locker
        self._config = config
        self._pool = Pool()
        self._plugin_manager: Optional["PluginManager"] = None

    @property
    def locker(self) -> "Locker":
        return self._locker

    @property
    def pool(self) -> "Pool":
        return self._pool

    @property
    def config(self) -> "Config":
        return self._config

    @cached_property
    def env(self) -> Optional["Env"]:
        from .utils.env import Env, EnvManager
        if self.pyproject.is_parent():
            return None

        env_manager = EnvManager(self)
        env = env_manager.create_venv()

        console.println(f"Using virtualenv: <comment>{env.path}</>", "verbose")
        return env

    @cached_property
    def installer(self) -> Optional["Installer"]:
        if self.pyproject.is_parent():
            return None

        installer = Installer(
            console.io,
            self.env,
            self.package,
            self.locker,
            self.pool,
            self.config,
        )

        installer.use_executor(self.config.get("experimental.new-installer", False))
        return installer

    def set_locker(self, locker: "Locker") -> "Poetry":
        self._locker = locker

        return self

    def set_pool(self, pool: "Pool") -> "Poetry":
        self._pool = pool

        return self

    def set_config(self, config: "Config") -> "Poetry":
        self._config = config

        return self

    def set_plugin_manager(self, plugin_manager: "PluginManager") -> "Poetry":
        self._plugin_manager = plugin_manager

        return self

    def get_sources(self) -> List[Source]:
        return [
            Source(**source)
            for source in self.pyproject.poetry_config.get("source", [])
        ]

    def all_sub_poetries(self) -> Iterator["Poetry"]:
        from poetry.factory import Factory
        if self.pyproject.is_parent():
            plugins_disabled = self._plugin_manager.is_plugins_disabled() if self._plugin_manager else True

            for subproject in self.pyproject.sub_projects.values():
                subpoetry = Factory().create_poetry_for_pyproject(subproject, disable_plugins=plugins_disabled)
                yield from subpoetry.all_sub_poetries()
        else:
            yield self
