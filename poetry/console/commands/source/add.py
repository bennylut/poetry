from typing import Optional, List, Any

from cleo.helpers import argument
from cleo.helpers import option
from cleo.io.null_io import NullIO
from poetry.core.utils.collections import nested_dict_set, nested_dict_get

from poetry.config.source import Source
from poetry.console.commands.command import Command
from poetry.factory import Factory
from poetry.repositories import Pool


class SourceAddCommand(Command):
    name = "source add"
    description = "Add source configuration for project."

    arguments = [
        argument(
            "name",
            "Source repository name.",
        ),
        argument("url", "Source repository url."),
    ]

    options = [
        option(
            "default",
            "d",
            "Set this source as the default (disable PyPI). A "
            "default source will also be the fallback source if "
            "you add other sources.",
        ),
        option("secondary", "s", "Set this source as secondary."),
    ]

    def handle(self) -> Optional[int]:
        name = self.argument("name")
        url = self.argument("url")
        is_default = self.option("default")
        is_secondary = self.option("secondary")

        if is_default and is_secondary:
            self.line_error(
                "Cannot configure a source as both <c1>default</c1> and <c1>secondary</c1>."
            )
            return 1

        new_source = Source(
            name=name, url=url, default=is_default, secondary=is_secondary
        )
        existing_sources = self.poetry.get_sources()

        for source in existing_sources:
            if source.name == new_source.name:
                self.line(
                    f"Source with name <c1>{name}</c1> already exits. Skipping addition."
                )
                return 0
            elif source.default and is_default:
                self.line_error(
                    f"<error>Source with name <c1>{source.name}</c1> is already set to default. "
                    f"Only one default source can be configured at a time.</error>"
                )
                return 1

        self.line(f"Adding source with name <c1>{name}</c1>.")
        new_source_dict = new_source.to_dict()

        # ensure new source is valid. eg: invalid name etc.
        self.poetry._pool = Pool()
        try:
            Factory.configure_sources(
                self.poetry, [new_source_dict], self.poetry.config, NullIO()
            )
            self.poetry.pool.repository(name)
        except ValueError as e:
            self.line_error(
                f"<error>Failed to validate addition of <c1>{name}</c1>: {e}</error>"
            )
            return 1

        sources_path = ['tool', 'poetry', 'source']
        with self.poetry.pyproject.edit() as data:
            lst: List[Any] = nested_dict_get(data, sources_path)
            if not lst:
                lst = [new_source_dict]
                nested_dict_set(data, sources_path, lst)
            else:
                lst.append(new_source_dict)
        return 0
