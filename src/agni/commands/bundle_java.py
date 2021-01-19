import click
from pathlib import Path
from .. import config
import shutil
import tempfile
import importlib.resources as resources
import json
import re
import toml
from textwrap import dedent
from typing import Iterable, List
from ..proc_util import run_process
import asyncio
import os
import sys


@click.command()
@click.option(
    "--config",
    expose_value=False,
    callback=lambda ctx, param, value: config.load(value),
)
@click.option("--prefix", default=None)
@click.option("--gen-single-file", default=None)
@click.argument(
    "testcase-dir",
    nargs=1,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    callback=lambda ctx, key, val: Path(val),
)
@click.argument(
    "solution-dir",
    nargs=1,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    callback=lambda ctx, key, val: Path(val),
)
@click.argument(
    "bundle-dir", nargs=1, callback=lambda ctx, key, val: Path(val),
)
def main(
    prefix: str,
    gen_single_file: str,
    testcase_dir: Path,
    solution_dir: Path,
    bundle_dir: Path,
):
    """[Java] Bundle tests into a jar file and create runscript."""
    if not bundle_dir.exists():
        bundle_dir.mkdir()
    if not prefix:
        prefix = f"[{testcase_dir.name}] "
    bundle(prefix, testcase_dir, solution_dir, bundle_dir)
    if gen_single_file:
        generate_single_file(testcase_dir, bundle_dir, gen_single_file)


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


def _build(
    cmd: List[str],
    files: Iterable[Path],
    classpaths: List[Path] = None,
    dest: Path = None,
    cwd=None,
):
    with tempfile.NamedTemporaryFile(mode="wt", suffix=".txt") as argfile:
        lines = []
        if classpaths:
            cp = os.pathsep.join(str(p) for p in classpaths)
            lines.append(f'-cp "{cp}"\n')
        if dest:
            lines.append(f'-d "{dest}"\n')
        lines.extend(f'"{p}"\n' for p in files)

        argfile.write("".join(lines))
        argfile.flush()
        proc_result = asyncio.run(run_process([*cmd, f"@{argfile.name}"], cwd=cwd))
        if proc_result.returncode != 0:
            print(proc_result.stdout)
            print(proc_result.stderr)
            sys.exit(1)


def get_test_metadata(testdir: Path, test_paths: Iterable[Path], prefix: str):
    result: dict = {}
    code_pattern = "begin_code.*?\n(.*\n).*?end_code"
    config_pattern = r"/\*\s*config\s*(.*?)\*/"
    # replace_config_pattern = r"/\*\s*_begin_config_.*?\n(.*\n).*?_end_config_\s*\*/"
    for p in sorted(test_paths):
        relative_path = p.relative_to(testdir)
        contents = p.read_text()
        dotted_name = ".".join([*relative_path.parent.parts, relative_path.stem])
        info: dict = {}
        match = re.search(config_pattern, contents, re.DOTALL)
        if match:
            info.update(toml.loads(match.group(1)))  # TODO error checks
        match = re.search(code_pattern, contents, re.DOTALL)
        if match:
            info["code"] = dedent(match.group(1))
        else:
            info["code"] = re.sub(config_pattern, "", contents, flags=re.DOTALL)

        tokens = dotted_name.split(".")[-1].split("_", 1)
        if len(tokens) == 1:
            category, testname = "", tokens[0]
        else:
            category, testname = tokens
        info["testcaseID"] = f"{prefix}{category}_@_{testname}"
        result[dotted_name] = info
    return result


