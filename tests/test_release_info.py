from hydropattern_gui.release_info import (
    PINNED_RUNTIME_SET,
    build_about_text,
    collect_runtime_versions,
    validate_pinned_runtime_set,
)


def test_collect_runtime_versions_contains_expected_packages() -> None:
    versions = collect_runtime_versions()
    assert "hydropattern-gui" in versions
    assert "hydropattern" in versions
    assert "climate-canvas" in versions


def test_about_text_contains_version_lines() -> None:
    text = build_about_text()
    assert "hydropattern-gui" in text
    assert "hydropattern" in text
    assert "climate-canvas" in text
    assert "Pinned runtime set" in text


def test_validate_pinned_runtime_set_matches_current_environment() -> None:
    assert validate_pinned_runtime_set(PINNED_RUNTIME_SET) == {}
