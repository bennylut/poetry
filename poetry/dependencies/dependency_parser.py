import os
import re
import urllib.parse
from pathlib import Path
from typing import Dict, Optional, Any, List, Union
from typing import TYPE_CHECKING

from dataclasses import dataclass
from poetry.core.pyproject.exceptions import PyProjectException
from poetry.core.semver.helpers import parse_constraint
from poetry.factory import Factory
from poetry.managed_project import ManagedProject

if TYPE_CHECKING:
    from poetry.core.packages.types import DependencyTypes


@dataclass
class ParsedDependency:
    dependency: "DependencyTypes"
    spec: Union[Dict[str, Any], str]
    version_specified: bool


class DependencyParser:

    def __init__(self, project: ManagedProject):
        try:
            self._base_path = project.file.parent
        except (PyProjectException, RuntimeError):
            self._base_path = Path.cwd()

        self._project = project

    def parse(
            self,
            requires: str,
            allow_prereleases: bool = False,
            source: Optional[str] = None,
            optional: bool = False,
            extras_strings: Optional[List[str]] = None,
            editable: bool = False,
            python: Optional[str] = None,
            platform: Optional[str] = None
    ) -> ParsedDependency:

        requirement = self._parse_requirement(requires)
        version_specified = True
        if "git" in requirement or "url" in requirement or "path" in requirement:
            pass
        elif "version" not in requirement:
            requirement["version"] = "*"
            version_specified = False

        if "version" in requirement:
            # Validate version constraint
            parse_constraint(requirement["version"])

        constraint = {}
        for name, value in requirement.items():
            if name == "name":
                continue

            constraint[name] = value

        if optional:
            constraint["optional"] = True

        if allow_prereleases:
            constraint["allow-prereleases"] = True

        if extras_strings:
            extras = []
            for extra in extras_strings:
                if " " in extra:
                    extras += [e.strip() for e in extra.split(" ")]
                else:
                    extras.append(extra)

            constraint["extras"] = extras

        if editable:
            if "git" in requirement or "path" in requirement:
                constraint["develop"] = True
            else:
                raise ValueError("Only vcs/path dependencies support editable installs. "
                                 f"{requirement['name']} is neither.")

        if python:
            constraint["python"] = python

        if platform:
            constraint["platform"] = platform

        if source:
            constraint["source"] = source

        if len(constraint) == 1 and "version" in constraint:
            constraint = constraint["version"]

        return ParsedDependency(
            Factory.create_dependency(
                requirement["name"],
                constraint,
                root_dir=self._base_path,
                project=self._project.pyproject
            ),

            constraint,

            version_specified
        )

    def _parse_requirement(self, requirement: str) -> Dict[str, str]:
        from poetry.puzzle.provider import Provider

        cwd = self._base_path

        requirement = requirement.strip()
        extras = []
        extras_m = re.search(r"\[([\w\d,-_ ]+)\]$", requirement)
        if extras_m:
            extras = [e.strip() for e in extras_m.group(1).split(",")]
            requirement, _ = requirement.split("[")

        url_parsed = urllib.parse.urlparse(requirement)
        if url_parsed.scheme and url_parsed.netloc:
            # Url
            if url_parsed.scheme in ["git+https", "git+ssh"]:
                from poetry.core.vcs.git import Git
                from poetry.core.vcs.git import ParsedUrl

                parsed = ParsedUrl.parse(requirement)
                url = Git.normalize_url(requirement)

                pair = dict([("name", parsed.name), ("git", url.url)])
                if parsed.rev:
                    pair["rev"] = url.revision

                if extras:
                    pair["extras"] = extras

                package = Provider.get_package_from_vcs(
                    "git", url.url, rev=pair.get("rev")
                )
                pair["name"] = package.name

                return pair
            elif url_parsed.scheme in ["http", "https"]:
                package = Provider.get_package_from_url(requirement)

                pair = dict([("name", package.name), ("url", package.source_url)])
                if extras:
                    pair["extras"] = extras

                return pair
        elif (os.path.sep in requirement or "/" in requirement) and (
                cwd.joinpath(requirement).exists()
                or Path(requirement).expanduser().exists()
                and Path(requirement).expanduser().is_absolute()
        ):
            path = Path(requirement).expanduser()
            is_absolute = path.is_absolute()

            if not path.is_absolute():
                path = cwd.joinpath(requirement)

            if path.is_file():
                package = Provider.get_package_from_file(path.resolve())
            else:
                package = Provider.get_package_from_directory(path.resolve())

            return dict(
                [
                    ("name", package.name),
                    (
                        "path",
                        path.relative_to(cwd).as_posix()
                        if not is_absolute
                        else path.as_posix(),
                    ),
                ]
                + ([("extras", extras)] if extras else [])
            )

        pair = re.sub(
            "^([^@=: ]+)(?:@|==|(?<![<>~!])=|:| )(.*)$", "\\1 \\2", requirement
        )
        pair = pair.strip()

        require = dict()
        if " " in pair:
            name, version = pair.split(" ", 2)
            extras_m = re.search(r"\[([\w\d,-_]+)\]$", name)
            if extras_m:
                extras = [e.strip() for e in extras_m.group(1).split(",")]
                name, _ = name.split("[")

            require["name"] = name
            if version != "latest":
                require["version"] = version
        else:
            m = re.match(
                r"^([^><=!: ]+)((?:>=|<=|>|<|!=|~=|~|\^).*)$", requirement.strip()
            )
            if m:
                name, constraint = m.group(1), m.group(2)
                extras_m = re.search(r"\[([\w\d,-_]+)\]$", name)
                if extras_m:
                    extras = [e.strip() for e in extras_m.group(1).split(",")]
                    name, _ = name.split("[")

                require["name"] = name
                require["version"] = constraint
            else:
                extras_m = re.search(r"\[([\w\d,-_]+)\]$", pair)
                if extras_m:
                    extras = [e.strip() for e in extras_m.group(1).split(",")]
                    pair, _ = pair.split("[")

                require["name"] = pair

        if extras:
            require["extras"] = extras

        return require
