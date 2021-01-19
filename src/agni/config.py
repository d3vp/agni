from pathlib import Path
import toml
import click


class _Dirs:
    def set_root(self, project_root):
        self.project_root = Path(project_root).resolve()
        self.src = self.project_root / "src"
        self.solutions = self.src / "solutions"
        self.helpers = self.src / "helpers"
        self.testcases = self.src / "testcases"
        self.bundle = self.project_root / "bundle"
        self.input_files = self.project_root / "input_files"
        self.submissions = self.project_root / "submissions"
        self.autograder = self.project_root / "autograder"
        self.logs = self.project_root / "logs"


_config: dict = dict()
dirs: _Dirs = _Dirs()


def get(key, default=None):
    return _config.get(key, default)


def load(toml_file):
    if toml_file is None:
        toml_file = "./config.toml"
    toml_file = Path(toml_file)
    if not toml_file.exists():
        raise click.BadParameter(
            f"Config file {toml_file} does not exist.\n"
            "Please run this command from assignment directory or provide --config option."
        )
    dirs.set_root(toml_file.parent)
    _config.clear()
    _config.update(toml.load(toml_file))
    return _config
