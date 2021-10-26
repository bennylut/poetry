import sys
from threading import RLock
from typing import Optional, Union, Iterable

from cleo.formatters.style import Style
from cleo.io.inputs.argv_input import ArgvInput
from cleo.io.io import IO
from cleo.io.null_io import NullIO
from cleo.io.outputs.output import Verbosity, Output
from cleo.io.outputs.stream_output import StreamOutput
from typing_extensions import Protocol


class Printer(Protocol):
    def println(
            self, message: str,
            verbosity: Verbosity = Verbosity.NORMAL,
    ) -> None:
        ...

    def print(
            self, message: str,
            verbosity: Verbosity = Verbosity.NORMAL, ) -> None:
        ...

    def is_decorated(self) -> bool:
        ...

    def as_output(self) -> Output:
        ...

    def dynamic_line(self, prefix: str = "") -> "Printer":
        ...


class NullPrinter(Printer):
    def print(
            self, message: str,
            verbosity: Verbosity = Verbosity.NORMAL, ) -> None:
        pass

    def println(
            self, message: str,
            verbosity: Verbosity = Verbosity.NORMAL,
    ) -> None:
        pass

    def is_decorated(self) -> bool:
        return False

    def as_output(self) -> Output:
        return NullIO().output

    def dynamic_line(self, prefix: str = "") -> "Printer":
        return self


NullPrinter = NullPrinter()


class Console(Printer):
    def __init__(self, io: Optional[IO] = None):
        if io is None:
            inpt = ArgvInput()
            inpt.set_stream(sys.stdin)
            io = IO(inpt, StreamOutput(sys.stdout), StreamOutput(sys.stderr))

        self.io: Optional[IO] = None
        self.set_io(io)
        self._nlines = 0
        self.out_lock = RLock()

    def dynamic_line(self, prefix: str = "") -> Printer:
        if not self.is_decorated():
            self.println(prefix)
            return self

        result = DynamicLinePrinter(self._nlines, prefix)
        self.println(prefix)
        return result

    def set_io(self, new_io: IO):

        write_unwrap = new_io._output._write

        def write_wrap(message: str, new_line: bool = False):
            if new_line:
                self._nlines += 1
            self._nlines += message.count('\n')
            return write_unwrap(message, new_line)

        new_io._output._write = write_wrap

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

    def print(
            self, messages: Union[str, Iterable[str]],
            verbosity: Verbosity = Verbosity.NORMAL, ) -> None:
        with self.out_lock:
            self.io.write(messages, verbosity=verbosity)

    def println(
            self, messages: Union[str, Iterable[str]] = "",
            verbosity: Verbosity = Verbosity.NORMAL,
    ) -> None:
        with self.out_lock:
            self.io.write_line(messages, verbosity=verbosity)

    def as_output(self) -> Output:
        return self.io.output

    def is_decorated(self) -> bool:
        return self.io.is_decorated()


console = Console()


class DynamicLinePrinter(Printer):
    def __init__(self, line_num: int, prefix: str):
        self._line_num = line_num
        self._prefix = prefix

    def println(
            self, message: str,
            verbosity: Verbosity = Verbosity.NORMAL,
    ) -> None:
        self.print(message, verbosity)

    def print(
            self, message: str,
            verbosity: Verbosity = Verbosity.NORMAL, ) -> None:
        with console.out_lock:
            up = console._nlines - self._line_num
            if up > 0:
                console.print(f"\u001b[{up}A")  # move up
            console.print("\u001b[1000D\u001b[K")  # move to start of line and clear it
            if self._prefix:
                console.print(self._prefix, verbosity)
            console.print(message, verbosity)
            if up > 0:
                console.print(f"\u001b[{up}B\u001b[1000D")  # move down and to the start of the line

    def is_decorated(self) -> bool:
        return console.is_decorated()

    def dynamic_line(self, prefix: str = "") -> "Printer":
        return DynamicLinePrinter(self._line_num, self._prefix + prefix)

    def as_output(self) -> Output:
        dout = console.as_output()
        dself = self

        class Out(Output):
            def __init__(self):
                super(Out, self).__init__(dout.verbosity, dout.is_decorated(), dout.formatter)

            def _write(self, message: str, new_line: bool = False) -> None:
                dself.println(message)

        return Out()


if __name__ == '__main__':
    console.println("<c1>hello</c1> <c2>world</c2>")
