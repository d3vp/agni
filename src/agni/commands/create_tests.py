from pathlib import Path
import click
from .. import config
import sys
import json


def dir_must_exist(ctx, param, value):
    value = Path(value)
    if value.exists() and value.is_dir():
        return value
    else:
        raise click.BadParameter(f'Path "{value}" must be an existing directory.')


@click.command()
@click.option(
    "--config",
    expose_value=False,
    callback=lambda ctx, param, value: config.load(value),
)
@click.argument(
    "bundle-dir", nargs=1, callback=dir_must_exist,
)
def main(bundle_dir: Path):
    """Create external tests on Codepost."""
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

    metadata = json.loads((bundle_dir / f"{bundle_dir.name}_metadata.json").read_text())

    cat2id = {info.get("testcaseID").split("_@_")[0]: None for info in metadata.values()}
    for cat in cat2id.keys():
        obj = codepost.test_category.create(assignment=assignment.id, name=cat)
        cat2id[cat] = obj.id
        print(f"{cat}: {obj.id}")

    print("-" * 80)

    for i, info in enumerate(metadata.values()):
        pointsPass = pointsFail = 0
        points = info.get("points")
        if points < 0:
            pointsFail = points
        else:
            pointsPass = points

        test_category, test_name = info.get("testcaseID").split("_@_")
        test_obj = codepost.test_case.create(
            testCategory=cat2id[test_category],
            type="external",
            description=test_name,
            sortKey=i,
            pointsFail=pointsFail,
            pointsPass=pointsPass,
        )
        print(f"{test_category} :: {test_name} : {test_obj.id}")
