from cleo.helpers import argument

from ..command import Command
from ... import console


class EnvUseCommand(Command):

    name = "env use"
    description = "Activates or creates a new virtualenv for the current project."

    arguments = [argument("python", "The python executable to use.")]

    def handle(self) -> int:
        if self.poetry.pyproject.is_parent():
            console.println("This command is not applicable for parent projects")
            return 1

        from poetry.utils.env import EnvManager

        manager = EnvManager(self.poetry)

        if self.argument("python") == "system":
            manager.deactivate(self._io)

            return 0

        env = manager.activate(self.argument("python"), self._io)

        self.line("Using virtualenv: <comment>{}</>".format(env.path))

        return 0
