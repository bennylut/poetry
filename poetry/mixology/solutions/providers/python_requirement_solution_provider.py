import re

from typing import List

from crashtest.contracts.has_solutions_for_exception import HasSolutionsForException
from crashtest.contracts.solution import Solution


class PythonRequirementSolutionProvider(HasSolutionsForException):
    def can_solve(self, exception: Exception) -> bool:
        from poetry.puzzle.exceptions import SolverProblemError

        if not isinstance(exception, SolverProblemError):
            return False

        m = re.match(
            "^The installed project's Python version (.+) is not compatible "
            "with some of the required packages Python requirement",
            str(exception),
        )

        if not m:
            return False

        return True

    def get_solutions(self, exception: Exception) -> List[Solution]:
        from ..solutions.python_requirement_solution import PythonRequirementSolution

        return [PythonRequirementSolution(exception)]
