"""Tests for syncing typed Duration card state with characteristic_rows,
mirroring test_gui_form_magnitude_row_sync.py."""

from hydropattern_gui.gui_form import (
    CharacteristicRowState,
    DurationFields,
    duration_insertion_offset,
    extract_duration_state,
    sync_duration_row,
)

_BLANK_SIMPLE = DurationFields(mode="simple", operator=None, steps=None, min_steps=None, max_steps=None)


def test_sync_disabled_removes_duration_row_and_keeps_others() -> None:
    rows = [
        CharacteristicRowState(kind="timing", metrics_text="[1, 366]"),
        CharacteristicRowState(kind="duration", metrics_text='[">", 7]'),
    ]
    updated = sync_duration_row(rows, enabled=False, fields=_BLANK_SIMPLE)
    assert [row.kind for row in updated] == ["timing"]


def test_sync_enabled_appends_duration_row_when_absent() -> None:
    rows = [CharacteristicRowState(kind="timing", metrics_text="[1, 366]")]
    fields = DurationFields(mode="simple", operator=">", steps=7, min_steps=None, max_steps=None)
    updated = sync_duration_row(rows, enabled=True, fields=fields)
    assert [row.kind for row in updated] == ["timing", "duration"]
    assert updated[1].metrics_text == '[">", 7]'


def test_sync_enabled_updates_in_place_preserving_position() -> None:
    rows = [
        CharacteristicRowState(kind="duration", metrics_text='[">", 7]'),
        CharacteristicRowState(kind="frequency", metrics_text='[">", 1, 2]'),
    ]
    fields = DurationFields(mode="between", operator=None, steps=None, min_steps=1, max_steps=5)
    updated = sync_duration_row(rows, enabled=True, fields=fields)
    assert [row.kind for row in updated] == ["duration", "frequency"]
    assert updated[0].metrics_text == "[1, 5]"


def test_sync_enabled_inserts_at_requested_offset_when_absent() -> None:
    rows = [
        CharacteristicRowState(kind="timing", metrics_text="[1, 366]"),
        CharacteristicRowState(kind="frequency", metrics_text='[">", 1, 2]'),
    ]
    fields = DurationFields(mode="simple", operator=">", steps=3, min_steps=None, max_steps=None)
    updated = sync_duration_row(rows, enabled=True, fields=fields, insert_at=1)
    assert [row.kind for row in updated] == ["timing", "duration", "frequency"]


def test_duration_insertion_offset_counts_rows_before_duration() -> None:
    rows = [
        CharacteristicRowState(kind="timing", metrics_text="[1, 366]"),
        CharacteristicRowState(kind="duration", metrics_text='[">", 7]'),
    ]
    assert duration_insertion_offset(rows) == 1


def test_duration_insertion_offset_defaults_to_zero_when_absent() -> None:
    rows = [CharacteristicRowState(kind="timing", metrics_text="[1, 366]")]
    assert duration_insertion_offset(rows) == 0


def test_extract_absent_duration_defaults_to_disabled_blank_simple() -> None:
    rows = [CharacteristicRowState(kind="timing", metrics_text="[1, 366]")]
    enabled, fields = extract_duration_state(rows)
    assert enabled is False
    assert fields == _BLANK_SIMPLE


def test_extract_present_duration_parses_typed_fields() -> None:
    rows = [CharacteristicRowState(kind="duration", metrics_text="[1, 5]")]
    enabled, fields = extract_duration_state(rows)
    assert enabled is True
    assert fields == DurationFields(mode="between", operator=None, steps=None, min_steps=1, max_steps=5)


def test_round_trip_sync_then_extract() -> None:
    fields = DurationFields(mode="simple", operator=">=", steps=4, min_steps=None, max_steps=None)
    rows = sync_duration_row([], enabled=True, fields=fields)
    enabled, extracted = extract_duration_state(rows)
    assert enabled is True
    assert extracted == fields
