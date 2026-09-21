"""Headless widget tests for the typed-card visual order indicator
(HANDOFF.md Task 6 -- magnitude-card-visual-order-indicator, generalized to
all 5 typed cards): each enabled card shows a "#N" badge reflecting its
1-based position among currently-active rows; disabled cards show no
badge. No window is shown and mainloop() is never called."""

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


def test_order_label_blank_when_card_disabled(app: HydropatternGuiApp) -> None:
    assert app._order_labels["timing"].cget("text") == ""


def test_order_label_shows_position_one_for_single_enabled_card(
    app: HydropatternGuiApp,
) -> None:
    app._timing_enabled_var.set(True)
    assert app._order_labels["timing"].cget("text") == "#1"


def test_order_labels_reflect_row_order_across_multiple_enabled_cards(
    app: HydropatternGuiApp,
) -> None:
    app._timing_enabled_var.set(True)
    app._magnitude_enabled_var.set(True)
    app._duration_enabled_var.set(True)
    # default self._row_order is timing, magnitude, rate_of_change,
    # duration, frequency -- active subset preserves that relative order.
    assert app._order_labels["timing"].cget("text") == "#1"
    assert app._order_labels["magnitude"].cget("text") == "#2"
    assert app._order_labels["duration"].cget("text") == "#3"
    assert app._order_labels["rate_of_change"].cget("text") == ""


def test_order_labels_update_after_move_row(app: HydropatternGuiApp) -> None:
    app._timing_enabled_var.set(True)
    app._magnitude_enabled_var.set(True)
    assert app._order_labels["timing"].cget("text") == "#1"
    assert app._order_labels["magnitude"].cget("text") == "#2"

    app._move_row("magnitude", -1)
    assert app._order_labels["magnitude"].cget("text") == "#1"
    assert app._order_labels["timing"].cget("text") == "#2"


def test_order_label_clears_when_card_disabled_again(app: HydropatternGuiApp) -> None:
    app._timing_enabled_var.set(True)
    assert app._order_labels["timing"].cget("text") == "#1"
    app._timing_enabled_var.set(False)
    assert app._order_labels["timing"].cget("text") == ""
