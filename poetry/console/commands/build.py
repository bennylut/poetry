from cleo.helpers import option
from poetry.core.pyproject.toml import PyProject
from poetry.core.version.helpers import format_python_constraint

from .env_command import EnvCommand
from ...poetry import Poetry
from poetry.core.masonry.builder import Builder
from poetry.utils.env import EnvManager


class BuildCommand(EnvCommand):
    name = "build"
    description = "Builds a package, as a tarball and a wheel by default."

    options = [
        option("format", "f", "Limit the format to either sdist or wheel.", flag=False),
        option("keep-python-bounds", "k", "don't tighten bounds to python version requirements based on dependencies",
               flag=True)
    ]

    loggers = [
        "poetry.core.masonry.builders.builder",
        "poetry.core.masonry.builders.sdist",
        "poetry.core.masonry.builders.wheel",
    ]

    def handle(self) -> None:
        fmt = "all"
        if self.option("format"):
            fmt = self.option("format")

        for poetry in self.poetry.all_sub_poetries():
            self._build(fmt, poetry)

    def _build(self, fmt: str, poetry: Poetry):

        package = poetry.package
        self.line(
            "Building <c1>{}</c1> (<c2>{}</c2>)".format(
                package.pretty_name, package.version
            )
        )

        env = EnvManager(poetry).get()

        if not self.option("keep-python-bounds"):
            from poetry.puzzle import Solver
            from poetry.repositories import Repository

            self._io.write_line("Tightening bounds to python version requirements based on dependencies")
            pool = poetry.pool

            solver = Solver(package, pool, Repository(), Repository(), self._io, env)
            bounds = solver.solve().calculate_interpreter_bounds(package.python_constraint)
            bounds_constraint_str = format_python_constraint(bounds)
            poetry.package.python_versions = bounds_constraint_str
            poetry.pyproject.data["tool"]["poetry"]["dependencies"]["python"] = bounds_constraint_str

            self._io.write_line(f"Will require python version: {bounds_constraint_str}")

        builder = Builder(poetry)

        builder.build(fmt, executable=env.python)
