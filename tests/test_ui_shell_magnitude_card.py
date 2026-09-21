"""Characterization tests for the Magnitude typed card (_build_magnitude_card /
_read_magnitude_fields / _write_magnitude_fields / _update_magnitude_mode_visibility
/ _update_magnitude_unit_labels) in ui_shell.py.

Written as a safety net BEFORE the TypedCard abstraction refactor (see
HANDOFF.md Task 1, Phase 0) so behavior can be verified unchanged afterward.
No window is shown and mainloop() is never called."""

from __future__ import annotations

import tkinter as tk

import pytest

from hydropattern_gui.gui_form import MagnitudeFields
from hydropattern_gui.runner_service import InProcessHydropatternRunner
from hydropattern_gui.ui_shell import GuiController, HydropatternGuiApp


@pytest.fixture
def app(root: tk.Tk) -> HydropatternGuiApp:
    controller = GuiController(InProcessHydropatternRunner())
    application = HydropatternGuiApp(root, controller)
    yield application
    for child in root.winfo_children():
        child.destroy()


def test_build_magnitude_card_creates_expected_widgets(app: HydropatternGuiApp) -> None:
    assert isinstance(app._magnitude_card, tk.Widget)
    assert isinstance(app._magnitude_body, tk.Widget)
    assert not app._magnitude_body.grid_info()
    # Simple mode is the default -> simple frame visible, between hidden.
    assert app._magnitude_simple_frame.grid_info()
    assert not app._magnitude_between_frame.grid_info()


def test_update_magnitude_mode_visibility_toggles_frames(app: HydropatternGuiApp) -> None:
    app._magnitude_mode_var.set("between")
    assert not app._magnitude_simple_frame.grid_info()
    assert app._magnitude_between_frame.grid_info()
    app._magnitude_mode_var.set("simple")
    assert app._magnitude_simple_frame.grid_info()
    assert not app._magnitude_between_frame.grid_info()


def test_changing_mode_resets_the_other_modes_fields(app: HydropatternGuiApp) -> None:
    app._magnitude_operator_var.set(">=")
    app._magnitude_threshold_var.set("5")
    app._magnitude_mode_var.set("between")
    assert app._magnitude_operator_var.get() == ">"
    assert app._magnitude_threshold_var.get() == ""

    app._magnitude_min_var.set("1")
    app._magnitude_max_var.set("2")
    app._magnitude_mode_var.set("simple")
    assert app._magnitude_min_var.get() == ""
    assert app._magnitude_max_var.get() == ""


def test_update_magnitude_unit_labels_reflects_data_units(app: HydropatternGuiApp) -> None:
    app._data_units_var.set("cfs")
    assert app._magnitude_threshold_unit_label.cget("text") == "(cfs)"
    assert app._magnitude_min_unit_label.cget("text") == "(cfs)"
    assert app._magnitude_max_unit_label.cget("text") == "(cfs)"
    app._data_units_var.set("")
    assert app._magnitude_threshold_unit_label.cget("text") == "(data units)"


def test_read_magnitude_fields_simple_mode(app: HydropatternGuiApp) -> None:
    app._magnitude_mode_var.set("simple")
    app._magnitude_operator_var.set(">=")
    app._magnitude_threshold_var.set("42.5")
    fields = app._read_magnitude_fields()
    assert fields.mode == "simple"
    assert fields.operator == ">="
    assert fields.threshold == 42.5
    assert fields.minimum is None
    assert fields.maximum is None
    assert fields.ma_enabled is False
    assert fields.ma_periods is None


def test_read_magnitude_fields_between_mode_with_moving_average(app: HydropatternGuiApp) -> None:
    app._magnitude_mode_var.set("between")
    app._magnitude_min_var.set("1.5")
    app._magnitude_max_var.set("9.5")
    app._magnitude_ma_enabled_var.set(True)
    app._magnitude_ma_periods_var.set("7")
    fields = app._read_magnitude_fields()
    assert fields.mode == "between"
    assert fields.minimum == 1.5
    assert fields.maximum == 9.5
    assert fields.ma_enabled is True
    assert fields.ma_periods == 7


def test_write_magnitude_fields_roundtrips_simple_mode(app: HydropatternGuiApp) -> None:
    fields = MagnitudeFields(
        mode="simple",
        operator="<",
        threshold=3.0,
        minimum=None,
        maximum=None,
        ma_enabled=False,
        ma_periods=None,
    )
    app._write_magnitude_fields(True, fields)
    assert app._magnitude_enabled_var.get() is True
    assert app._magnitude_mode_var.get() == "simple"
    assert app._magnitude_operator_var.get() == "<"
    assert app._magnitude_threshold_var.get() == "3.0"
    assert app._read_magnitude_fields() == fields
    assert app._magnitude_body.grid_info()


def test_write_magnitude_fields_roundtrips_between_mode_with_ma(
    app: HydropatternGuiApp,
) -> None:
    fields = MagnitudeFields(
        mode="between",
        operator=None,
        threshold=None,
        minimum=2.0,
        maximum=8.0,
        ma_enabled=True,
        ma_periods=4,
    )
    app._write_magnitude_fields(True, fields)
    assert app._magnitude_mode_var.get() == "between"
    assert app._magnitude_min_var.get() == "2.0"
    assert app._magnitude_max_var.get() == "8.0"
    assert app._magnitude_ma_enabled_var.get() is True
    assert app._magnitude_ma_periods_var.get() == "4"
    # write always sets an operator default of ">" even in between mode,
    # matching the existing (pre-refactor) behavior.
    read_back = app._read_magnitude_fields()
    assert read_back.minimum == fields.minimum
    assert read_back.maximum == fields.maximum
    assert read_back.ma_enabled == fields.ma_enabled
    assert read_back.ma_periods == fields.ma_periods


def test_write_magnitude_fields_disabled_hides_body(app: HydropatternGuiApp) -> None:
    app._write_magnitude_fields(
        True,
        MagnitudeFields(
            mode="simple",
            operator=">",
            threshold=1.0,
            minimum=None,
            maximum=None,
            ma_enabled=False,
            ma_periods=None,
        ),
    )
    app._write_magnitude_fields(
        False,
        MagnitudeFields(
            mode="simple",
            operator=">",
            threshold=1.0,
            minimum=None,
            maximum=None,
            ma_enabled=False,
            ma_periods=None,
        ),
    )
    assert app._magnitude_enabled_var.get() is False
    assert not app._magnitude_body.grid_info()
