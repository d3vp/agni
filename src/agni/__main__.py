import click
from .commands import (
    new_assignment,
    bundle_java,
    bundle_python,
    run_external,
    update_points,
    create_tests,
    delete_tests,
    download_submissions,
    update_test_results,
)


class NaturalOrderGroup(click.Group):
    def list_commands(self, ctx):
        return self.commands.keys()


@click.group(
    cls=NaturalOrderGroup,
    context_settings=dict(help_option_names=["-h", "--help"], max_content_width=120),
)
@click.pass_context
def main(ctx: click.Context):
    """AGNI: Python autograder and Codepost companion."""


main.add_command(new_assignment.main, name="new-assignment")
main.add_command(bundle_java.main, name="bundle-java")
main.add_command(bundle_python.main, name="bundle-python")
main.add_command(update_points.main, name="update-points")

main.add_command(download_submissions.main, name="download-submissions")
main.add_command(create_tests.main, name="create-tests")
main.add_command(delete_tests.main, name="delete-tests")
main.add_command(run_external.main, name="run-external")
main.add_command(update_test_results.main, name="update-results")

main(prog_name="agni")
