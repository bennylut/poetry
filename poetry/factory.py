from __future__ import absolute_import
from __future__ import unicode_literals

from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import TYPE_CHECKING

from cleo.io.io import IO
from cleo.io.outputs.output import Verbosity
from poetry.core.factory import Factory as BaseFactory
from poetry.core.poetry import Poetry
from poetry.core.pyproject.profiles import ProfilesActivationRequest
from poetry.core.pyproject.project import Project
from poetry.core.utils import toml

from .config.config import Config
from .console import console
from .managed_project import ManagedProject
from .packages.locker import Locker, NullLocker
from .packages.project_package import ProjectPackage
from .repositories.pypi_repository import PyPiRepository

if TYPE_CHECKING:
    from .repositories.legacy_repository import LegacyRepository
    from .utils.env import Env


class Factory(BaseFactory):
    """
    Factory class to create various elements needed by Poetry.
    """

    def create_poetry_for_pyproject(
            self, project: Project, *,
            env: Optional["Env"] = None):

        base_poetry = super(Factory, self).create_poetry_for_pyproject(project)
        return self._upgrade(base_poetry, env=env)

    def create_poetry(
            self,
            cwd: Optional[Path] = None,
            profiles: Optional[ProfilesActivationRequest] = None
    ) -> ManagedProject:

        console.println(f"Loading managed project from directory: {cwd} with profiles activation: {profiles}", Verbosity.DEBUG)

        base_poetry = super(Factory, self).create_poetry(cwd, profiles=profiles)
        return self._upgrade(base_poetry)

    def _upgrade(
            self,
            base_poetry: Poetry,
            env: Optional["Env"] = None):

        io = console.io

        if base_poetry.pyproject.is_stored():
            locker = Locker(
                base_poetry.pyproject.project_management_files / "lock.toml", base_poetry.local_config
            )
        else:
            # TODO: why do we needs to supply a file if it is a null locker???
            locker = NullLocker("/non-existing-file.lock", {})

        # Loading global configuration
        config = Config.load_global()

        # Loading local configuration

        def apply_config(p: Project):
            if p.parent:
                apply_config(p.parent)

            if p.is_stored():
                local_config_file = base_poetry.pyproject.project_management_files / "config.toml"
                if local_config_file.exists():
                    if io.is_debug():
                        io.write_line(
                            "Loading configuration file {}".format(local_config_file)
                        )

                    config_data,_ = toml.load(local_config_file)
                    config.merge(config_data)

        apply_config(base_poetry.pyproject)

        # Load local sources
        repositories = {}
        existing_repositories = config.get("repositories", {})
        for source in base_poetry.pyproject.poetry_config.get("source", []):
            name = source.get("name")
            url = source.get("url")
            if name and url:
                if name not in existing_repositories:
                    repositories[name] = {"url": url}

        config.merge({"repositories": repositories})

        poetry = ManagedProject(
            base_poetry.pyproject,
            base_poetry.package,
            locker,
            config,
            env=env
        )

        # Configuring sources
        self.configure_sources(
            poetry, poetry.local_config.get("source", []), config, io
        )

        return poetry

    @classmethod
    def get_package(cls, name: str, version: str) -> ProjectPackage:
        return ProjectPackage(name, version, version)

    @classmethod
    def configure_sources(
            cls, poetry: "ManagedProject", sources: List[Dict[str, str]], config: "Config", io: "IO"
    ) -> None:
        for source in sources:
            repository = cls.create_legacy_repository(source, config)
            is_default = source.get("default", False)
            is_secondary = source.get("secondary", False)
            if io.is_debug():
                message = "Adding repository {} ({})".format(
                    repository.name, repository.url
                )
                if is_default:
                    message += " and setting it as the default one"
                elif is_secondary:
                    message += " and setting it as secondary"

                io.write_line(message)

            poetry.pool.add_repository(repository, is_default, secondary=is_secondary)

        # Put PyPI last to prefer private repositories
        # unless we have no default source AND no primary sources
        # (default = false, secondary = false)
        if poetry.pool.has_default():
            if io.is_debug():
                io.write_line("Deactivating the PyPI repository")
        else:
            default = not poetry.pool.has_primary_repositories()
            poetry.pool.add_repository(PyPiRepository(), default, not default)

    @classmethod
    def create_legacy_repository(
            cls, source: Dict[str, str], auth_config: Config
    ) -> "LegacyRepository":
        from .repositories.legacy_repository import LegacyRepository
        from .utils.helpers import get_cert
        from .utils.helpers import get_client_cert

        if "url" in source:
            # PyPI-like repository
            if "name" not in source:
                raise RuntimeError("Missing [name] in source.")
        else:
            raise RuntimeError("Unsupported source specified")

        name = source["name"]
        url = source["url"]

        return LegacyRepository(
            name,
            url,
            config=auth_config,
            cert=get_cert(auth_config, name),
            client_cert=get_client_cert(auth_config, name),
        )
