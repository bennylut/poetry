import code
import inspect


def bp(msg: str):
    def console_exit():
        raise SystemExit

    print(f"BREAKPOINT: {msg}")
    caller = inspect.stack()[1]
    try:
        code.InteractiveConsole(locals={**caller[0].f_locals, "exit": console_exit}).interact()
    except SystemExit:
        pass
