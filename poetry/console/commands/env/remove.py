from cleo.helpers import argument

from ..command import Command
from ... import console


class EnvRemoveCommand(Command):
    name = "env remove"
    description = "Removes a specific virtualenv associated with the project."

    arguments = [
        argument("python", "The python executable to remove the virtualenv for.")
    ]

    def handle(self) -> int:
        if self.poetry.env is None:
            console.println(
                "<error>This project does not requires python interpreter and therefore cannot have virtual-envs.</>\n"
                "To change that, add a python dependency to <c1>pyproject.toml</c1>")
            return 1

        from poetry.utils.env import EnvManager

        manager = EnvManager(self.poetry)
        venv = manager.remove(self.argument("python"))

        self.line("Deleted virtualenv: <comment>{}</comment>".format(venv.path))
        return 0
