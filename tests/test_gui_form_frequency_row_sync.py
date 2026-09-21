"""Bullets 3+5: sync/extract/offset tests for the Frequency characteristic
card. Mirrors test_gui_form_rate_of_change_row_sync.py.
"""

from hydropattern_gui.gui_form import (
    CharacteristicRowState,
    FrequencyFields,
    FrequencyPatternFields,
    extract_frequency_state,
    frequency_insertion_offset,
    sync_frequency_row,
)

_BASE = FrequencyPatternFields(
    mode="count",
    operator=">",
    count_n=3,
    probability=None,
    between_min=None,
    between_max=None,
    out_of_n=10,
    count_by_event=True,
)
_BLANK_PATTERN = FrequencyPatternFields(
    mode="count",
    operator=None,
    count_n=None,
    probability=None,
    between_min=None,
    between_max=None,
    out_of_n=None,
    count_by_event=True,
)
_FIELDS = FrequencyFields(nested_enabled=False, base=_BASE, nested=_BLANK_PATTERN)


def test_sync_adds_frequency_row_when_enabled() -> None:
    rows = sync_frequency_row([], enabled=True, fields=_FIELDS)
    assert rows == [CharacteristicRowState(kind="frequency", metrics_text='[">", 3, 10, True]')]


def test_sync_omits_frequency_row_when_disabled() -> None:
    rows = sync_frequency_row(
        [CharacteristicRowState(kind="frequency", metrics_text='[">", 1, 5, True]')],
        enabled=False,
        fields=_FIELDS,
    )
    assert rows == []


def test_sync_preserves_existing_position_when_already_present() -> None:
    rows = [
        CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]'),
        CharacteristicRowState(kind="frequency", metrics_text='[">", 1, 5, True]'),
        CharacteristicRowState(kind="duration", metrics_text='[">", 3]'),
    ]
    result = sync_frequency_row(rows, enabled=True, fields=_FIELDS)
    assert [row.kind for row in result] == ["magnitude", "frequency", "duration"]
    assert result[1].metrics_text == '[">", 3, 10, True]'


def test_sync_inserts_at_offset_when_new() -> None:
    rows = [
        CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]'),
        CharacteristicRowState(kind="duration", metrics_text='[">", 3]'),
    ]
    result = sync_frequency_row(rows, enabled=True, fields=_FIELDS, insert_at=1)
    assert [row.kind for row in result] == ["magnitude", "frequency", "duration"]


def test_sync_clamps_insert_at_to_bounds() -> None:
    rows = [CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]')]
    result = sync_frequency_row(rows, enabled=True, fields=_FIELDS, insert_at=99)
    assert [row.kind for row in result] == ["magnitude", "frequency"]


def test_frequency_insertion_offset_counts_preceding_rows() -> None:
    rows = [
        CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]'),
        CharacteristicRowState(kind="duration", metrics_text='[">", 3]'),
        CharacteristicRowState(kind="frequency", metrics_text='[">", 1, 5, True]'),
    ]
    assert frequency_insertion_offset(rows) == 2


def test_frequency_insertion_offset_is_zero_when_absent() -> None:
    assert frequency_insertion_offset([]) == 0


def test_extract_frequency_state_returns_fields_when_present() -> None:
    rows = [CharacteristicRowState(kind="frequency", metrics_text='[">", 3, 10, True]')]
    enabled, fields = extract_frequency_state(rows)
    assert enabled is True
    assert fields == _FIELDS


def test_extract_frequency_state_returns_disabled_blank_when_absent() -> None:
    enabled, fields = extract_frequency_state([])
    assert enabled is False
    assert fields.nested_enabled is False
