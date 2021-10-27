import os
from pathlib import Path
from typing import Dict, List, Optional

from poetry.__version__ import __version__
from poetry.app.relaxed_poetry_updater import RelaxedPoetryUpdater
from poetry.config.config import Config
from poetry.console import console
from poetry.core.pyproject.profiles import ProfilesActivationRequest
from poetry.core.semver.version import Version
from poetry.core.utils.props_ext import cached_property
from poetry.locations import CACHE_DIR
from poetry.managed_project import ManagedProject
from poetry.plugins.plugin_manager import PluginManager
from poetry.repositories.artifacts import Artifacts
from poetry.templates.template_executor import TemplateExecutor
from poetry.utils.appdirs import user_data_dir
from poetry.utils.authenticator import Authenticator


class RelaxedPoetry:
    _instance: "RelaxedPoetry" = None

    def __init__(self):
        self._active_project: Optional[ManagedProject] = None
        self._template_executor = TemplateExecutor(self)
        self._updater = RelaxedPoetryUpdater(self)
        self.artifacts = Artifacts(Path(CACHE_DIR) / "artifacts")
        self._plugin_manager: Optional[PluginManager] = None

    def activate_plugins(self, disable_plugins: bool = False):
        if self._plugin_manager:
            return
        plugin_manager = PluginManager("plugin", disable_plugins=disable_plugins)
        plugin_manager.load_plugins()
        self._plugin_manager = plugin_manager

        if self._active_project:
            plugin_manager.activate(self._active_project, console.io)

    def activate_project(self, path: Path, command: str = "build"):

        from poetry.factory import Factory
        io = console.io

        if io.input.has_option("profiles"):
            manual_profiles = [s for s in (io.input.option("profiles") or "").split(",") if len(s) > 0]
        else:
            manual_profiles = []

        profile_activation = ProfilesActivationRequest.from_commandline(command, manual_profiles)

        try:
            self._active_project = Factory().create_poetry(
                path, profiles=profile_activation
            )

            if self._plugin_manager:
                self._plugin_manager.activate(self._active_project)

        except RuntimeError as err:
            if command not in ("new", "init"):
                raise FileNotFoundError("could not find project to activate") from err

    def has_active_project(self) -> bool:
        return self._active_project is not None

    @property
    def active_project(self) -> ManagedProject:
        return self._active_project

    @cached_property
    def config(self) -> Config:
        return Config.load_global()

    @cached_property
    def authenticator(self) -> Authenticator:
        return Authenticator(self.config, console.io)

    def execute_template(
            self, descriptor: str, out_path: Path,
            args: List[str], kwargs: Dict[str, str],
            allow_override: bool
    ):
        self._template_executor.execute(descriptor, out_path, args, kwargs, allow_override)

    def document_template(self, descriptor: str) -> str:
        return self._template_executor.document(descriptor)

    def update_installation(self, version: Optional[str], dry_run: bool) -> bool:
        return self._updater.update(version, dry_run)

    @staticmethod
    def installation_dir() -> Path:
        if os.getenv("RP_HOME"):
            return Path(os.getenv("RP_HOME")).expanduser()

        return Path(user_data_dir("relaxed-poetry", roaming=True))

    @cached_property
    def version(self):
        return Version.parse(__version__)


rp = RelaxedPoetry()
