"""Characterization tests for the Rate of Change typed card
(_build_rate_of_change_card / _read_roc_fields / _write_roc_fields /
_update_roc_mode_visibility / _update_roc_cascade_state and the
_on_roc_*_changed handlers) in ui_shell.py.

Written as a safety net BEFORE the TypedCard abstraction refactor (see
HANDOFF.md Task 1, Phase 0) so behavior can be verified unchanged afterward.
No window is shown and mainloop() is never called."""

from __future__ import annotations

import tkinter as tk

import pytest

from hydropattern_gui.gui_form import RateOfChangeFields
from hydropattern_gui.runner_service import InProcessHydropatternRunner
from hydropattern_gui.ui_shell import GuiController, HydropatternGuiApp


@pytest.fixture
def app(root: tk.Tk) -> HydropatternGuiApp:
    controller = GuiController(InProcessHydropatternRunner())
    application = HydropatternGuiApp(root, controller)
    yield application
    for child in root.winfo_children():
        child.destroy()


def test_build_roc_card_creates_expected_widgets(app: HydropatternGuiApp) -> None:
    assert isinstance(app._roc_card, tk.Widget)
    assert isinstance(app._roc_body, tk.Widget)
    assert not app._roc_body.grid_info()
    assert app._roc_simple_frame.grid_info()
    assert not app._roc_between_frame.grid_info()
    # Cascade starts fully disabled: ma off -> look_back/min entries disabled.
    assert str(app._roc_ma_periods_entry["state"]) == "disabled"
    assert str(app._roc_look_back_checkbutton["state"]) == "disabled"
    assert str(app._roc_look_back_entry["state"]) == "disabled"
    assert str(app._roc_min_checkbutton["state"]) == "disabled"
    assert str(app._roc_min_value_entry["state"]) == "disabled"


def test_update_roc_mode_visibility_toggles_frames(app: HydropatternGuiApp) -> None:
    app._roc_mode_var.set("between")
    assert not app._roc_simple_frame.grid_info()
    assert app._roc_between_frame.grid_info()
    app._roc_mode_var.set("simple")
    assert app._roc_simple_frame.grid_info()
    assert not app._roc_between_frame.grid_info()


def test_changing_mode_resets_the_other_modes_fields(app: HydropatternGuiApp) -> None:
    app._roc_operator_var.set(">=")
    app._roc_threshold_var.set("5")
    app._roc_mode_var.set("between")
    assert app._roc_operator_var.get() == ">"
    assert app._roc_threshold_var.get() == ""

    app._roc_min_var.set("1")
    app._roc_max_var.set("2")
    app._roc_mode_var.set("simple")
    assert app._roc_min_var.get() == ""
    assert app._roc_max_var.get() == ""


def test_enabling_ma_enables_ma_periods_and_look_back_checkbox(app: HydropatternGuiApp) -> None:
    app._roc_ma_enabled_var.set(True)
    assert str(app._roc_ma_periods_entry["state"]) == "normal"
    assert str(app._roc_look_back_checkbutton["state"]) == "normal"
    # look_back entry/min checkbutton stay disabled until look_back itself
    # is enabled (cascade requires the prior step to be checked too).
    assert str(app._roc_look_back_entry["state"]) == "disabled"
    assert str(app._roc_min_checkbutton["state"]) == "disabled"


def test_enabling_look_back_enables_its_entry_and_min_checkbox(app: HydropatternGuiApp) -> None:
    app._roc_ma_enabled_var.set(True)
    app._roc_look_back_enabled_var.set(True)
    assert str(app._roc_look_back_entry["state"]) == "normal"
    assert str(app._roc_min_checkbutton["state"]) == "normal"
    assert str(app._roc_min_value_entry["state"]) == "disabled"


def test_enabling_min_enables_its_value_entry(app: HydropatternGuiApp) -> None:
    app._roc_ma_enabled_var.set(True)
    app._roc_look_back_enabled_var.set(True)
    app._roc_min_enabled_var.set(True)
    assert str(app._roc_min_value_entry["state"]) == "normal"


def test_disabling_ma_cascades_off_look_back_and_clears_values(app: HydropatternGuiApp) -> None:
    app._roc_ma_enabled_var.set(True)
    app._roc_ma_periods_var.set("5")
    app._roc_look_back_enabled_var.set(True)
    app._roc_look_back_var.set("3")

    app._roc_ma_enabled_var.set(False)

    assert app._roc_ma_periods_var.get() == ""
    assert app._roc_look_back_enabled_var.get() is False
    assert str(app._roc_ma_periods_entry["state"]) == "disabled"
    assert str(app._roc_look_back_checkbutton["state"]) == "disabled"


