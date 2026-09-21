"""Bullets 3+5: sync/extract/offset tests for the Rate of Change
characteristic card. Mirrors test_gui_form_duration_row_sync.py.
"""

from hydropattern_gui.gui_form import (
    CharacteristicRowState,
    RateOfChangeFields,
    extract_rate_of_change_state,
    rate_of_change_insertion_offset,
    sync_rate_of_change_row,
)

_FIELDS = RateOfChangeFields(
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


def test_sync_adds_rate_of_change_row_when_enabled() -> None:
    rows = sync_rate_of_change_row([], enabled=True, fields=_FIELDS)
    assert rows == [CharacteristicRowState(kind="rate_of_change", metrics_text='[">", 1.5]')]


def test_sync_omits_rate_of_change_row_when_disabled() -> None:
    rows = sync_rate_of_change_row(
        [CharacteristicRowState(kind="rate_of_change", metrics_text='[">", 1]')],
        enabled=False,
        fields=_FIELDS,
    )
    assert rows == []


def test_sync_preserves_existing_position_when_already_present() -> None:
    rows = [
        CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]'),
        CharacteristicRowState(kind="rate_of_change", metrics_text='[">", 1]'),
        CharacteristicRowState(kind="duration", metrics_text='[">", 3]'),
    ]
    result = sync_rate_of_change_row(rows, enabled=True, fields=_FIELDS)
    assert [row.kind for row in result] == ["magnitude", "rate_of_change", "duration"]
    assert result[1].metrics_text == '[">", 1.5]'


def test_sync_inserts_at_offset_when_new() -> None:
    rows = [
        CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]'),
        CharacteristicRowState(kind="duration", metrics_text='[">", 3]'),
    ]
    result = sync_rate_of_change_row(rows, enabled=True, fields=_FIELDS, insert_at=1)
    assert [row.kind for row in result] == ["magnitude", "rate_of_change", "duration"]


def test_sync_clamps_insert_at_to_bounds() -> None:
    rows = [CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]')]
    result = sync_rate_of_change_row(rows, enabled=True, fields=_FIELDS, insert_at=99)
    assert [row.kind for row in result] == ["magnitude", "rate_of_change"]


def test_rate_of_change_insertion_offset_counts_preceding_rows() -> None:
    rows = [
        CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]'),
        CharacteristicRowState(kind="duration", metrics_text='[">", 3]'),
        CharacteristicRowState(kind="rate_of_change", metrics_text='[">", 1]'),
    ]
    assert rate_of_change_insertion_offset(rows) == 2


def test_rate_of_change_insertion_offset_is_zero_when_absent() -> None:
    assert rate_of_change_insertion_offset([]) == 0


def test_extract_rate_of_change_state_returns_fields_when_present() -> None:
    rows = [CharacteristicRowState(kind="rate_of_change", metrics_text='[">", 1.5]')]
    enabled, fields = extract_rate_of_change_state(rows)
    assert enabled is True
    assert fields == _FIELDS


def test_extract_rate_of_change_state_returns_disabled_blank_when_absent() -> None:
    enabled, fields = extract_rate_of_change_state([])
    assert enabled is False
    assert fields.ma_enabled is False
    assert fields.look_back_enabled is False
    assert fields.min_enabled is False
