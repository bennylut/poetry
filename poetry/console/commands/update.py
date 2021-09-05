from cleo.helpers import argument
from cleo.helpers import option

from .installer_command import InstallerCommand
from .. import console


class UpdateCommand(InstallerCommand):

    name = "update"
    description = (
        "Update the dependencies as according to the <comment>pyproject.toml</> file."
    )

    arguments = [
        argument("packages", "The packages to update", optional=True, multiple=True)
    ]
    options = [
        option("no-dev", None, "Do not update the development dependencies."),
        option(
            "dry-run",
            None,
            "Output the operations but do not execute anything "
            "(implicitly enables --verbose).",
        ),
        option("lock", None, "Do not perform operations (only update the lockfile)."),
    ]

    loggers = ["poetry.repositories.pypi_repository"]

    def handle(self) -> int:
        packages = self.argument("packages")

        for poetry in self.poetry.all_sub_poetries():

            console.println(f"Updating project: <c1>{poetry.pyproject.name}</c1>")

            if packages:
                poetry.installer.whitelist({name: "*" for name in packages})

            if self.option("no-dev"):
                poetry.installer.with_groups(["dev"])

            poetry.installer.dry_run(self.option("dry-run"))
            poetry.installer.execute_operations(not self.option("lock"))

            # Force update
            poetry.installer.update(True)

            exit_code = poetry.installer.run()
            if exit_code != 0:
                return exit_code

        return 0
