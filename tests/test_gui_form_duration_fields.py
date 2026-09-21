"""TDD tests for the typed Duration card fields <-> metrics_text translation.

Duration metrics are simpler than Magnitude: [symbol, time_steps] or
[min_steps, max_steps], both integers >= 1, no optional moving-average.
"""

import pytest

from hydropattern_gui.gui_form import (
    DurationFields,
    FormValidationError,
    duration_fields_to_metrics,
    duration_metrics_from_text,
)


def test_simple_mode_round_trip() -> None:
    fields = DurationFields(mode="simple", operator=">", steps=7, min_steps=None, max_steps=None)
    text = duration_fields_to_metrics(fields)
    assert text == '[">", 7]'
    assert duration_metrics_from_text(text) == fields


def test_between_mode_round_trip() -> None:
    fields = DurationFields(mode="between", operator=None, steps=None, min_steps=1, max_steps=5)
    text = duration_fields_to_metrics(fields)
    assert text == "[1, 5]"
    assert duration_metrics_from_text(text) == fields


def test_simple_mode_requires_operator_and_steps() -> None:
    fields = DurationFields(mode="simple", operator=None, steps=None, min_steps=None, max_steps=None)
    with pytest.raises(FormValidationError) as exc_info:
        duration_fields_to_metrics(fields)
    assert "operator" in exc_info.value.field_errors
    assert "steps" in exc_info.value.field_errors


def test_between_mode_requires_min_and_max_steps() -> None:
    fields = DurationFields(mode="between", operator=None, steps=None, min_steps=None, max_steps=None)
    with pytest.raises(FormValidationError) as exc_info:
        duration_fields_to_metrics(fields)
    assert "min_steps" in exc_info.value.field_errors
    assert "max_steps" in exc_info.value.field_errors


def test_from_text_rejects_invalid_literal() -> None:
    with pytest.raises(FormValidationError) as exc_info:
        duration_metrics_from_text("not a list")
    assert "metrics" in exc_info.value.field_errors


def test_from_text_rejects_wrong_length() -> None:
    with pytest.raises(FormValidationError) as exc_info:
        duration_metrics_from_text("[1]")
    assert "metrics" in exc_info.value.field_errors
