from pathlib import Path
import click
from .. import config
import sys
import json


def path_must_exist(ctx, param, value):
    value = Path(value)
    if value.exists() and value.is_file():
        return value
    else:
        raise click.BadParameter(f'Path "{value}" must be an existing file.')


@click.command()
@click.option(
    "--config",
    expose_value=False,
    callback=lambda ctx, param, value: config.load(value),
)
@click.argument("metadata-file", nargs=1, callback=path_must_exist)
def main(metadata_file: Path):
    """Update points of test cases on Codepost."""
    import codepost

    d = config.get("codepost")
    assert d and isinstance(d, dict)
    assignment_name = d.get("assignment_name")
    course_name = d.get("course_name")
    course_period = d.get("course_period")
    api_key_path = d.get("api_key_path")
    assert assignment_name and course_name and course_period and api_key_path

    codepost.configure_api_key(Path(api_key_path).expanduser().read_text().strip())

    mycourse = codepost.course.list_available(name=course_name, period=course_period)[0]
    print(f"Course: {mycourse.name}, {mycourse.period}")
    assignment = {x.name: x for x in mycourse.assignments}[assignment_name]
    print(f"Assignment: {assignment.name}")

    answer = input("Continue? [yes/no]: ")
    if answer != "yes":
        print("Not continuing further, bye.")
        sys.exit(1)

    tests_on_codepost = {
        (cat.name, test.description): test
        for cat in assignment.testCategories
        for test in cat.testCases
    }

    metadata = json.loads(metadata_file.read_text())

    tests_in_metadata = set(
        (info.get("test_category"), info.get("test_name"))
        for mod, info in metadata.items()
    )
    diff = tests_in_metadata.difference(set(tests_on_codepost.keys()))
    if diff:
        print("The following test cases were found locally but not on codepost:")
        print("\n".join(f"{cat} : {test}" for cat, test in diff))
        sys.exit(1)

    for mod, info in metadata.items():
        key = (info.get("test_category"), info.get("test_name"))
        testobj = tests_on_codepost[key]
        points = info.get("points")
        if points < 0:
            testobj.pointsFail = points
        else:
            testobj.pointsPass = points
        response = testobj.saveInstance()
        print("[OK]" if response else "[FAILED]", response)
