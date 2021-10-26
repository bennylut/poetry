from pathlib import Path
from typing import List

from .command import Command
from .. import console
from ...app.relaxed_poetry import rp


class NewCommand(Command):
    """
    creates a directory tree based on a given template

    new
        {template : the template to use (supports path, git, zip, url to zip and builtins)}
        {--o|out : the output path to use (defaults to the active project directory,
                   if no active project, defaults to the current directory)}
        {--f|allow-override : allows the template to override existing files}
        {template_args?* : template arguments, can be positional and key=value}
    """

    def handle(self) -> int:

        template_descriptor: str = self.argument("template")
        if template_descriptor.endswith("?"):
            console.println(rp.document_template(template_descriptor[:-1]))
            return 0

        template_args: List[str] = self.argument("template_args")
        args = []
        kwargs = {}

        for arg in template_args:
            try:
                key, value = arg.split("=", 2)
            except ValueError:
                key, value = (None, arg)

            if key:
                kwargs[key] = value
            else:
                args.append(value)

        rp.execute_template(
            template_descriptor,
            self.option("out") or (rp.active_project.path if rp.has_active_project() else Path.cwd()),
            args, kwargs,
            self.option("allow-override") and True
        )

        return 0
