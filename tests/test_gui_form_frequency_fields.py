"""Bullet 1 (Frequency): pure translation tests for the Frequency
characteristic card.

Frequency has un-nested COUNT [operator, n, N] and BETWEEN
[min_n, max_n, N] forms, plus a PROBABILITY [operator, probability] form
that hydropattern only accepts as the *base* pattern of a nested spec
(never standalone). Nested frequency wraps a base pattern (COUNT, BETWEEN,
or PROBABILITY) and a dependent nested pattern (COUNT or BETWEEN only) as
[base_list, nested_list]. Per user decision, count_by_event is always
emitted explicitly (never omitted for its default of True).
"""

import pytest

from hydropattern_gui.gui_form import (
    FormValidationError,
    FrequencyFields,
    FrequencyPatternFields,
    frequency_fields_to_metrics,
    frequency_metrics_from_text,
)


def _pattern(**overrides: object) -> FrequencyPatternFields:
    base: dict[str, object] = dict(
        mode="count",
        operator=">",
        count_n=3,
        probability=None,
        between_min=None,
        between_max=None,
        out_of_n=10,
        count_by_event=True,
    )
    base.update(overrides)
    return FrequencyPatternFields(**base)  # type: ignore[arg-type]


def _blank_pattern() -> FrequencyPatternFields:
    return FrequencyPatternFields(
        mode="count",
        operator=None,
        count_n=None,
        probability=None,
        between_min=None,
        between_max=None,
        out_of_n=None,
        count_by_event=True,
    )


def _fields(**overrides: object) -> FrequencyFields:
    base: dict[str, object] = dict(
        nested_enabled=False,
        base=_pattern(),
        nested=_blank_pattern(),
    )
    base.update(overrides)
    return FrequencyFields(**base)  # type: ignore[arg-type]


def test_count_form_produces_metrics_text() -> None:
    assert frequency_fields_to_metrics(_fields()) == '[">", 3, 10, True]'


def test_between_form_produces_metrics_text() -> None:
    fields = _fields(
        base=_pattern(mode="between", operator=None, count_n=None, between_min=1, between_max=5, out_of_n=10)
    )
    assert frequency_fields_to_metrics(fields) == "[1, 5, 10, True]"


def test_count_by_event_false_is_emitted() -> None:
    fields = _fields(base=_pattern(count_by_event=False))
    assert frequency_fields_to_metrics(fields) == '[">", 3, 10, False]'


def test_standalone_probability_raises_field_error() -> None:
    fields = _fields(base=_pattern(mode="probability", operator=">", count_n=None, probability=0.5, out_of_n=None))
    with pytest.raises(FormValidationError) as exc_info:
        frequency_fields_to_metrics(fields)
    assert "base_mode" in exc_info.value.field_errors


def test_missing_count_n_raises_field_error() -> None:
    fields = _fields(base=_pattern(count_n=None))
    with pytest.raises(FormValidationError) as exc_info:
        frequency_fields_to_metrics(fields)
    assert "base_count_n" in exc_info.value.field_errors


def test_nested_count_base_with_count_nested_produces_metrics_text() -> None:
    fields = _fields(
        nested_enabled=True,
        base=_pattern(),
        nested=_pattern(operator="<", count_n=1, out_of_n=4),
    )
    assert frequency_fields_to_metrics(fields) == '[[">", 3, 10, True], ["<", 1, 4, True]]'


def test_nested_probability_base_is_allowed() -> None:
    fields = _fields(
        nested_enabled=True,
        base=_pattern(mode="probability", operator=">", count_n=None, probability=0.5, out_of_n=None),
        nested=_pattern(),
    )
    assert frequency_fields_to_metrics(fields) == '[[">", 0.5, True], [">", 3, 10, True]]'


def test_nested_probability_in_nested_slot_raises_field_error() -> None:
    fields = _fields(
        nested_enabled=True,
        base=_pattern(),
        nested=_pattern(mode="probability", operator=">", count_n=None, probability=0.5, out_of_n=None),
    )
    with pytest.raises(FormValidationError) as exc_info:
        frequency_fields_to_metrics(fields)
    assert "nested_mode" in exc_info.value.field_errors


def test_metrics_text_round_trips_count_form() -> None:
    fields = frequency_metrics_from_text('[">", 3, 10, True]')
    assert fields == _fields()


def test_metrics_text_round_trips_between_form() -> None:
    fields = frequency_metrics_from_text("[1, 5, 10, True]")
    assert fields == _fields(
        base=_pattern(mode="between", operator=None, count_n=None, between_min=1, between_max=5, out_of_n=10)
    )


def test_metrics_text_round_trips_count_by_event_false() -> None:
    fields = frequency_metrics_from_text('[">", 3, 10, False]')
    assert fields == _fields(base=_pattern(count_by_event=False))


def test_metrics_text_defaults_count_by_event_true_when_omitted() -> None:
    fields = frequency_metrics_from_text('[">", 3, 10]')
    assert fields == _fields()


def test_metrics_text_round_trips_nested_form() -> None:
    fields = frequency_metrics_from_text('[[">", 3, 10, True], ["<", 1, 4, True]]')
    assert fields == _fields(
        nested_enabled=True,
        base=_pattern(),
        nested=_pattern(operator="<", count_n=1, out_of_n=4),
    )


def test_metrics_text_round_trips_nested_probability_base() -> None:
    fields = frequency_metrics_from_text('[[">", 0.5, True], [">", 3, 10, True]]')
    assert fields == _fields(
        nested_enabled=True,
        base=_pattern(mode="probability", operator=">", count_n=None, probability=0.5, out_of_n=None),
        nested=_pattern(),
    )


def test_invalid_metrics_text_raises_field_error() -> None:
    with pytest.raises(FormValidationError):
        frequency_metrics_from_text("not a list")


def test_empty_metrics_text_raises_field_error() -> None:
    with pytest.raises(FormValidationError):
        frequency_metrics_from_text("[]")
