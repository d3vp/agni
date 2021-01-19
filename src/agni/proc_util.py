import sys
import traceback
import asyncio
from typing import List, Optional, Iterable
from dataclasses import dataclass, asdict


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@dataclass
class ProcessResult:
    is_timeout: bool = False
    timeout: Optional[int] = None
    error: str = ""
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""

    def to_dict(self):
        return asdict(self)


async def run_process(
    command: List[str], timeout: Optional[int] = None, cwd=None, env=None
) -> ProcessResult:
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except Exception as exc:
        proc.kill()
        await proc.wait()
        return ProcessResult(
            is_timeout=isinstance(exc, asyncio.TimeoutError),
            timeout=timeout,
            error=traceback.format_exc(),
        )
    else:
        return ProcessResult(
            returncode=proc.returncode,
            timeout=timeout,
            stdout=stdout.decode(),
            stderr=stderr.decode(),
        )


async def concurrent(coroutines: Iterable, num: int):
    sem = asyncio.Semaphore(num)

    async def inner(i, aw):
        async with sem:
            return i, await aw

    for fut in asyncio.as_completed(
        {inner(i, coro) for i, coro in enumerate(coroutines)}
    ):
        yield await fut
