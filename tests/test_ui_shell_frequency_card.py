"""Characterization tests for the Frequency typed card (_build_frequency_card /
_build_frequency_pattern_editor / _read_frequency_fields / _write_frequency_fields
/ _update_freq_mode_visibility / _update_freq_nested_visibility / the
_on_freq_*_changed handlers) in ui_shell.py.

Written as a safety net BEFORE the TypedCard abstraction refactor (see
HANDOFF.md Task 1, Phase 0) so behavior can be verified unchanged afterward.
No window is shown and mainloop() is never called."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import pytest

from hydropattern_gui.gui_form import FrequencyFields, FrequencyPatternFields
from hydropattern_gui.runner_service import InProcessHydropatternRunner
from hydropattern_gui.ui_shell import GuiController, HydropatternGuiApp


@pytest.fixture
def app(root: tk.Tk) -> HydropatternGuiApp:
    controller = GuiController(InProcessHydropatternRunner())
    application = HydropatternGuiApp(root, controller)
    yield application
    for child in root.winfo_children():
        child.destroy()


def _blank_pattern(**overrides: object) -> FrequencyPatternFields:
    base = dict(
        mode="count",
        operator=">",
        count_n=None,
        probability=None,
        between_min=None,
        between_max=None,
        out_of_n=None,
        count_by_event=True,
    )
    base.update(overrides)
    return FrequencyPatternFields(**base)  # type: ignore[arg-type]


def test_build_frequency_card_creates_expected_widgets(app: HydropatternGuiApp) -> None:
    assert isinstance(app._freq_card, tk.Widget)
    assert isinstance(app._freq_body, tk.Widget)
    assert not app._freq_body.grid_info()
    # Base pattern defaults to Count mode -> count frame visible.
    assert app._freq_frames["base_count"].grid_info()
    assert not app._freq_frames["base_between"].grid_info()
    assert not app._freq_frames["base_probability"].grid_info()
    # Nested disabled by default -> nested pattern hidden, base probability
    # radio disabled (probability is only valid as the base of a nested freq).
    assert not app._freq_nested_label.grid_info()
    assert not app._freq_frames["nested_wrapper"].grid_info()
    base_probability_radio = app._freq_frames["base_probability_radio"]
    assert isinstance(base_probability_radio, ttk.Radiobutton)
    assert str(base_probability_radio["state"]) == "disabled"


def test_update_freq_mode_visibility_toggles_frames_for_base(app: HydropatternGuiApp) -> None:
    app._freq_vars["base"]["mode"].set("between")
    assert not app._freq_frames["base_count"].grid_info()
    assert app._freq_frames["base_between"].grid_info()
    assert not app._freq_frames["base_probability"].grid_info()
    app._freq_vars["base"]["mode"].set("count")
    assert app._freq_frames["base_count"].grid_info()
    assert not app._freq_frames["base_between"].grid_info()


def test_enabling_nested_allows_base_probability_mode(app: HydropatternGuiApp) -> None:
    app._freq_nested_enabled_var.set(True)
    base_probability_radio = app._freq_frames["base_probability_radio"]
    assert str(base_probability_radio["state"]) == "normal"
    assert app._freq_nested_label.grid_info()
    assert app._freq_frames["nested_wrapper"].grid_info()

    app._freq_vars["base"]["mode"].set("probability")
    assert app._freq_frames["base_probability"].grid_info()
    assert not app._freq_frames["base_count"].grid_info()


def test_disabling_nested_forces_base_out_of_probability_and_clears_nested(
    app: HydropatternGuiApp,
) -> None:
    app._freq_nested_enabled_var.set(True)
    app._freq_vars["base"]["mode"].set("probability")
    app._freq_vars["nested"]["count_n"].set("3")
    app._freq_vars["nested"]["out_of_n"].set("10")

    app._freq_nested_enabled_var.set(False)

    assert app._freq_vars["base"]["mode"].get() == "count"
    assert app._freq_vars["nested"]["count_n"].get() == ""
    assert app._freq_vars["nested"]["out_of_n"].get() == ""
    base_probability_radio = app._freq_frames["base_probability_radio"]
    assert str(base_probability_radio["state"]) == "disabled"
    assert not app._freq_nested_label.grid_info()
    assert not app._freq_frames["nested_wrapper"].grid_info()


def test_changing_pattern_mode_resets_other_modes_fields(app: HydropatternGuiApp) -> None:
    pattern_vars = app._freq_vars["base"]
    pattern_vars["count_n"].set("4")
    pattern_vars["out_of_n"].set("10")
    pattern_vars["mode"].set("between")
    assert pattern_vars["count_n"].get() == ""
    # out_of_n is shared by count/between, only cleared for probability mode.
    assert pattern_vars["out_of_n"].get() == "10"

    pattern_vars["between_min"].set("1")
    pattern_vars["between_max"].set("5")
    app._freq_nested_enabled_var.set(True)
    pattern_vars["mode"].set("probability")
    assert pattern_vars["between_min"].get() == ""
    assert pattern_vars["between_max"].get() == ""
    assert pattern_vars["out_of_n"].get() == ""


def test_read_frequency_fields_unnested_count_mode(app: HydropatternGuiApp) -> None:
    app._freq_nested_enabled_var.set(False)
    app._freq_vars["base"]["mode"].set("count")
    app._freq_vars["base"]["operator"].set(">=")
    app._freq_vars["base"]["count_n"].set("3")
    app._freq_vars["base"]["out_of_n"].set("10")
    app._freq_vars["base"]["count_by_event"].set(False)

    fields = app._read_frequency_fields()
    assert fields.nested_enabled is False
    assert fields.base.mode == "count"
    assert fields.base.operator == ">="
    assert fields.base.count_n == 3
    assert fields.base.out_of_n == 10
    assert fields.base.count_by_event is False


def test_read_frequency_fields_nested_between_and_probability(app: HydropatternGuiApp) -> None:
    app._freq_nested_enabled_var.set(True)
    app._freq_vars["base"]["mode"].set("probability")
    app._freq_vars["base"]["operator"].set(">")
    app._freq_vars["base"]["probability"].set("0.25")
    app._freq_vars["nested"]["mode"].set("between")
    app._freq_vars["nested"]["between_min"].set("2")
    app._freq_vars["nested"]["between_max"].set("6")
    app._freq_vars["nested"]["out_of_n"].set("12")

    fields = app._read_frequency_fields()
    assert fields.nested_enabled is True
    assert fields.base.mode == "probability"
    assert fields.base.probability == 0.25
    assert fields.nested.mode == "between"
    assert fields.nested.between_min == 2
    assert fields.nested.between_max == 6
    assert fields.nested.out_of_n == 12


def test_write_frequency_fields_roundtrips_unnested(app: HydropatternGuiApp) -> None:
    fields = FrequencyFields(
        nested_enabled=False,
        base=_blank_pattern(mode="between", between_min=1, between_max=4, out_of_n=8),
        nested=_blank_pattern(),
    )
    app._write_frequency_fields(True, fields)
    assert app._freq_enabled_var.get() is True
    assert app._freq_nested_enabled_var.get() is False
    assert app._freq_vars["base"]["mode"].get() == "between"
    assert app._freq_vars["base"]["between_min"].get() == "1"
    assert app._freq_vars["base"]["between_max"].get() == "4"
    assert app._freq_vars["base"]["out_of_n"].get() == "8"
    read_back = app._read_frequency_fields()
    assert read_back.base.between_min == 1
    assert read_back.base.between_max == 4
    assert read_back.base.out_of_n == 8
    assert app._freq_body.grid_info()


def test_write_frequency_fields_roundtrips_nested(app: HydropatternGuiApp) -> None:
    fields = FrequencyFields(
        nested_enabled=True,
        base=_blank_pattern(
            mode="probability", operator=">=", probability=0.5, count_by_event=True
        ),
        nested=_blank_pattern(
            mode="count", operator="<", count_n=2, out_of_n=5, count_by_event=False
        ),
    )
    app._write_frequency_fields(True, fields)
    assert app._freq_nested_enabled_var.get() is True
    assert app._freq_vars["base"]["mode"].get() == "probability"
    assert app._freq_vars["base"]["probability"].get() == "0.5"
    assert app._freq_vars["nested"]["mode"].get() == "count"
    assert app._freq_vars["nested"]["count_n"].get() == "2"
    assert app._freq_vars["nested"]["count_by_event"].get() is False
    read_back = app._read_frequency_fields()
    assert read_back.nested_enabled is True
    assert read_back.base.probability == 0.5
    assert read_back.nested.count_n == 2
    assert read_back.nested.count_by_event is False


def test_write_frequency_fields_disabled_hides_body(app: HydropatternGuiApp) -> None:
    fields = FrequencyFields(
        nested_enabled=False, base=_blank_pattern(count_n=1, out_of_n=2), nested=_blank_pattern()
    )
    app._write_frequency_fields(True, fields)
    app._write_frequency_fields(False, fields)
    assert app._freq_enabled_var.get() is False
    assert not app._freq_body.grid_info()
