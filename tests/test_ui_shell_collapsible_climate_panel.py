"""Headless widget tests for Task 5 collapsible advanced panel (HANDOFF.md
phase5-collapsible-advanced-panel): the climate-canvas section body toggles
via grid()/grid_remove(), idempotently, and the header button's disclosure
glyph flips each call. No window is shown and mainloop() is never called."""

from __future__ import annotations

import tkinter as tk

import pytest

from hydropattern_gui.runner_service import InProcessHydropatternRunner
from hydropattern_gui.ui_shell import GuiController, HydropatternGuiApp


@pytest.fixture
def app(root: tk.Tk) -> HydropatternGuiApp:
    controller = GuiController(InProcessHydropatternRunner())
    application = HydropatternGuiApp(root, controller)
    yield application
    for child in root.winfo_children():
        child.destroy()


def test_climate_panel_starts_expanded(app: HydropatternGuiApp) -> None:
    assert app._climate_panel_expanded is True
    assert app._climate_body.winfo_manager() == "grid"
    assert app._climate_toggle_button.cget("text") == "\u25be Advanced"


def test_toggle_collapses_and_restores_climate_panel(app: HydropatternGuiApp) -> None:
    original_grid_info = app._climate_body.grid_info()

    app._on_toggle_climate_panel()
    assert app._climate_panel_expanded is False
    assert app._climate_body.winfo_manager() == ""
    assert app._climate_toggle_button.cget("text") == "\u25b8 Advanced"

    app._on_toggle_climate_panel()
    assert app._climate_panel_expanded is True
    assert app._climate_body.winfo_manager() == "grid"
    assert app._climate_toggle_button.cget("text") == "\u25be Advanced"
    assert app._climate_body.grid_info() == original_grid_info


def test_toggle_twice_more_is_idempotent(app: HydropatternGuiApp) -> None:
    for _ in range(4):
        app._on_toggle_climate_panel()
    assert app._climate_panel_expanded is True
    assert app._climate_body.winfo_manager() == "grid"


def test_climate_field_entries_remain_reachable_when_collapsed(
    app: HydropatternGuiApp,
) -> None:
    """Field-error highlighting (Task 3) must still work even while the
    advanced panel is collapsed -- the widgets exist regardless of grid
    visibility, so _apply_field_errors can still flag them."""
    app._on_toggle_climate_panel()
    app._apply_field_errors({"output.plot.climate-canvas.threshold": "must be a number"})
    assert app._climate_threshold_entry.cget("style") == "Invalid.TEntry"
    app._apply_field_errors({})
