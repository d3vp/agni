from pathlib import Path
import click
from .. import config
from ..proc_util import run_process, concurrent
import asyncio
import tempfile
import json
import os
import sys
import shutil
from datetime import datetime
import re
import shlex
from typing import List


def dir_must_exist(ctx, param, value):
    value = Path(value)
    if value.exists() and value.is_dir():
        return value
    else:
        raise click.BadParameter(f'Path "{value}" must be an existing directory.')


def file_must_exist(ctx, param, value):
    if not value:
        return None
    value = Path(value)
    if value.exists() and value.is_file():
        return value
    else:
        raise click.BadParameter(f'Path "{value}" must be an existing file.')


def _copytree(src, dest, keep_parent=False, ignore=None):
    src, dest = Path(src), Path(dest)
    if keep_parent:
        shutil.copytree(str(src), str(dest / src.name), ignore=ignore)
        return
    for s in src.glob("*"):
        if s.is_dir():
            shutil.copytree(str(s), str(dest / s.name), ignore=ignore)
        else:
            shutil.copy2(str(s), str(dest / s.name))


@click.command()
@click.option(
    "--config",
    expose_value=False,
    callback=lambda ctx, param, value: config.load(value),
)
@click.option("--num-procs", type=int, default=1)
@click.option("--students", default=None, callback=file_must_exist)
@click.option("--tests", default=None, callback=file_must_exist)
@click.argument(
    "bundle-dir", nargs=1, callback=dir_must_exist,
)
def main(num_procs: int, students: Path, tests: Path, bundle_dir: Path):
    """Run external tests on student submissions."""
    language = config.get("language")
    if language == "java":
        asyncio.run(_main(num_procs, students, tests, bundle_dir))


async def _main(num_procs: int, students: Path, testsfile: Path, bundle_dir: Path):
    if students:
        student_list = {
            s.strip().split("__")[0] for s in students.read_text().strip().splitlines()
        }
        subdirs = [
            s
            for s in config.dirs.submissions.glob("*")
            if s.name.split("__")[0] in student_list
        ]
        print("Running tests for the following students:")
        for s in sorted(student_list):
            print(s)
    else:
        subdirs = list(config.dirs.submissions.glob("*"))
        print("Running tests for ALL students.")

    answer = input("Continue? [yes/no]: ")
    if answer != "yes":
        print("Not continuing further, bye.")
        sys.exit(1)

    commandfile = bundle_dir / f"{bundle_dir.name}_commands.sh"
    if testsfile:
        tests = set(s.strip() for s in testsfile.read_text().splitlines())
        commands = []
        for line in commandfile.read_text().splitlines():
            if re.search(r'testcaseID="(.*?)"', line).group(1) in tests:
                args = shlex.split(line)
                commands.append([args[0], "-DisExternal=true", *args[1:]])
    else:
        commands = []
        for line in commandfile.read_text().splitlines():
            args = shlex.split(line)
            commands.append([args[0], "-DisExternal=true", *args[1:]])

        print("Running ALL tests.")

    print("Running the following tests:")
    for cmd in commands:
        # print(" ".join(cmd))
        print(cmd)

    answer = input("Continue? [yes/no]: ")
    if answer != "yes":
        print("Not continuing further, bye.")
        sys.exit(1)

    graderdir = config.dirs.autograder / datetime.now().strftime("%Y-%m-%dT%H%M%S")
    outdir = graderdir / "outputs"
    outdir.mkdir(parents=True, exist_ok=True)
    jarfile = bundle_dir / f"{bundle_dir.name}.jar"

    coros = [
        run(subdir, jarfile, commands, outdir / f"{subdir.name}.json")
        for subdir in subdirs
    ]

    with click.progressbar(length=len(coros), width=50) as bar:
        async for _ in concurrent(coros, num_procs):
            bar.update(1)


def _show_files(dir):
    print([str(p.relative_to(dir)) for p in dir.glob("**/*")])


async def run(subdir: Path, jarfile: Path, commands: List, outputfile: Path):
    with tempfile.TemporaryDirectory() as t:
        tmpdir = Path(t)
        if config.dirs.input_files.exists():
            _copytree(config.dirs.input_files, tmpdir, keep_parent=False)

        if config.dirs.helpers.exists():
            _copytree(config.dirs.helpers, tmpdir, keep_parent=False)

        _copytree(subdir, tmpdir, keep_parent=False)

        for p in tmpdir.glob("*.java"):
            match = re.search(r"package\s+(\w+)\s*;", p.read_text())
            if match and match.group(1):
                pkgdir = Path(tmpdir, *match.group(1).split("."))
                pkgdir.mkdir(exist_ok=True)
                shutil.move(str(p), str(pkgdir))
                # (pkgdir / p.name).write_text(code)

        proc_result = await run_process(
            ["javac", "-cp", ".", *(str(p) for p in tmpdir.glob("**/*.java"))],
            cwd=tmpdir,
        )

        # _show_files(tmpdir)

        if proc_result.returncode != 0:
            result = {"compile_error": f"{proc_result.stdout}{proc_result.stderr}"}
            outputfile.write_text(json.dumps(result))
            return

        with open(outputfile, "wt") as fout:
            for cmd in commands:
                proc_result = await run_process(
                    cmd,
                    cwd=tmpdir,
                    env={
                        **os.environ,
                        "CLASSPATH": f".{os.pathsep}{jarfile.resolve()}",
                    },
                )
                if proc_result.error:
                    print(" ".join(cmd))
                    print(proc_result.error)
                elif proc_result.returncode != 0:
                    print(" ".join(cmd))
                    print(proc_result.stdout)
                    print(proc_result.stderr)
                else:
                    fout.write(proc_result.stdout)