def test_disabling_look_back_cascades_off_min_and_clears_values(app: HydropatternGuiApp) -> None:
    app._roc_ma_enabled_var.set(True)
    app._roc_look_back_enabled_var.set(True)
    app._roc_look_back_var.set("4")
    app._roc_min_enabled_var.set(True)
    app._roc_min_value_var.set("1.5")

    app._roc_look_back_enabled_var.set(False)

    assert app._roc_look_back_var.get() == ""
    assert app._roc_min_enabled_var.get() is False
    assert str(app._roc_look_back_entry["state"]) == "disabled"
    assert str(app._roc_min_checkbutton["state"]) == "disabled"


def test_disabling_min_clears_its_value(app: HydropatternGuiApp) -> None:
    app._roc_ma_enabled_var.set(True)
    app._roc_look_back_enabled_var.set(True)
    app._roc_min_enabled_var.set(True)
    app._roc_min_value_var.set("2.0")

    app._roc_min_enabled_var.set(False)

    assert app._roc_min_value_var.get() == ""
    assert str(app._roc_min_value_entry["state"]) == "disabled"


def test_read_roc_fields_simple_mode_full_cascade(app: HydropatternGuiApp) -> None:
    app._roc_mode_var.set("simple")
    app._roc_operator_var.set(">=")
    app._roc_threshold_var.set("2.5")
    app._roc_ma_enabled_var.set(True)
    app._roc_ma_periods_var.set("6")
    app._roc_look_back_enabled_var.set(True)
    app._roc_look_back_var.set("2")
    app._roc_min_enabled_var.set(True)
    app._roc_min_value_var.set("0.1")

    fields = app._read_roc_fields()
    assert fields.mode == "simple"
    assert fields.operator == ">="
    assert fields.threshold == 2.5
    assert fields.ma_enabled is True
    assert fields.ma_periods == 6
    assert fields.look_back_enabled is True
    assert fields.look_back == 2
    assert fields.min_enabled is True
    assert fields.min_value == 0.1


def test_read_roc_fields_between_mode_no_optionals(app: HydropatternGuiApp) -> None:
    app._roc_mode_var.set("between")
    app._roc_min_var.set("1.0")
    app._roc_max_var.set("9.0")
    fields = app._read_roc_fields()
    assert fields.mode == "between"
    assert fields.minimum == 1.0
    assert fields.maximum == 9.0
    assert fields.ma_enabled is False
    assert fields.look_back_enabled is False
    assert fields.min_enabled is False


def test_write_roc_fields_roundtrips_full_cascade(app: HydropatternGuiApp) -> None:
    fields = RateOfChangeFields(
        mode="simple",
        operator="<",
        threshold=3.0,
        minimum=None,
        maximum=None,
        ma_enabled=True,
        ma_periods=5,
        look_back_enabled=True,
        look_back=2,
        min_enabled=True,
        min_value=0.5,
    )
    app._write_roc_fields(True, fields)
    assert app._roc_enabled_var.get() is True
    assert app._roc_mode_var.get() == "simple"
    assert app._roc_operator_var.get() == "<"
    assert app._roc_threshold_var.get() == "3.0"
    assert app._roc_ma_enabled_var.get() is True
    assert app._roc_ma_periods_var.get() == "5"
    assert app._roc_look_back_enabled_var.get() is True
    assert app._roc_look_back_var.get() == "2"
    assert app._roc_min_enabled_var.get() is True
    assert app._roc_min_value_var.get() == "0.5"
    assert str(app._roc_min_value_entry["state"]) == "normal"
    assert app._read_roc_fields() == fields
    assert app._roc_body.grid_info()


def test_write_roc_fields_disabled_hides_body(app: HydropatternGuiApp) -> None:
    fields = RateOfChangeFields(
        mode="simple",
        operator=">",
        threshold=1.0,
        minimum=None,
        maximum=None,
        ma_enabled=False,
        ma_periods=None,
        look_back_enabled=False,
        look_back=None,
        min_enabled=False,
        min_value=None,
    )
    app._write_roc_fields(True, fields)
    app._write_roc_fields(False, fields)
    assert app._roc_enabled_var.get() is False
    assert not app._roc_body.grid_info()
