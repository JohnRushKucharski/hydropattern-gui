from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

PINNED_RUNTIME_SET: dict[str, str] = {
    "hydropattern-gui": "0.1.0",
    "hydropattern": "0.0.0",
    "climate-canvas": "0.1.0",
}


def collect_runtime_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for package in ("hydropattern-gui", "hydropattern", "climate-canvas"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def validate_pinned_runtime_set(pinned: dict[str, str]) -> dict[str, tuple[str, str]]:
    mismatches: dict[str, tuple[str, str]] = {}
    actual = collect_runtime_versions()
    for package, expected_version in pinned.items():
        actual_version = actual.get(package, "not-installed")
        if actual_version != expected_version:
            mismatches[package] = (expected_version, actual_version)
    return mismatches


def build_about_text() -> str:
    versions = collect_runtime_versions()
    mismatches = validate_pinned_runtime_set(PINNED_RUNTIME_SET)
    lines = [
        "hydropattern-gui",
        "",
        "Runtime versions:",
        f"- hydropattern-gui: {versions['hydropattern-gui']}",
        f"- hydropattern: {versions['hydropattern']}",
        f"- climate-canvas: {versions['climate-canvas']}",
        "",
        "Pinned runtime set:",
        f"- hydropattern-gui=={PINNED_RUNTIME_SET['hydropattern-gui']}",
        f"- hydropattern=={PINNED_RUNTIME_SET['hydropattern']}",
        f"- climate-canvas=={PINNED_RUNTIME_SET['climate-canvas']}",
    ]
    if mismatches:
        lines.extend(["", "Mismatch detected:"])
        for package, (expected, actual) in mismatches.items():
            lines.append(f"- {package}: expected {expected}, actual {actual}")
    return "\n".join(lines)
