from hydropattern_gui.ui_shell import (
    build_log_placeholder,
    mousewheel_scroll_units,
    normalize_path_for_display,
    should_enable_characteristic_row,
    suggest_toml_path,
)


def test_normalize_path_for_display_uses_backslashes() -> None:
    assert normalize_path_for_display("C:/a/b/c.csv") == r"C:\a\b\c.csv"


def test_normalize_path_for_display_keeps_empty() -> None:
    assert normalize_path_for_display("") == ""


def test_suggest_toml_path_uses_output_dir_and_timeseries_stem() -> None:
    assert (
        suggest_toml_path(r"C:\out", r"C:\data\series.csv")
        == r"C:\out\series.toml"
    )


def test_suggest_toml_path_empty_without_output_dir() -> None:
    assert suggest_toml_path("", r"C:\data\series.csv") == ""


def test_characteristic_enable_rule_only_needs_first_row() -> None:
    rows = ["[305, 335]", "", "", "", ""]
    assert should_enable_characteristic_row(0, rows) is True
    assert should_enable_characteristic_row(1, rows) is True
    assert should_enable_characteristic_row(4, rows) is True

    rows2 = ["", "[\">\", 1.0]", "", "", ""]
    assert should_enable_characteristic_row(0, rows2) is True
    assert should_enable_characteristic_row(1, rows2) is False


def test_log_placeholder_describes_log_purpose() -> None:
    placeholder = build_log_placeholder()
    assert "Application logs appear here." in placeholder
    assert "[stdout]/[stderr]" in placeholder


def test_mousewheel_scroll_units_converts_common_deltas() -> None:
    assert mousewheel_scroll_units(120) == -1
    assert mousewheel_scroll_units(-120) == 1
    assert mousewheel_scroll_units(240) == -2
    assert mousewheel_scroll_units(0) == 0
