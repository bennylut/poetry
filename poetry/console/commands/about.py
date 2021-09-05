from .command import Command


class AboutCommand(Command):

    name = "about"

    description = "Shows information about Relaxed-Poetry."

    def handle(self) -> None:
        self.line(
            """<info>Relaxed-Poetry - Package Management for Python</info>

<comment>Relaxed-Poetry is a Poetry fork, a dependency manager tracking local dependencies of your projects and libraries.
See <fg=blue>https://github.com/bennylut/relaxed-poetry</> for more information.</comment>"""
        )
