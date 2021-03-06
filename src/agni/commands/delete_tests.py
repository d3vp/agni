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
    """Delete test cases on Codepost."""
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

    # metadata = json.loads((bundle_dir / f"{bundle_dir.name}_metadata.json").read_text())
    # cats_in_metadata = {info.get("test_category") for info in metadata.values()}

    cat_objs = {
        cat.name: cat
        for cat in assignment.testCategories
        # if cat.name in cats_in_metadata
        if cat.name in ("[secret] ", "[forbidden_checks]")
    }

    # for c in cat_objs:
    #     print(f"{c}|")

    # sys.exit(1)

    print("Deleting the following categories:")
    for c in cat_objs:
        print(c)

    answer = input("Continue? [yes/no]: ")
    if answer != "yes":
        print("Not continuing further, bye.")
        sys.exit(1)

    for cat in cat_objs.values():
        print(f"Deleting category id:{cat.id}, name: {cat.name}")
        response = cat.delete() 
        print(f"Response from delete: {response}")
