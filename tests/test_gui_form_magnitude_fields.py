"""TDD tests for the typed Magnitude card fields <-> metrics_text translation.

These tests exercise pure logic only (no Tkinter widgets) so the
Simple/Between + moving-average behavior for the Magnitude characteristic
card can be verified independently of the GUI shell.
"""

import pytest

from hydropattern_gui.gui_form import (
    FormValidationError,
    MagnitudeFields,
    magnitude_fields_to_metrics,
    magnitude_metrics_from_text,
)


def test_simple_mode_round_trip_without_moving_average() -> None:
    fields = MagnitudeFields(
        mode="simple", operator=">", threshold=1.0, minimum=None, maximum=None,
        ma_enabled=False, ma_periods=None,
    )
    text = magnitude_fields_to_metrics(fields)
    assert text == '[">", 1.0]'
    assert magnitude_metrics_from_text(text) == fields


def test_between_mode_round_trip_without_moving_average() -> None:
    fields = MagnitudeFields(
        mode="between", operator=None, threshold=None, minimum=0.0, maximum=10.0,
        ma_enabled=False, ma_periods=None,
    )
    text = magnitude_fields_to_metrics(fields)
    assert text == "[0.0, 10.0]"
    assert magnitude_metrics_from_text(text) == fields


def test_simple_mode_round_trip_with_moving_average() -> None:
    fields = MagnitudeFields(
        mode="simple", operator=">", threshold=1.0, minimum=None, maximum=None,
        ma_enabled=True, ma_periods=5,
    )
    text = magnitude_fields_to_metrics(fields)
    assert text == '[">", 1.0, 5]'
    assert magnitude_metrics_from_text(text) == fields


def test_between_mode_round_trip_with_moving_average() -> None:
    fields = MagnitudeFields(
        mode="between", operator=None, threshold=None, minimum=0.0, maximum=10.0,
        ma_enabled=True, ma_periods=3,
    )
    text = magnitude_fields_to_metrics(fields)
    assert text == "[0.0, 10.0, 3]"
    assert magnitude_metrics_from_text(text) == fields


def test_ma_enabled_requires_periods_value() -> None:
    fields = MagnitudeFields(
        mode="simple", operator=">", threshold=1.0, minimum=None, maximum=None,
        ma_enabled=True, ma_periods=None,
    )
    with pytest.raises(FormValidationError) as exc_info:
        magnitude_fields_to_metrics(fields)
    assert "ma_periods" in exc_info.value.field_errors


def test_ma_disabled_ignores_stale_periods_value() -> None:
    """A previously-entered periods value must not leak into metrics_text
    once moving average is unchecked (cascade requirement)."""
    fields = MagnitudeFields(
        mode="simple", operator=">", threshold=1.0, minimum=None, maximum=None,
        ma_enabled=False, ma_periods=5,
    )
    assert magnitude_fields_to_metrics(fields) == '[">", 1.0]'


def test_simple_mode_requires_operator_and_threshold() -> None:
    fields = MagnitudeFields(
        mode="simple", operator=None, threshold=None, minimum=None, maximum=None,
        ma_enabled=False, ma_periods=None,
    )
    with pytest.raises(FormValidationError) as exc_info:
        magnitude_fields_to_metrics(fields)
    assert "operator" in exc_info.value.field_errors
    assert "threshold" in exc_info.value.field_errors


def test_between_mode_requires_min_and_max() -> None:
    fields = MagnitudeFields(
        mode="between", operator=None, threshold=None, minimum=None, maximum=None,
        ma_enabled=False, ma_periods=None,
    )
    with pytest.raises(FormValidationError) as exc_info:
        magnitude_fields_to_metrics(fields)
    assert "minimum" in exc_info.value.field_errors
    assert "maximum" in exc_info.value.field_errors


def test_from_text_rejects_invalid_literal() -> None:
    with pytest.raises(FormValidationError) as exc_info:
        magnitude_metrics_from_text("not a list")
    assert "metrics" in exc_info.value.field_errors


def test_from_text_rejects_wrong_length() -> None:
    with pytest.raises(FormValidationError) as exc_info:
        magnitude_metrics_from_text("[1.0]")
    assert "metrics" in exc_info.value.field_errors
