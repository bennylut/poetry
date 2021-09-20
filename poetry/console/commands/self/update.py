from cleo.helpers import argument
from cleo.helpers import option

from poetry.app.relaxed_poetry import rp
from ..command import Command


class SelfUpdateCommand(Command):
    name = "self update"
    description = "Updates Relaxed-Poetry to the latest version."

    arguments = [argument("version", "The version to update to.", optional=True)]
    options = [
        option(
            "dry-run",
            None,
            "Output the operations but do not execute anything "
            "(implicitly enables --verbose).",
        ),
    ]

    def handle(self) -> int:
        rp.update_installation(self.argument("version"), self.option("dry-run"))
        return 0
