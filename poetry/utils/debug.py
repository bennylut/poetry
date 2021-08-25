import code
import inspect
import traceback

from cleo.io.outputs.stream_output import StreamOutput
import sys

_out = StreamOutput(sys.stdout)


def bp(msg: str):
    def console_exit():
        raise SystemExit

    print(f"BREAKPOINT: {msg}")
    caller = inspect.stack()[1]
    try:
        code.InteractiveConsole(locals={**caller[0].f_locals, "exit": console_exit}).interact()
    except SystemExit:
        pass


def print_st():
    traceback.print_stack()
