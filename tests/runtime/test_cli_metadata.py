from referee.cli import parser
from referee.version import __version__


def test_package_version_is_public():
    assert __version__ == "0.1.0"


def test_cli_registers_version_flag():
    actions = {opt for action in parser()._actions for opt in action.option_strings}
    assert "--version" in actions
