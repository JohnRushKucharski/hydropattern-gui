"""Headless widget tests for the generic reorder/enable-state helpers in
ui_shell.py (_update_reorder_buttons / _update_card_enabled_state /
_refresh_all_reorder_buttons), which replaced 5 near-duplicated per-kind
method families during the thermo-nuclear-code-review-pre-phase1 refactor.
No window is shown and mainloop() is never called."""

from __future__ import annotations

import tkinter as tk

import pytest

from hydropattern_gui.runner_service import InProcessHydropatternRunner
from hydropattern_gui.ui_shell import GuiController, HydropatternGuiApp


@pytest.fixture(scope="module")
def root() -> tk.Tk:
    try:
        tk_root = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - no display/broken Tk install
        pytest.skip(f"Tk display unavailable: {exc}")
    tk_root.withdraw()
    yield tk_root
    tk_root.destroy()


@pytest.fixture
def app(root: tk.Tk) -> HydropatternGuiApp:
    # Reuse a single module-scoped Tk() root across tests (repeatedly creating
    # tk.Tk() in-process is unreliable in this environment's Tk install) and
    # just clear its children between tests instead of destroying the root.
    controller = GuiController(InProcessHydropatternRunner())
    application = HydropatternGuiApp(root, controller)
    yield application
    for child in root.winfo_children():
        child.destroy()


def _safe_pack_info(widget: tk.Widget) -> bool:
    try:
        widget.pack_info()
        return True
    except tk.TclError:
        return False


def test_disabled_card_hides_reorder_buttons_by_default(app: HydropatternGuiApp) -> None:
    up_button, down_button = app._reorder_buttons["magnitude"]
    assert not _safe_pack_info(up_button)
    assert not _safe_pack_info(down_button)


def test_enabling_card_shows_reorder_buttons_and_updates_state(
    app: HydropatternGuiApp,
) -> None:
    app._magnitude_enabled_var.set(True)
    up_button, down_button = app._reorder_buttons["magnitude"]
    assert _safe_pack_info(up_button)
    assert _safe_pack_info(down_button)
    # magnitude is the only active row -> both ends of the (length-1) list.
    assert str(up_button["state"]) == "disabled"
    assert str(down_button["state"]) == "disabled"
    assert app._magnitude_body.winfo_manager() == "grid"


def test_disabling_card_hides_body_and_reorder_buttons(app: HydropatternGuiApp) -> None:
    app._duration_enabled_var.set(True)
    app._duration_enabled_var.set(False)
    up_button, down_button = app._reorder_buttons["duration"]
    assert not _safe_pack_info(up_button)
    assert not _safe_pack_info(down_button)
    assert not app._duration_body.grid_info()


def test_move_row_swaps_active_order_and_button_bounds(app: HydropatternGuiApp) -> None:
    app._magnitude_enabled_var.set(True)
    app._duration_enabled_var.set(True)
    assert app._active_row_order() == ["magnitude", "duration"]

    magnitude_up, magnitude_down = app._reorder_buttons["magnitude"]
    duration_up, duration_down = app._reorder_buttons["duration"]
    assert str(magnitude_up["state"]) == "disabled"
    assert str(magnitude_down["state"]) == "normal"
    assert str(duration_up["state"]) == "normal"
    assert str(duration_down["state"]) == "disabled"

    app._move_row("duration", -1)

    assert app._active_row_order() == ["duration", "magnitude"]
    assert str(duration_up["state"]) == "disabled"
    assert str(duration_down["state"]) == "normal"
    assert str(magnitude_up["state"]) == "normal"
    assert str(magnitude_down["state"]) == "disabled"
    # Visual grid stack follows the new order too.
    assert app._duration_card.grid_info()["row"] < app._magnitude_card.grid_info()["row"]
