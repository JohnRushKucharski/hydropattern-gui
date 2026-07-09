from pathlib import Path

from hydropattern_gui.packaging_cli import build_pyinstaller_command


def test_build_pyinstaller_command_is_deterministic() -> None:
    repo_root = Path(r"C:\repo\hydropattern-gui")
    command = build_pyinstaller_command(repo_root)
    assert command == [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onefile",
        "--name",
        "hydropattern-gui",
        str(repo_root / "src" / "hydropattern_gui" / "__main__.py"),
    ]
