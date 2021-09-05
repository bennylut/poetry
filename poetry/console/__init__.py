from typing import Optional

from cleo.formatters.style import Style
from cleo.io.inputs.argv_input import ArgvInput
from cleo.io.io import IO
import sys

from cleo.io.outputs.stream_output import StreamOutput


class Console:
    def __init__(self, io: Optional[IO] = None):
        if io is None:
            io = IO(
                ArgvInput(sys.argv),
                StreamOutput(sys.stdout),
                StreamOutput(sys.stderr))

        self.set_io(io)

    def set_io(self, new_io: IO):
        # Set our own CLI styles
        formatter = new_io.output.formatter
        formatter.set_style("c1", Style("cyan"))
        formatter.set_style("c2", Style("default", options=["bold"]))
        formatter.set_style("info", Style("blue"))
        formatter.set_style("comment", Style("green"))
        formatter.set_style("warning", Style("yellow"))
        formatter.set_style("debug", Style("default", options=["dark"]))
        formatter.set_style("success", Style("green"))

        # Dark variants
        formatter.set_style("c1_dark", Style("cyan", options=["dark"]))
        formatter.set_style("c2_dark", Style("default", options=["bold", "dark"]))
        formatter.set_style("success_dark", Style("green", options=["dark"]))

        new_io.output.set_formatter(formatter)
        new_io.error_output.set_formatter(formatter)

        self.io = new_io

    def println(self, msg: str = "", mode: str = "all"):
        if mode != 'all':
            if not getattr(self.io, f"is_{mode}")():
                return

        self.io.write_line(msg)

    def print(self, msg: str, mode: str = "all"):
        if mode != 'all':
            if not getattr(self.io, f"is_{mode}")():
                return

        self.io.write(msg)


console = Console()

if __name__ == '__main__':
    console.println("<c1>hello</c1> <c2>world</c2>")
