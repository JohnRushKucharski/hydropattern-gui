from __future__ import annotations

import subprocess
from pathlib import Path


def build_pyinstaller_command(repo_root: Path) -> list[str]:
    return [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onefile",
        "--name",
        "hydropattern-gui",
        str(repo_root / "src" / "hydropattern_gui" / "__main__.py"),
    ]


def build_windows_executable(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        build_pyinstaller_command(repo_root),
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )
