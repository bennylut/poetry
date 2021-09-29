from typing import TYPE_CHECKING
from typing import Optional

from cleo.commands.command import Command as BaseCommand

if TYPE_CHECKING:
    from poetry.console.application import Application
    from poetry.managed_project import ManagedProject


class Command(BaseCommand):
    loggers = []

    _poetry: Optional["ManagedProject"] = None

    @property
    def poetry(self) -> "ManagedProject":
        from poetry.app.relaxed_poetry import rp
        if self._poetry is None:
            return rp.active_project
        return self._poetry

    def set_poetry(self, poetry: "ManagedProject") -> None:
        self._poetry = poetry

    def get_application(self) -> "Application":
        return self.application

    def reset_poetry(self) -> None:
        self.get_application().reset_poetry()
