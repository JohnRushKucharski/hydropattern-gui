"""Bullet 1: pure translation tests for the Rate of Change characteristic
card.

Rate of change has 3 cascading optional positional params (ma_periods ->
look_back -> min): hydropattern requires each earlier optional to be a
real int/float if a later one is supplied (no null placeholder), so the
typed fields enforce the same cascade rule.
"""

import pytest

from hydropattern_gui.gui_form import (
    FormValidationError,
    RateOfChangeFields,
    rate_of_change_fields_to_metrics,
    rate_of_change_metrics_from_text,
)


def _fields(**overrides: object) -> RateOfChangeFields:
    base: dict[str, object] = dict(
        mode="simple",
        operator=">",
        threshold=1.5,
        minimum=None,
        maximum=None,
        ma_enabled=False,
        ma_periods=None,
        look_back_enabled=False,
        look_back=None,
        min_enabled=False,
        min_value=None,
    )
    base.update(overrides)
    return RateOfChangeFields(**base)  # type: ignore[arg-type]


def test_simple_with_no_optionals_produces_metrics_text() -> None:
    assert rate_of_change_fields_to_metrics(_fields()) == '[">", 1.5]'


def test_between_with_no_optionals_produces_metrics_text() -> None:
    fields = _fields(mode="between", operator=None, threshold=None, minimum=1.0, maximum=5.0)
    assert rate_of_change_fields_to_metrics(fields) == "[1.0, 5.0]"


def test_ma_enabled_appends_ma_periods() -> None:
    fields = _fields(ma_enabled=True, ma_periods=3)
    assert rate_of_change_fields_to_metrics(fields) == '[">", 1.5, 3]'


def test_look_back_enabled_appends_look_back_after_ma_periods() -> None:
    fields = _fields(ma_enabled=True, ma_periods=3, look_back_enabled=True, look_back=2)
    assert rate_of_change_fields_to_metrics(fields) == '[">", 1.5, 3, 2]'


def test_min_enabled_appends_min_after_look_back() -> None:
    fields = _fields(
        ma_enabled=True, ma_periods=3,
        look_back_enabled=True, look_back=2,
        min_enabled=True, min_value=0.0,
    )
    assert rate_of_change_fields_to_metrics(fields) == '[">", 1.5, 3, 2, 0.0]'


def test_look_back_enabled_without_ma_enabled_raises_cascade_error() -> None:
    fields = _fields(look_back_enabled=True, look_back=2)
    with pytest.raises(FormValidationError) as exc_info:
        rate_of_change_fields_to_metrics(fields)
    assert "look_back" in exc_info.value.field_errors


def test_min_enabled_without_look_back_enabled_raises_cascade_error() -> None:
    fields = _fields(ma_enabled=True, ma_periods=3, min_enabled=True, min_value=0.0)
    with pytest.raises(FormValidationError) as exc_info:
        rate_of_change_fields_to_metrics(fields)
    assert "min_value" in exc_info.value.field_errors


def test_missing_threshold_raises_field_error() -> None:
    fields = _fields(threshold=None)
    with pytest.raises(FormValidationError) as exc_info:
        rate_of_change_fields_to_metrics(fields)
    assert "threshold" in exc_info.value.field_errors


def test_metrics_text_with_two_items_round_trips_simple() -> None:
    fields = rate_of_change_metrics_from_text('[">", 1.5]')
    assert fields == _fields()


def test_metrics_text_with_three_items_round_trips_ma_enabled() -> None:
    fields = rate_of_change_metrics_from_text('[">", 1.5, 3]')
    assert fields == _fields(ma_enabled=True, ma_periods=3)


def test_metrics_text_with_four_items_round_trips_look_back_enabled() -> None:
    fields = rate_of_change_metrics_from_text('[">", 1.5, 3, 2]')
    assert fields == _fields(ma_enabled=True, ma_periods=3, look_back_enabled=True, look_back=2)


def test_metrics_text_with_five_items_round_trips_min_enabled() -> None:
    fields = rate_of_change_metrics_from_text('[">", 1.5, 3, 2, 0.0]')
    assert fields == _fields(
        ma_enabled=True, ma_periods=3,
        look_back_enabled=True, look_back=2,
        min_enabled=True, min_value=0.0,
    )


def test_metrics_text_between_round_trips() -> None:
    fields = rate_of_change_metrics_from_text("[1.0, 5.0]")
    assert fields == _fields(
        mode="between", operator=None, threshold=None, minimum=1.0, maximum=5.0
    )


def test_invalid_metrics_text_raises_field_error() -> None:
    with pytest.raises(FormValidationError):
        rate_of_change_metrics_from_text("not a list")


def test_wrong_length_metrics_text_raises_field_error() -> None:
    with pytest.raises(FormValidationError):
        rate_of_change_metrics_from_text("[1]")
