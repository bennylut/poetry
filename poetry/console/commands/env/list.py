from cleo.helpers import option

from ..command import Command
from ... import console


class EnvListCommand(Command):

    name = "env list"
    description = "Lists all virtualenvs associated with the current project."

    options = [option("full-path", None, "Output the full paths of the virtualenvs.")]

    def handle(self) -> int:
        if self.poetry.pyproject.is_parent():
            console.println("This command is not applicable for parent projects")
            return 1

        from poetry.utils.env import EnvManager

        manager = EnvManager(self.poetry)
        current_env = manager.get()

        for venv in manager.list():
            name = venv.path.name
            if self.option("full-path"):
                name = str(venv.path)

            if venv == current_env:
                self.line("<info>{} (Activated)</info>".format(name))

                continue

            self.line(name)

        return 0