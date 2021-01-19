import itertools
import importlib
import traceback
import sys
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json


def main():
    log = []
    passed = False
    out = StringIO()
    try:
        module_dotted_name = sys.argv[1]
        with redirect_stdout(out), redirect_stderr(out):
            importlib.import_module(module_dotted_name)
        log.append(out.getvalue())
        passed = True
    except ImportError:
        log.append(
            f"[Autograder Error] Could not import test module: {module_dotted_name}"
        )
        log.append(traceback.format_exc())
    except AssertionError as e:
        log.append(out.getvalue())
        log.append(f"[Feedback] {e}\n")
    except Exception:
        log.append(out.getvalue())
        exc_lines = itertools.dropwhile(
            lambda x: module_dotted_name.replace(".", "/") not in x,
            traceback.format_exception(*sys.exc_info()),
        )
        log.append("".join(exc_lines))

    try:
        print(json.dumps({"passed": passed, "log": "\n".join(log)}))
    except Exception:
        print(
            json.dumps(
                {"passed": False, "log": f"[Autograder Error] {traceback.format_exc()}"}
            )
        )


if __name__ == "__main__":
    main()
