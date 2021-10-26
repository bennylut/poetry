from poetry.console import console
from poetry.console.commands.command import Command


class RemoveCommand(Command):
    """
    Removes a package from the project dependencies.

    remove
        {--dry-run : Output the operations but do not execute anything (implicitly enables --verbose).}
        {--without-deps : Remove only the given packages, dont remove their dependencies }
        {packages?* : The packages to remove. }
    """

    help = """
    The <info>remove</info> command removes a package from the current
    list of installed packages

    <info>rp remove</info>
    """

    def handle(self) -> int:
        from poetry.app.relaxed_poetry import rp

        project = rp.active_project
        if not project.env:
            console.println(
                "<error>This project does not requires python interpreter and therefore cannot have dependencies.</>\n"
                "To change that, add a python dependency to <c1>pyproject.toml</c1>")
            return 1

        project.remove_dependencies(
            self.argument("packages"),
            include_deps=not self.option("without-deps"),
            dry_run=self.option("dry-run"),
        )

        return 0
