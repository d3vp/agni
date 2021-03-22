from pathlib import Path
import click
from .. import config
import sys
import json
import pandas as pd
from typing import List


def dir_must_exist(ctx, param, value):
    if not value:
        return None
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


def file_to_path(ctx, param, value):
    if not value:
        return None
    return Path(value)


@click.command()
@click.option(
    "--config",
    expose_value=False,
    callback=lambda ctx, param, value: config.load(value),
)
@click.option("--students", default=None, callback=file_must_exist)
@click.option("--download", default=None, callback=file_to_path)
@click.option("--update", default=None, callback=dir_must_exist)
@click.argument(
    "bundle-dir", nargs=1, callback=dir_must_exist,
)
def main(students: Path, download: Path, update: Path, bundle_dir: Path):
    """Manage test results on Codepost."""
    if students:
        student_list = sorted(
            {
                s.strip().split("__")[0]
                for s in students.read_text().strip().splitlines()
            }
        )
        print("Processing the following students:")
        for s in student_list:
            print(s)
    else:
        student_list = sorted(
            {p.name.strip().split("__")[0] for p in config.dirs.submissions.glob("*")}
        )
        print("Processing ALL students.")

    answer = input("Continue? [yes/no]: ")
    if answer != "yes":
        print("Not continuing further, bye.")
        sys.exit(1)

    if download:
        save_results(student_list, download)
    elif update:
        update_results(update, bundle_dir)
    else:
        print("Invalid options")  # TODO


def get_assignment():
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

    return assignment


def save_results(students: List[str], csvfile: Path):
    assignment = get_assignment()
    if students:
        all_submissions = [
            assignment.list_submissions(student=student)[0] for student in students
        ]
    else:
        all_submissions = assignment.list_submissions()

    def genr():
        for submission in all_submissions:
            student_name = submission.students[0]
            print(f"Processing submission {submission.id} for {student_name}")
            for obj in submission.tests:
                d = {"student": student_name}
                for field in ("submission", "testCase", "logs", "passed", "isError"):
                    d[field] = getattr(obj, field)
                yield d

    df = pd.DataFrame(genr())
    df.to_csv(csvfile, index=False)


def update_results(outdir: Path, bundle_dir: Path):
    import codepost

    assignment = get_assignment()

    tests_on_codepost = {
        f"{cat.name}_@_{test.description}": test
        for cat in assignment.testCategories
        for test in cat.testCases
    }

    print(tests_on_codepost.keys())
    metadata = json.loads((bundle_dir / f"{bundle_dir.name}_metadata.json").read_text())
    tests_in_metadata = set(info.get("testcaseID") for mod, info in metadata.items())
    print(tests_in_metadata)

    test_to_update = {
        test_id: test
        for test_id, test in tests_on_codepost.items()
        if test_id in tests_in_metadata
    }

    print("Number of tests to update:", len(test_to_update))
    print("Following tests will be updated:")
    for tid in test_to_update:
        print(tid)
    answer = input("Continue? [yes/no]: ")
    if answer != "yes":
        print("Not continuing further, bye.")
        sys.exit(1)

    for resultfile in outdir.glob("*.json"):
        lines = resultfile.read_text().splitlines()
        compile_error = None

        print(resultfile.name)

        if len(lines) == 1 and "compile_error" in json.loads(lines[0]):
            compile_error = json.loads(lines[0])["compile_error"]
            for testobj in test_to_update.values():
                args = {
                    "submission": int(resultfile.stem.split("__")[-1]),
                    "testCase": testobj.id,
                    "passed": False,
                    "logs": compile_error,
                }
                # print(json.dumps(args))
                subtestobj = codepost.submission_test.create(**args)
                print(subtestobj)
        else:
            for line in lines:
                data = json.loads(line)
                # cat, name = data["id"].split("_@_")  # TODO remove
                testobj = test_to_update["id"]
                args = {
                    "submission": int(resultfile.stem.split("__")[-1]),
                    "testCase": testobj.id,
                    "passed": data["passed"],
                    "logs": data["log"][:5000],
                }
                # print(json.dumps(args))
                subtestobj = codepost.submission_test.create(**args)
                print(subtestobj)
