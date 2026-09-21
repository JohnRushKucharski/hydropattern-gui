"""Characterization tests for the Duration typed card (_build_duration_card /
_read_duration_fields / _write_duration_fields / _update_duration_mode_visibility)
in ui_shell.py.

Written as a safety net BEFORE the TypedCard abstraction refactor (see
HANDOFF.md Task 1, Phase 0) so behavior can be verified unchanged afterward.
No window is shown and mainloop() is never called."""

from __future__ import annotations

import tkinter as tk

import pytest

from hydropattern_gui.gui_form import DurationFields
from hydropattern_gui.runner_service import InProcessHydropatternRunner
from hydropattern_gui.ui_shell import GuiController, HydropatternGuiApp


@pytest.fixture
def app(root: tk.Tk) -> HydropatternGuiApp:
    controller = GuiController(InProcessHydropatternRunner())
    application = HydropatternGuiApp(root, controller)
    yield application
    for child in root.winfo_children():
        child.destroy()


def test_build_duration_card_creates_expected_widgets(app: HydropatternGuiApp) -> None:
    assert isinstance(app._duration_card, tk.Widget)
    assert isinstance(app._duration_body, tk.Widget)
    assert not app._duration_body.grid_info()
    assert app._duration_simple_frame.grid_info()
    assert not app._duration_between_frame.grid_info()


def test_update_duration_mode_visibility_toggles_frames(app: HydropatternGuiApp) -> None:
    app._duration_mode_var.set("between")
    assert not app._duration_simple_frame.grid_info()
    assert app._duration_between_frame.grid_info()
    app._duration_mode_var.set("simple")
    assert app._duration_simple_frame.grid_info()
    assert not app._duration_between_frame.grid_info()


def test_changing_mode_resets_the_other_modes_fields(app: HydropatternGuiApp) -> None:
    app._duration_operator_var.set(">=")
    app._duration_steps_var.set("5")
    app._duration_mode_var.set("between")
    assert app._duration_operator_var.get() == ">"
    assert app._duration_steps_var.get() == ""

    app._duration_min_var.set("1")
    app._duration_max_var.set("2")
    app._duration_mode_var.set("simple")
    assert app._duration_min_var.get() == ""
    assert app._duration_max_var.get() == ""


def test_read_duration_fields_simple_mode(app: HydropatternGuiApp) -> None:
    app._duration_mode_var.set("simple")
    app._duration_operator_var.set(">=")
    app._duration_steps_var.set("12")
    fields = app._read_duration_fields()
    assert fields.mode == "simple"
    assert fields.operator == ">="
    assert fields.steps == 12
    assert fields.min_steps is None
    assert fields.max_steps is None


def test_read_duration_fields_between_mode(app: HydropatternGuiApp) -> None:
    app._duration_mode_var.set("between")
    app._duration_min_var.set("3")
    app._duration_max_var.set("9")
    fields = app._read_duration_fields()
    assert fields.mode == "between"
    assert fields.min_steps == 3
    assert fields.max_steps == 9


def test_write_duration_fields_roundtrips_simple_mode(app: HydropatternGuiApp) -> None:
    fields = DurationFields(mode="simple", operator="<", steps=6, min_steps=None, max_steps=None)
    app._write_duration_fields(True, fields)
    assert app._duration_enabled_var.get() is True
    assert app._duration_mode_var.get() == "simple"
    assert app._duration_operator_var.get() == "<"
    assert app._duration_steps_var.get() == "6"
    assert app._read_duration_fields() == fields
    assert app._duration_body.grid_info()


def test_write_duration_fields_roundtrips_between_mode(app: HydropatternGuiApp) -> None:
    fields = DurationFields(mode="between", operator=None, steps=None, min_steps=2, max_steps=15)
    app._write_duration_fields(True, fields)
    assert app._duration_mode_var.get() == "between"
    assert app._duration_min_var.get() == "2"
    assert app._duration_max_var.get() == "15"
    read_back = app._read_duration_fields()
    assert read_back.min_steps == fields.min_steps
    assert read_back.max_steps == fields.max_steps


def test_write_duration_fields_disabled_hides_body(app: HydropatternGuiApp) -> None:
    fields = DurationFields(mode="simple", operator=">", steps=1, min_steps=None, max_steps=None)
    app._write_duration_fields(True, fields)
    app._write_duration_fields(False, fields)
    assert app._duration_enabled_var.get() is False
    assert not app._duration_body.grid_info()
