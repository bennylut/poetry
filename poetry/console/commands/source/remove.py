from typing import Optional, Dict, Any

from cleo.helpers import argument
from poetry.core.pyproject.tables import SOURCES_TABLE
from poetry.core.utils.collections import nested_dict_set

from poetry.config.source import Source
from poetry.console.commands.command import Command


class SourceRemoveCommand(Command):

    name = "source remove"
    description = "Remove source configured for the project."

    arguments = [
        argument(
            "name",
            "Source repository name.",
        ),
    ]

    @staticmethod
    def source_to_table(source: Source) -> Dict[str, Any]:
        source_table: Dict[str, Any] = {}
        for key, value in source.to_dict().items():
            source_table[key] = value
        return source_table

    def handle(self) -> Optional[int]:
        name = self.argument("name")

        sources = []
        removed = False

        for source in self.poetry.get_sources():
            if source.name == name:
                self.line(f"Removing source with name <c1>{source.name}</c1>.")
                removed = True
                continue
            sources.append(self.source_to_table(source))

        if not removed:
            self.line_error(
                f"<error>Source with name <c1>{name}</c1> was not found.</error>"
            )
            return 1

        with self.poetry.pyproject.edit() as data:
            nested_dict_set(data, SOURCES_TABLE, sources)

        return 0
