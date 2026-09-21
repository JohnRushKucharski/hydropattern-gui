"""Characterization tests for the Timing typed card (_build_timing_card /
_read_timing_fields / _write_timing_fields) in ui_shell.py.

Written as a safety net BEFORE the TypedCard abstraction refactor (see
HANDOFF.md Task 1, Phase 0) so behavior can be verified unchanged afterward.
No window is shown and mainloop() is never called."""

from __future__ import annotations

import tkinter as tk

import pytest

from hydropattern_gui.gui_form import TimingFields
from hydropattern_gui.runner_service import InProcessHydropatternRunner
from hydropattern_gui.ui_shell import GuiController, HydropatternGuiApp


@pytest.fixture
def app(root: tk.Tk) -> HydropatternGuiApp:
    controller = GuiController(InProcessHydropatternRunner())
    application = HydropatternGuiApp(root, controller)
    yield application
    for child in root.winfo_children():
        child.destroy()


def test_build_timing_card_creates_expected_widgets(app: HydropatternGuiApp) -> None:
    assert isinstance(app._timing_card, tk.Widget)
    assert isinstance(app._timing_body, tk.Widget)
    # Disabled by default -> body hidden.
    assert not app._timing_body.grid_info()


def test_read_timing_fields_defaults_to_none(app: HydropatternGuiApp) -> None:
    fields = app._read_timing_fields()
    assert fields == TimingFields(first_day_of_year=None, last_day_of_year=None)


def test_read_timing_fields_parses_entered_values(app: HydropatternGuiApp) -> None:
    app._timing_first_day_var.set("32")
    app._timing_last_day_var.set("305")
    fields = app._read_timing_fields()
    assert fields.first_day_of_year == 32
    assert fields.last_day_of_year == 305


def test_write_timing_fields_roundtrips_into_widget_state(app: HydropatternGuiApp) -> None:
    fields = TimingFields(first_day_of_year=10, last_day_of_year=280)
    app._write_timing_fields(True, fields)
    assert app._timing_enabled_var.get() is True
    assert app._timing_first_day_var.get() == "10"
    assert app._timing_last_day_var.get() == "280"
    # Roundtrip back through _read_timing_fields recovers the same fields.
    assert app._read_timing_fields() == fields


def test_write_timing_fields_none_values_clear_entries(app: HydropatternGuiApp) -> None:
    app._timing_first_day_var.set("1")
    app._timing_last_day_var.set("2")
    app._write_timing_fields(False, TimingFields(first_day_of_year=None, last_day_of_year=None))
    assert app._timing_enabled_var.get() is False
    assert app._timing_first_day_var.get() == ""
    assert app._timing_last_day_var.get() == ""


def test_write_timing_fields_enabled_shows_body(app: HydropatternGuiApp) -> None:
    app._write_timing_fields(True, TimingFields(first_day_of_year=1, last_day_of_year=366))
    assert app._timing_body.grid_info()


def test_write_timing_fields_disabled_hides_body(app: HydropatternGuiApp) -> None:
    app._write_timing_fields(True, TimingFields(first_day_of_year=1, last_day_of_year=366))
    app._write_timing_fields(False, TimingFields(first_day_of_year=1, last_day_of_year=366))
    assert not app._timing_body.grid_info()
