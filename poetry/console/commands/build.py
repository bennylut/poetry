from cleo.helpers import option
from poetry.core.version.helpers import format_python_constraint

from .env_command import EnvCommand


class BuildCommand(EnvCommand):

    name = "build"
    description = "Builds a package, as a tarball and a wheel by default."

    options = [
        option("format", "f", "Limit the format to either sdist or wheel.", flag=False),
        option("keep-python-bounds", "k", "don't tighten bounds to python version requirements based on dependencies", flag=True)
    ]

    loggers = [
        "poetry.core.masonry.builders.builder",
        "poetry.core.masonry.builders.sdist",
        "poetry.core.masonry.builders.wheel",
    ]

    def handle(self) -> None:
        from poetry.core.masonry.builder import Builder

        fmt = "all"
        if self.option("format"):
            fmt = self.option("format")

        package = self.poetry.package
        self.line(
            "Building <c1>{}</c1> (<c2>{}</c2>)".format(
                package.pretty_name, package.version
            )
        )

        if not self.option("keep-python-bounds"):
            from poetry.utils.env import EnvManager
            from poetry.puzzle import Solver
            from poetry.repositories import Repository

            self._io.write_line("Tightening bounds to python version requirements based on dependencies")
            pool = self.poetry.pool
            env = EnvManager(self.poetry).get()

            solver = Solver(package, pool, Repository(), Repository(), self._io, env)
            bounds = solver.solve().calculate_interpreter_bounds(package.python_constraint)
            bounds_constraint_str = format_python_constraint(bounds)
            self.poetry.package.python_versions=bounds_constraint_str
            self._poetry.pyproject.data["tool"]["poetry"]["dependencies"]["python"] = bounds_constraint_str

            self._io.write_line(f"Will require python version: {bounds_constraint_str}")

        builder = Builder(self.poetry)
        builder.build(fmt, executable=self.env.python)
