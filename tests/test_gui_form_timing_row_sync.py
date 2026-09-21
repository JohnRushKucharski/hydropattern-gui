"""Bullets 3+5: sync/extract/offset tests for the Timing characteristic card.

Mirrors test_gui_form_duration_row_sync.py.
"""

from hydropattern_gui.gui_form import (
    CharacteristicRowState,
    TimingFields,
    extract_timing_state,
    sync_timing_row,
    timing_insertion_offset,
)

_FIELDS = TimingFields(first_day_of_year=100, last_day_of_year=200)


def test_sync_adds_timing_row_when_enabled() -> None:
    rows = sync_timing_row([], enabled=True, fields=_FIELDS)
    assert rows == [CharacteristicRowState(kind="timing", metrics_text="[100, 200]")]


def test_sync_omits_timing_row_when_disabled() -> None:
    rows = sync_timing_row(
        [CharacteristicRowState(kind="timing", metrics_text="[1, 2]")],
        enabled=False,
        fields=_FIELDS,
    )
    assert rows == []


def test_sync_preserves_existing_position_when_already_present() -> None:
    rows = [
        CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]'),
        CharacteristicRowState(kind="timing", metrics_text="[1, 2]"),
        CharacteristicRowState(kind="duration", metrics_text='[">", 3]'),
    ]
    result = sync_timing_row(rows, enabled=True, fields=_FIELDS)
    assert [row.kind for row in result] == ["magnitude", "timing", "duration"]
    assert result[1].metrics_text == "[100, 200]"


def test_sync_inserts_at_offset_when_new() -> None:
    rows = [
        CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]'),
        CharacteristicRowState(kind="duration", metrics_text='[">", 3]'),
    ]
    result = sync_timing_row(rows, enabled=True, fields=_FIELDS, insert_at=1)
    assert [row.kind for row in result] == ["magnitude", "timing", "duration"]


def test_sync_clamps_insert_at_to_bounds() -> None:
    rows = [CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]')]
    result = sync_timing_row(rows, enabled=True, fields=_FIELDS, insert_at=99)
    assert [row.kind for row in result] == ["magnitude", "timing"]


def test_timing_insertion_offset_counts_preceding_rows() -> None:
    rows = [
        CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]'),
        CharacteristicRowState(kind="duration", metrics_text='[">", 3]'),
        CharacteristicRowState(kind="timing", metrics_text="[1, 2]"),
    ]
    assert timing_insertion_offset(rows) == 2


def test_timing_insertion_offset_is_zero_when_absent() -> None:
    assert timing_insertion_offset([]) == 0


def test_extract_timing_state_returns_fields_when_present() -> None:
    rows = [CharacteristicRowState(kind="timing", metrics_text="[100, 200]")]
    enabled, fields = extract_timing_state(rows)
    assert enabled is True
    assert fields == _FIELDS


def test_extract_timing_state_returns_disabled_blank_when_absent() -> None:
    enabled, fields = extract_timing_state([])
    assert enabled is False
    assert fields == TimingFields(first_day_of_year=None, last_day_of_year=None)
