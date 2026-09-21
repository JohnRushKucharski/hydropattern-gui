"""Characterization tests for Phase 1 of the TypedCard refactor (see
HANDOFF.md Task 1): self._cards[kind] must wrap the *same* widget/variable
objects as the legacy self._X_..._var attributes, with no behavior change.
No window is shown and mainloop() is never called."""

from __future__ import annotations

import tkinter as tk

import pytest

from hydropattern_gui.runner_service import InProcessHydropatternRunner
from hydropattern_gui.ui_shell import GuiController, HydropatternGuiApp, TypedCard


@pytest.fixture
def app(root: tk.Tk) -> HydropatternGuiApp:
    controller = GuiController(InProcessHydropatternRunner())
    application = HydropatternGuiApp(root, controller)
    yield application
    for child in root.winfo_children():
        child.destroy()


def test_cards_dict_has_one_entry_per_typed_kind(app: HydropatternGuiApp) -> None:
    assert set(app._cards) == {
        "timing",
        "magnitude",
        "duration",
        "rate_of_change",
        "frequency",
    }
    assert all(isinstance(card, TypedCard) for card in app._cards.values())


def test_timing_card_wraps_legacy_attributes(app: HydropatternGuiApp) -> None:
    card = app._cards["timing"]
    assert card.enabled_var is app._timing_enabled_var
    assert card.mode_var is None
    assert card.field_vars["first_day_of_year"] is app._timing_first_day_var
    assert card.field_vars["last_day_of_year"] is app._timing_last_day_var
    assert card.body is app._timing_body
    assert card.up_button is app._timing_up_button
    assert card.down_button is app._timing_down_button


def test_magnitude_card_wraps_legacy_attributes(app: HydropatternGuiApp) -> None:
    card = app._cards["magnitude"]
    assert card.enabled_var is app._magnitude_enabled_var
    assert card.mode_var is app._magnitude_mode_var
    assert card.field_vars["operator"] is app._magnitude_operator_var
    assert card.field_vars["threshold"] is app._magnitude_threshold_var
    assert card.field_vars["minimum"] is app._magnitude_min_var
    assert card.field_vars["maximum"] is app._magnitude_max_var
    assert card.field_vars["ma_enabled"] is app._magnitude_ma_enabled_var
    assert card.field_vars["ma_periods"] is app._magnitude_ma_periods_var
    assert card.body is app._magnitude_body
    assert card.up_button is app._magnitude_up_button
    assert card.down_button is app._magnitude_down_button


def test_duration_card_wraps_legacy_attributes(app: HydropatternGuiApp) -> None:
    card = app._cards["duration"]
    assert card.enabled_var is app._duration_enabled_var
    assert card.mode_var is app._duration_mode_var
    assert card.field_vars["operator"] is app._duration_operator_var
    assert card.field_vars["steps"] is app._duration_steps_var
    assert card.field_vars["min_steps"] is app._duration_min_var
    assert card.field_vars["max_steps"] is app._duration_max_var
    assert card.body is app._duration_body
    assert card.up_button is app._duration_up_button
    assert card.down_button is app._duration_down_button


def test_rate_of_change_card_wraps_legacy_attributes(app: HydropatternGuiApp) -> None:
    card = app._cards["rate_of_change"]
    assert card.enabled_var is app._roc_enabled_var
    assert card.mode_var is app._roc_mode_var
    assert card.field_vars["operator"] is app._roc_operator_var
    assert card.field_vars["threshold"] is app._roc_threshold_var
    assert card.field_vars["minimum"] is app._roc_min_var
    assert card.field_vars["maximum"] is app._roc_max_var
    assert card.field_vars["ma_enabled"] is app._roc_ma_enabled_var
    assert card.field_vars["ma_periods"] is app._roc_ma_periods_var
    assert card.field_vars["look_back_enabled"] is app._roc_look_back_enabled_var
    assert card.field_vars["look_back"] is app._roc_look_back_var
    assert card.field_vars["min_enabled"] is app._roc_min_enabled_var
    assert card.field_vars["min_value"] is app._roc_min_value_var
    assert card.body is app._roc_body
    assert card.up_button is app._roc_up_button
    assert card.down_button is app._roc_down_button


def test_frequency_card_wraps_legacy_attributes(app: HydropatternGuiApp) -> None:
    card = app._cards["frequency"]
    assert card.enabled_var is app._freq_enabled_var
    assert card.mode_var is None
    assert card.field_vars["nested_enabled"] is app._freq_nested_enabled_var
    for prefix in ("base", "nested"):
        for name, var in app._freq_vars[prefix].items():
            assert card.field_vars[f"{prefix}_{name}"] is var
    assert card.body is app._freq_body
    assert card.up_button is app._freq_up_button
    assert card.down_button is app._freq_down_button


def test_cards_are_pure_additive_wrapping_no_behavior_change(app: HydropatternGuiApp) -> None:
    # Mutating through the legacy attribute must still be reflected via the
    # card's field_vars (same underlying tk.Variable object), confirming
    # Phase 1 introduced no copies/behavior divergence.
    app._timing_first_day_var.set("123")
    assert app._cards["timing"].field_vars["first_day_of_year"].get() == "123"
    app._cards["magnitude"].enabled_var.set(True)
    assert app._magnitude_enabled_var.get() is True
    assert app._magnitude_body.grid_info()
