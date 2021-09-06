from cleo.helpers import option

from .installer_command import InstallerCommand
from .. import console


class LockCommand(InstallerCommand):

    name = "lock"
    description = "Locks the project dependencies."

    options = [
        option(
            "no-update", None, "Do not update locked versions, only refresh lock file."
        ),
        option(
            "check",
            None,
            "Check that the <comment>etc/rp/lock.toml</> file corresponds to the current version "
            "of <comment>pyproject.toml</>.",
        ),
    ]

    help = """
The <info>lock</info> command reads the <comment>pyproject.toml</> file from the
current directory, processes it, and locks the dependencies in the <comment>etc/lock.toml</>
file.

<info>rp lock</info>
"""

    loggers = ["poetry.repositories.pypi_repository"]

    def handle(self) -> int:

        for poetry in self.poetry.all_sub_poetries():

            console.println(f"locking project: <c1>{poetry.pyproject.name}</c1>")

            if self.option("check") :
                if not (poetry.locker.is_locked() and poetry.locker.is_fresh()):
                    return 1
            else:
                poetry.installer.lock(update=not self.option("no-update"))
                exit_code = poetry.installer.run()
                if exit_code != 0:
                    return exit_code

        return 0

