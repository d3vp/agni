from pathlib import Path
import re
import sys
import importlib
import traceback
import itertools


srcpath = Path("./src")
assert (srcpath / "testcases").exists(), f"Wrong path: {srcpath.resolve()}"

testpath = srcpath / "testcases"
solutionpath = srcpath / "solutions/authorX"
helperpath = srcpath / "_helpers"

tests_to_run = "exposed.*"

sys.path.extend([str(p) for p in (testpath, solutionpath, helperpath)])

for p in testpath.glob("**/*.py"):
    module_relative_path = p.relative_to(testpath)
    module_relative_str = str(module_relative_path)
    if not re.match(tests_to_run, module_relative_str) or module_relative_str.endswith(
        "__init__.py"
    ):
        continue

    module_dotted_name = ".".join(
        (module_relative_path.parent / module_relative_path.stem).parts
    )
    print(f"======== {' / '.join(module_dotted_name.split('.'))} ========")
    try:
        importlib.import_module(module_dotted_name)
    except ImportError:
        print(f"[ERROR] Could not import test module: {module_dotted_name}")
    except AssertionError as e:
        print("[FAILED]", e)
    except Exception:
        print("[FAILED]")
        exc_lines = itertools.dropwhile(
            lambda x: module_relative_str not in x,
            traceback.format_exception(*sys.exc_info()),
        )
        print("".join(exc_lines))
    print("\n")
