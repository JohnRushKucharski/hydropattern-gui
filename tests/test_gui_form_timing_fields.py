"""Bullet 1: pure translation tests for the Timing characteristic card.

Timing is the simplest kind: hydropattern's schema is always
[first_doy, last_doy] (two ints, 1-366) -- no operator, no Simple/Between
mode switch. Mirrors test_gui_form_magnitude_fields.py / duration but with
that reduced shape.
"""

import pytest

from hydropattern_gui.gui_form import (
    FormValidationError,
    TimingFields,
    timing_fields_to_metrics,
    timing_metrics_from_text,
)


def test_valid_timing_fields_produce_metrics_text() -> None:
    fields = TimingFields(first_day_of_year=100, last_day_of_year=200)
    assert timing_fields_to_metrics(fields) == "[100, 200]"


def test_missing_first_day_raises_field_error() -> None:
    fields = TimingFields(first_day_of_year=None, last_day_of_year=200)
    with pytest.raises(FormValidationError) as exc_info:
        timing_fields_to_metrics(fields)
    assert "first_day_of_year" in exc_info.value.field_errors


def test_missing_last_day_raises_field_error() -> None:
    fields = TimingFields(first_day_of_year=100, last_day_of_year=None)
    with pytest.raises(FormValidationError) as exc_info:
        timing_fields_to_metrics(fields)
    assert "last_day_of_year" in exc_info.value.field_errors


def test_metrics_text_round_trips_to_timing_fields() -> None:
    fields = timing_metrics_from_text("[100, 200]")
    assert fields == TimingFields(first_day_of_year=100, last_day_of_year=200)


def test_invalid_metrics_text_raises_field_error() -> None:
    with pytest.raises(FormValidationError):
        timing_metrics_from_text("not a list")


def test_wrong_length_metrics_text_raises_field_error() -> None:
    with pytest.raises(FormValidationError):
        timing_metrics_from_text("[100]")
