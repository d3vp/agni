import click
from pathlib import Path
from .. import config
import shutil
import tempfile
import importlib.resources as resources
import zipapp
import json
import re
import toml
from textwrap import dedent
import base64
from typing import Iterable


@click.command()
@click.option(
    "--config",
    expose_value=False,
    callback=lambda ctx, param, value: config.load(value),
)
@click.option("--prefix", default=None)
@click.argument(
    "testcase-dir",
    nargs=1,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    callback=lambda ctx, key, val: Path(val),
)
@click.argument(
    "bundle-dir", nargs=1, callback=lambda ctx, key, val: Path(val),
)
def main(
    prefix: str, testcase_dir: Path, bundle_dir: Path,
):
    """[Python] Bundle tests into a zip file and create runscript."""
    if not bundle_dir.exists():
        bundle_dir.mkdir()
    if not prefix:
        prefix = f"[{testcase_dir.name}] "
    bundle(prefix, testcase_dir, bundle_dir)


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


def get_test_metadata(testdir: Path, test_paths: Iterable[Path], prefix: str):
    result: dict = {}
    code_pattern = "_begin_code_.*?\n(.*\n).*?_end_code_"
    config_pattern = "_begin_config_.*?\n(.*\n).*?_end_config_"
    replace_config_pattern = (
        r'''(\'\'\'|""")\s*_begin_config_.*?\n(.*\n).*?_end_config_\s*(\'\'\'|""")'''
    )
    for p in sorted(test_paths):
        relative_path = p.relative_to(testdir)
        contents = p.read_text()
        dotted_name = ".".join((relative_path.parent / relative_path.stem).parts)
        info: dict = {}
        match = re.search(config_pattern, contents, re.DOTALL)
        if match:
            info.update(toml.loads(match.group(1)))
        match = re.search(code_pattern, contents, re.DOTALL)
        if match:
            info["code"] = dedent(match.group(1))
        else:
            info["code"] = re.sub(replace_config_pattern, "", contents)

        category, testname = dotted_name.split(".")[1:]
        info["testcaseID"] = f"{prefix}{category}_@_{testname}"
        result[dotted_name] = info
    return result


def bundle(prefix: str, testcase_dir: Path, bundle_dir: Path):
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    with tempfile.TemporaryDirectory() as t:
        tmpdir = Path(t)
        _copytree(testcase_dir, tmpdir, keep_parent=True, ignore=ignore)
        _copytree(config.dirs.helpers, tmpdir, keep_parent=False, ignore=ignore)
        with resources.path(f"agni.resources.python", "autograder") as agdir:
            _copytree(agdir, tmpdir, keep_parent=False, ignore=ignore)

        metadata = get_test_metadata(
            testcase_dir.parent,
            (p for p in testcase_dir.glob("**/*.py") if not str(p).endswith("__init__.py")),
            prefix,
        )
        genfile = tmpdir / "_autograder" / "testinfo.py"
        genfile.write_text(
            genfile.read_text().replace("_replace_me_", json.dumps(metadata, indent=4))
        )

        pyzfile = bundle_dir / f"{bundle_dir.name}.pyz"
        zipapp.create_archive(tmpdir, pyzfile)
        Path(f"{pyzfile}.b64").write_bytes(base64.b64encode(pyzfile.read_bytes()))

        metadatapath = bundle_dir / f"{bundle_dir.name}_metadata.json"
        metadatapath.write_text(json.dumps(metadata, indent=4))
