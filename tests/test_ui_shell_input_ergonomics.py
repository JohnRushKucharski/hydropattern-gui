"""Headless widget tests for Task 3 input ergonomics (HANDOFF.md
phase3-input-ergonomics): static field-error -> widget map completeness,
inline Invalid.TEntry/TCombobox highlighting, and focusout validation.
No window is shown and mainloop() is never called."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import pytest

from hydropattern_gui.characteristics._shared import FormValidationError
from hydropattern_gui.runner_service import InProcessHydropatternRunner
from hydropattern_gui.ui_shell import GuiController, HydropatternGuiApp

# Keys config_from_form_state can raise that map to exactly one static widget
# (see gui_form.config_from_form_state). Dynamic per-row keys and
# "components.rows" (no single widget target) are intentionally excluded.
KNOWN_FIELD_ERROR_KEYS = [
    "timeseries.path",
    "timeseries.first_day_of_water_year",
    "components.name",
    "output.metric.mode",
    "output.plot.climate-canvas.threshold",
    "output.plot.climate-canvas.color_map_ticks",
]


@pytest.fixture
def app(root: tk.Tk) -> HydropatternGuiApp:
    controller = GuiController(InProcessHydropatternRunner())
    application = HydropatternGuiApp(root, controller)
    yield application
    for child in root.winfo_children():
        child.destroy()


def test_every_known_field_error_key_maps_to_a_real_widget(app: HydropatternGuiApp) -> None:
    widget_map = app._field_error_widgets()
    assert set(widget_map) == set(KNOWN_FIELD_ERROR_KEYS)
    for key, widget in widget_map.items():
        assert isinstance(widget, (ttk.Entry, ttk.Combobox)), key
        assert widget.winfo_exists()


def test_apply_field_errors_flips_matched_widgets_to_invalid_style(
    app: HydropatternGuiApp,
) -> None:
    app._apply_field_errors({"timeseries.path": "required"})
    assert app._path_entry.cget("style") == "Invalid.TEntry"
    assert app._component_name_entry.cget("style") != "Invalid.TEntry"

    app._apply_field_errors({})
    assert app._path_entry.cget("style") != "Invalid.TEntry"


def test_apply_field_errors_flips_combobox_to_invalid_style(app: HydropatternGuiApp) -> None:
    app._apply_field_errors({"output.metric.mode": "invalid mode"})
    assert app._metric_mode_combobox.cget("style") == "Invalid.TCombobox"

    app._apply_field_errors({})
    assert app._metric_mode_combobox.cget("style") != "Invalid.TCombobox"


def test_first_day_focusout_flags_non_numeric_value(app: HydropatternGuiApp) -> None:
    app._first_day_var.set("not-a-number")
    app._on_first_day_focusout(tk.Event())
    assert app._first_day_entry.cget("style") == "Invalid.TEntry"

    app._first_day_var.set("120")
    app._on_first_day_focusout(tk.Event())
    assert app._first_day_entry.cget("style") != "Invalid.TEntry"


def test_climate_threshold_focusout_allows_blank_but_flags_bad_float(
    app: HydropatternGuiApp,
) -> None:
    app._climate_threshold_var.set("abc")
    app._on_climate_threshold_focusout(tk.Event())
    assert app._climate_threshold_entry.cget("style") == "Invalid.TEntry"

    app._climate_threshold_var.set("")
    app._on_climate_threshold_focusout(tk.Event())
    assert app._climate_threshold_entry.cget("style") != "Invalid.TEntry"

    app._climate_threshold_var.set("1.5")
    app._on_climate_threshold_focusout(tk.Event())
    assert app._climate_threshold_entry.cget("style") != "Invalid.TEntry"


def test_first_day_entry_has_day_of_year_unit_label(app: HydropatternGuiApp) -> None:
    grid_slaves = app._first_day_entry.master.grid_slaves(row=2, column=2)
    assert grid_slaves, "expected a unit label in column 2 next to First day of WY entry"
    assert grid_slaves[0].cget("text") == "(1-366)"


def test_form_validation_error_field_errors_round_trips_into_widget_map(
    app: HydropatternGuiApp,
) -> None:
    exc = FormValidationError({"timeseries.first_day_of_water_year": "must be an integer"})
    app._apply_field_errors(exc.field_errors)
    assert app._first_day_entry.cget("style") == "Invalid.TEntry"
    app._apply_field_errors({})
    assert app._first_day_entry.cget("style") != "Invalid.TEntry"
