from poetry.console import console
from poetry.console.commands.command import Command


class InstallCommand(Command):
    """
    install project dependencies

    install
        {--sync : Synchronize the environment with the locked packages and the specified groups.}
        {--dry-run : Output the operations but do not execute anything (implicitly enables --verbose).}
        {--extras=* : Extra sets of dependencies to install.}
        {--update : update the given packages to the last compatible version }
        {--lock-only : Do not perform operations (only update the lockfile). }
        {--editable : Add vcs/path dependencies as editable.}
        {--optional : add packages as an optional dependencies. }
        {--python= : Python version for which the dependency must be installed. }
        {--platform= : Platforms for which the dependency must be installed. }
        {--source= : Name of the source to use to install the package.}
        {--allow-prereleases : Accept prereleases.}
        {packages?* : The packages to add. }
    """

    help = """
    install project dependencies
    If you do not specify a version constraint, rp will choose a suitable one based on the available package versions.

    You can specify a package in the following forms:
      - A single name (<b>requests</b>)
      - A name and a constraint (<b>requests@^2.23.0</b>)
      - A git url (<b>git+https://github.com/python-poetry/poetry.git</b>)
      - A git url with a revision (<b>git+https://github.com/python-poetry/poetry.git#develop</b>)
      - A git SSH url (<b>git+ssh://github.com/python-poetry/poetry.git</b>)
      - A git SSH url with a revision (<b>git+ssh://github.com/python-poetry/poetry.git#develop</b>)
      - A file path (<b>../my-package/my-package.whl</b>)
      - A directory (<b>../my-package/</b>)
      - A url (<b>https://example.com/packages/my-package-0.1.0.tar.gz</b>)
    """

    def handle(self) -> int:
        from poetry.app.relaxed_poetry import rp

        project = rp.active_project

        for subp in project.projects_graph():
            if subp.env:
                subp.install(
                    self.argument("packages"),
                    synchronize=self.option("sync"),
                    dry_run=self.option("dry-run"),
                    extras_strings=self.option("extras"),
                    update=self.option("update"),
                    lock_only=self.option("lock-only"),
                    editable=self.option("editable"),
                    optional=self.option("optional"),
                    python=self.option("python"),
                    platform=self.option("platform"),
                    source=self.option("source"),
                    allow_prereleases=self.option("allow-prereleases")
                )
            else:
                console.println(
                    f"<info>Skipping {subp.pyproject.name}, it does not requires python interpreter and therefore cannot have dependencies.</>\n"
                    "To change that, add a python dependency to <c1>pyproject.toml</c1>")

        return 0
