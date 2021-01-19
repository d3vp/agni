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
@click.option("--students", required=False, default=None)
@click.argument("metadata-file", nargs=1, callback=path_must_exist)
def main(students: str, metadata_file: Path):
    """Update results of external tests on Codepost."""
    outputsdir = config.dirs.internal / "outputs"
    if not outputsdir.exists():
        print(f"{outputsdir} does not exist.")
        sys.exit(1)

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
        f"{cat.name}_@_{test.description}": test
        for cat in assignment.testCategories
        for test in cat.testCases
    }

    metadata = json.loads(metadata_file.read_text())

    tests_in_metadata = set(
        f"{info.get('test_category')}_@_{info.get('test_name')}"
        for mod, info in metadata.items()
    )

    test_to_update = {
        test_id: test
        for test_id, test in tests_on_codepost.items()
        if test_id in tests_in_metadata
    }
    if len(test_to_update) != len(tests_in_metadata):
        print("Number of tests in local metadata is not same as those in codepost.")
        print(len(test_to_update), len(tests_in_metadata))
        sys.exit(1)

    print("Number of tests to update:", len(test_to_update))
    print("Following tests will be updated:")
    for tid in test_to_update:
        print(tid)
    answer = input("Continue? [yes/no]: ")
    if answer != "yes":
        print("Not continuing further, bye.")
        sys.exit(1)

    students_list = students.split(",") if students else []
    for resultfile in outputsdir.glob("*.json"):
        if students_list and resultfile.stem.split("_@_")[0] not in students_list:
            continue
        lines = resultfile.read_text().splitlines()
        assert len(lines) in (1, len(test_to_update))
        if len(lines) == 1:
            data = json.loads(lines[0])
            if "compile_error" not in data:
                assert data.get("id")
                assert data.get("passed") in (True, False)
                assert data.get("log")
        else:
            test_ids = set()
            for line in lines:
                data = json.loads(line)
                assert data.get("id")
                assert data.get("passed") in (True, False)
                assert data.get("log")
                test_ids.add(data["id"])
            assert test_ids == set(test_to_update.keys())

    print("done validation.")

    subtestsdir = dirs.internal / "submission_tests"
    if not subtestsdir.exists():
        subtestsdir.mkdir()

    if students_list:
        print("Updating test results for the following students:")
        for s in students_list:
            print(s)
        answer = input("Continue? [yes/no]: ")
        if answer != "yes":
            print("Not continuing further, bye.")
            sys.exit(1)
    else:
        print("Updating test results for ALL students.")
        answer = input("Continue? [yes/no]: ")
        if answer != "yes":
            print("Not continuing further, bye.")
            sys.exit(1)

    for resultfile in outputsdir.glob("*.json"):
        if students_list and resultfile.stem.split("_@_")[0] not in students_list:
            continue
        lines = resultfile.read_text().splitlines()
        compile_error = None

        print(resultfile.name)

        if len(lines) == 1 and "compile_error" in json.loads(lines[0]):
            compile_error = json.loads(lines[0])["compile_error"]
            with (subtestsdir / f"{resultfile.stem}_response.json").open("wt") as fout:
                for testobj in test_to_update.values():
                    args = {
                        "submission": int(resultfile.stem.split("_@_")[-1]),
                        "testCase": testobj.id,
                        "passed": False,
                        "logs": compile_error,
                    }
                    # print(json.dumps(args))
                    subtestobj = codepost.submission_test.create(**args)
                    fout.write("{}\n".format(repr(subtestobj)))
        else:
            with (subtestsdir / f"{resultfile.stem}_response.json").open("wt") as fout:
                for line in lines:
                    data = json.loads(line)
                    testobj = test_to_update[data["id"]]
                    args = {
                        "submission": int(resultfile.stem.split("_@_")[-1]),
                        "testCase": testobj.id,
                        "passed": data["passed"],
                        "logs": data["log"][:5000],
                    }
                    # print(json.dumps(args))
                    subtestobj = codepost.submission_test.create(**args)
                    fout.write("{}\n".format(repr(subtestobj)))