def generate_single_file(testcase_dir: Path, bundle_dir: Path, single_filename: str):
    config_pattern = r"/\*\s*config\s*(.*?)\*/"
    package_regex = re.compile("^\s*package")
    import_regex = re.compile("^\s*import")
    imports = set()
    testnames = []
    classes = []
    for p in testcase_dir.glob("**/*.java"):
        relp = p.relative_to(testcase_dir)
        tname = "{}.{}".format(".".join(relp.parent.parts), relp.stem)
        testnames.append(tname)
        content = re.sub(config_pattern, "", p.read_text(), flags=re.DOTALL)
        lines = re.sub("\n\s*public\s+class", "\nclass", content).splitlines()
        package = next(filter(package_regex.match, lines), "")
        imports.update(filter(import_regex.match, lines))
        testclass = "\n".join(
            l for l in lines if not package_regex.match(l) and not import_regex.match(l)
        )
        classes.append(testclass.strip())

    with resources.path(f"agni.resources.java", "MinitesterTemplate.java") as mtfile:
        text = Path(mtfile).read_text()
    text = text.replace("MinitesterTemplate", Path(single_filename).stem)
    text = text.replace("//imports", "{}\n\n{}".format(package, "\n".join(imports)))
    text = text.replace("//classes", "\n\n\n".join(classes))
    text = text.replace("//tests", ",\n".join(f'"{t}"' for t in testnames))
    (bundle_dir / single_filename).write_text(text)


def bundle(prefix: str, testcase_dir: Path, solution_dir: Path, bundle_dir: Path):
    ignore = shutil.ignore_patterns("*.class")
    with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
        tmpbundle = Path(t1)
        tmpsolution = Path(t2)
        classpaths = [config.dirs.helpers, solution_dir]
        files = [
            *config.dirs.helpers.glob("**/*.java"),
            *Path(solution_dir).glob("**/*.java"),
        ]
        _build(
            ["javac"], files, classpaths=classpaths, dest=Path(tmpsolution),
        )

        classpaths = [Path(tmpsolution), testcase_dir]
        files = [*testcase_dir.glob("**/*.java")]
        _build(["javac"], files, classpaths=classpaths, dest=tmpbundle)

        with resources.path(f"agni.resources.java", "autograder") as agdir:
            _copytree(agdir, tmpbundle, keep_parent=False, ignore=ignore)
        genfile = tmpbundle / "_autograder" / "TestCode.java"

        metadata = get_test_metadata(
            testcase_dir, testcase_dir.glob("**/*.java"), prefix
        )

        lines = [
            '{{ "{}", {} }},\n'.format(mod, json.dumps(info["code"]))
            for mod, info in metadata.items()
        ]
        text = genfile.read_text().replace("//_replace_me_", "".join(lines))
        genfile.write_text(text)
        _build(
            ["javac"],
            genfile.parent.glob("**/*.java"),
            classpaths=[tmpbundle],
            dest=tmpbundle,
        )

        _build(
            ["jar", "cf", str((bundle_dir / f"{bundle_dir.name}.jar").resolve())],
            (p.relative_to(tmpbundle) for p in tmpbundle.glob("**/*.class")),
            cwd=tmpbundle,
        )

        metadatapath = bundle_dir / f"{bundle_dir.name}_metadata.json"
        metadatapath.write_text(json.dumps(metadata, indent=4))

        lines = []
        default_timeout = config.get("autograder", {}).get("default-timeout", 3000)
        for class_name, info in metadata.items():
            timeout = info.get("timeout", default_timeout)
            lines.append(
                f"""java -DclassName="{class_name}" -DtestcaseID="{info["testcaseID"]}" """
                f"""-Dtimeout={timeout} _autograder.Executor\n"""
            )
        (bundle_dir / f"{bundle_dir.name}_commands.sh").write_text("".join(lines))

        pkgname = next((p.name for p in Path(solution_dir).glob("*") if p.is_dir()), "")
        contents = dedent(
            f"""
            ls *.java &> /dev/null || {{
                echo 'No java files were not found.'
                exit 1
            }}

            # On codepost, students can submit files and not directories.
            # So here we move java files to their respective package directory.
            # Change the package name below if needed.
            PKGNAME={pkgname}
            mkdir -p $PKGNAME
            mv *.java $PKGNAME

            javac -cp . $PKGNAME/*.java || exit 1

            export CLASSPATH=".:{bundle_dir.name}.jar"
            bash "{bundle_dir.name}_commands.sh" > "/outputs/user_tests.txt"
            """
        )

        (bundle_dir / f"{bundle_dir.name}_codepost_runscript.sh").write_text(contents)
