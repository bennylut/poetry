from pathlib import Path
from typing import TYPE_CHECKING
from typing import Optional
from typing import Union

from poetry.core.packages.project_package import ProjectPackage as _ProjectPackage

if TYPE_CHECKING:
    from poetry.core.semver.version import Version  # noqa


class ProjectPackage(_ProjectPackage):
    def set_version(
            self, version: Union[str, "Version"], pretty_version: Optional[str] = None
    ) -> "ProjectPackage":
        from poetry.core.semver.version import Version  # noqa

        if not isinstance(version, Version):
            self._version = Version.parse(version)
            self._pretty_version = pretty_version or version
        else:
            self._version = version
            self._pretty_version = pretty_version or version.text

        return self

    def create_pyproject(self, path: Path):
        import tomlkit

        from poetry.layouts.layout import POETRY_DEFAULT

        pyproject = tomlkit.loads(POETRY_DEFAULT)
        content = pyproject["tool"]["poetry"]

        content["name"] = self.name
        content["version"] = self.version.text
        content["description"] = self.description
        content["authors"] = self.authors

        dependency_section = content["dependencies"]
        dependency_section["python"] = self.python_versions

        for dep in self.requires:
            constraint = tomlkit.inline_table()
            if dep.is_vcs():
                constraint[dep.vcs] = dep.source_url

                if dep.reference:
                    constraint["rev"] = dep.reference
            elif dep.is_file() or dep.is_directory():
                constraint["path"] = dep.source_url
            else:
                constraint["version"] = dep.pretty_constraint

            if not dep.marker.is_any():
                constraint["markers"] = str(dep.marker)

            if dep.extras:
                constraint["extras"] = list(sorted(dep.extras))

            if len(constraint) == 1 and "version" in constraint:
                constraint = constraint["version"]

            dependency_section[dep.name] = constraint

        path.joinpath("pyproject.toml").write_text(
            pyproject.as_string(), encoding="utf-8"
        )
