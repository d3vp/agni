from . import testinfo
from .proc_util import run_process
import json
import os
import asyncio


DEFAULT_TIMEOUT = 5


async def _main(fout, is_json):
    for module, info in testinfo.data.items():
        proc_result = await run_process(
            ["python3", "-m", "_autograder.executor", module],
            timeout=info.get("timeout", DEFAULT_TIMEOUT),
        )
        if proc_result.is_timeout:
            result = {
                "passed": False,
                "log": (
                    f"Timeout after {proc_result.timeout} seconds. "
                    "Please check if there is an infinite loop.\n"
                ),
            }
        elif proc_result.error:
            result = {
                "passed": False,
                "log": f"Autograder Error (please contact TA):\n{proc_result.error}",
            }
        else:
            result = json.loads(proc_result.stdout)

        prefix, category, test = module.split(".")
        result["id"] = f"[{prefix}] {category}_@_{test}"

        code = info.get("code")
        if code:
            lines = [
                f"{'-'*9} Test Code {'-'*9}",
                code,
                f"\n{'-'*9} Output {'-'*9}",
                result["log"],
            ]
            result["log"] = "\n".join(lines)

        status = "[PASSED]" if result["passed"] else "[FAILED]"
        result["log"] = "********* {} ********* {}\n{}\n\n\n".format(
            result["id"].replace("_@_", " : "), status, result["log"]
        )

        if is_json:
            line = json.dumps({k: result[k] for k in ("id", "passed", "log")})
            fout.write(f"{line}\n")
            fout.flush()
        else:
            fout.write(result["log"])
            fout.flush()


def main():
    outputpath = os.environ.get("AGNI_OUTPUTPATH")
    is_json = True
    if not outputpath:
        outputpath = "./test_result.txt"
        is_json = False
    with open(outputpath, "wt") as fout:
        asyncio.run(_main(fout, is_json))
