from pathlib import Path
from typing import Dict, List, Optional
import os

from poetry.core.pyproject.profiles import ProfilesActivationData
from poetry.core.semver.version import Version
from poetry.core.utils.props_ext import cached_property

from poetry.app.relaxed_poetry_updater import RelaxedPoetryUpdater
from poetry.console import console
from poetry.locations import CONFIG_DIR, CACHE_DIR
from poetry.managed_project import ManagedProject
from poetry.repositories.artifacts import Artifacts
from poetry.templates.template_executor import TemplateExecutor
from poetry.utils.appdirs import user_data_dir
from poetry.__version__ import __version__


class RelaxedPoetry:
    _instance: "RelaxedPoetry" = None

    def __init__(self):
        self._active_project: Optional[ManagedProject] = None
        self._template_executor = TemplateExecutor(self)
        self._updater = RelaxedPoetryUpdater(self)
        self.artifacts = Artifacts(Path(CACHE_DIR) / "artifacts")

    def activate_project(self, path: Path, command: str = "build", plugins_disabled: bool = False):

        from poetry.factory import Factory
        io = console.io

        if io.input.has_option("profiles"):
            manual_profiles = [s for s in (io.input.option("profiles") or "").split(",") if len(s) > 0]
        else:
            manual_profiles = []

        profile_activation = ProfilesActivationData(manual_profiles, command)

        try:
            self._active_project = Factory().create_poetry(
                path, io=io, disable_plugins=plugins_disabled, profiles=profile_activation
            )
        except RuntimeError as err:
            if command != "new":
                raise FileNotFoundError("could not find project to activate") from err

    def has_active_project(self) -> bool:
        return self._active_project is not None

    @property
    def active_project(self) -> ManagedProject:
        return self._active_project

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
