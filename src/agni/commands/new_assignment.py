import click
from pathlib import Path
import importlib.resources as resources
import shutil


def path_mustnot_exist(ctx, param, value):
    value = Path(value)
    if not value.exists():
        return value
    else:
        raise click.BadParameter(f'Path "{value}" already exists.')


@click.command()
@click.argument("language", type=click.Choice(["python", "java"], case_sensitive=False))
@click.argument("dirpath", nargs=1, callback=path_mustnot_exist)
def main(language: str, dirpath: Path):
    """Create new assignment directory structure."""
    with resources.path(f"agni.resources.{language}", "template") as templatedir:
        shutil.copytree(str(templatedir), str(dirpath))
