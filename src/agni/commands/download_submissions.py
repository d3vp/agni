from pathlib import Path
import click
from .. import config
import pandas as pd
import sys


@click.command()
@click.option(
    "--config",
    expose_value=False,
    callback=lambda ctx, param, value: config.load(value),
)
@click.option("--students", required=False, default=None)
def main(students):
    """Download student submissions from Codepost."""
    # filenames = config.get("filenames")
    # if not filenames:
    #     print("Please set filenames in config.toml")
    #     sys.exit(1)

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

    if not config.dirs.submissions.exists():
        config.dirs.submissions.mkdir()

    if students:
        all_submissions = [
            assignment.list_submissions(student=student)[0]
            for student in students.split(",")
        ]
    else:
        all_submissions = assignment.list_submissions()

    for submission in all_submissions:
        student_name = submission.students[0]  # .split("@")[0]
        print(f"Processing submission {submission.id} for {student_name}")
        files = pd.DataFrame(
            {
                field: getattr(obj, field)
                for field in ("id", "name", "code", "submission", "created")
            }
            for obj in submission.files
        )
        latest_files = (
            files.sort_values("created").drop_duplicates("name", keep="last")
            # .set_index("name")
        )
        sub_dir = (
            config.dirs.submissions
            / f"{student_name}__{assignment.id}__{submission.id}"
        )
        sub_dir.mkdir(exist_ok=True)
        # for fname in filenames:
        #     file_info = latest_files.loc[fname]
        #     (sub_dir / file_info.name).write_text(file_info.code)

        for _, row in latest_files.iterrows():
            (sub_dir / row["name"]).write_text(row["code"])
