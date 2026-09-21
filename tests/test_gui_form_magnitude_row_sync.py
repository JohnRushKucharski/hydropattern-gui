"""TDD tests for syncing the typed Magnitude card state with the
characteristic_rows list (the model shared with the other, still-generic
characteristic rows)."""

from hydropattern_gui.gui_form import (
    CharacteristicRowState,
    MagnitudeFields,
    extract_magnitude_state,
    magnitude_insertion_offset,
    sync_magnitude_row,
)

_BLANK_SIMPLE = MagnitudeFields(
    mode="simple", operator=None, threshold=None, minimum=None, maximum=None,
    ma_enabled=False, ma_periods=None,
)


def test_sync_disabled_removes_magnitude_row_and_keeps_others() -> None:
    rows = [
        CharacteristicRowState(kind="timing", metrics_text="[1, 366]"),
        CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]'),
    ]
    updated = sync_magnitude_row(rows, enabled=False, fields=_BLANK_SIMPLE)
    assert [row.kind for row in updated] == ["timing"]


def test_sync_enabled_appends_magnitude_row_when_absent() -> None:
    rows = [CharacteristicRowState(kind="timing", metrics_text="[1, 366]")]
    fields = MagnitudeFields(
        mode="simple", operator=">", threshold=1.0, minimum=None, maximum=None,
        ma_enabled=False, ma_periods=None,
    )
    updated = sync_magnitude_row(rows, enabled=True, fields=fields)
    assert [row.kind for row in updated] == ["timing", "magnitude"]
    assert updated[1].metrics_text == '[">", 1.0]'


def test_sync_enabled_updates_in_place_preserving_position() -> None:
    rows = [
        CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]'),
        CharacteristicRowState(kind="duration", metrics_text='[">", 7]'),
    ]
    fields = MagnitudeFields(
        mode="between", operator=None, threshold=None, minimum=0.0, maximum=5.0,
        ma_enabled=False, ma_periods=None,
    )
    updated = sync_magnitude_row(rows, enabled=True, fields=fields)
    assert [row.kind for row in updated] == ["magnitude", "duration"]
    assert updated[0].metrics_text == "[0.0, 5.0]"


def test_sync_enabled_inserts_at_requested_offset_when_absent() -> None:
    rows = [
        CharacteristicRowState(kind="timing", metrics_text="[1, 366]"),
        CharacteristicRowState(kind="duration", metrics_text='[">", 7]'),
    ]
    fields = MagnitudeFields(
        mode="simple", operator=">", threshold=1.0, minimum=None, maximum=None,
        ma_enabled=False, ma_periods=None,
    )
    updated = sync_magnitude_row(rows, enabled=True, fields=fields, insert_at=1)
    assert [row.kind for row in updated] == ["timing", "magnitude", "duration"]


def test_sync_enabled_clamps_out_of_range_insert_at() -> None:
    rows = [CharacteristicRowState(kind="timing", metrics_text="[1, 366]")]
    fields = MagnitudeFields(
        mode="simple", operator=">", threshold=1.0, minimum=None, maximum=None,
        ma_enabled=False, ma_periods=None,
    )
    updated_high = sync_magnitude_row(rows, enabled=True, fields=fields, insert_at=99)
    assert [row.kind for row in updated_high] == ["timing", "magnitude"]
    updated_low = sync_magnitude_row(rows, enabled=True, fields=fields, insert_at=-5)
    assert [row.kind for row in updated_low] == ["magnitude", "timing"]


def test_magnitude_insertion_offset_counts_rows_before_magnitude() -> None:
    rows = [
        CharacteristicRowState(kind="timing", metrics_text="[1, 366]"),
        CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]'),
        CharacteristicRowState(kind="duration", metrics_text='[">", 7]'),
    ]
    assert magnitude_insertion_offset(rows) == 1


def test_magnitude_insertion_offset_defaults_to_zero_when_absent() -> None:
    rows = [CharacteristicRowState(kind="timing", metrics_text="[1, 366]")]
    assert magnitude_insertion_offset(rows) == 0


def test_sync_enabled_with_incomplete_fields_falls_back_to_empty_metrics() -> None:
    rows: list[CharacteristicRowState] = []
    updated = sync_magnitude_row(rows, enabled=True, fields=_BLANK_SIMPLE)
    assert updated[0].kind == "magnitude"
    assert updated[0].metrics_text == ""


def test_extract_absent_magnitude_defaults_to_disabled_blank_simple() -> None:
    rows = [CharacteristicRowState(kind="timing", metrics_text="[1, 366]")]
    enabled, fields = extract_magnitude_state(rows)
    assert enabled is False
    assert fields == _BLANK_SIMPLE


def test_extract_present_magnitude_parses_typed_fields() -> None:
    rows = [CharacteristicRowState(kind="magnitude", metrics_text='[">", 2.5, 3]')]
    enabled, fields = extract_magnitude_state(rows)
    assert enabled is True
    assert fields == MagnitudeFields(
        mode="simple", operator=">", threshold=2.5, minimum=None, maximum=None,
        ma_enabled=True, ma_periods=3,
    )


def test_extract_present_but_unparseable_magnitude_treated_as_enabled_blank() -> None:
    rows = [CharacteristicRowState(kind="magnitude", metrics_text="")]
    enabled, fields = extract_magnitude_state(rows)
    assert enabled is True
    assert fields == _BLANK_SIMPLE


def test_round_trip_sync_then_extract() -> None:
    fields = MagnitudeFields(
        mode="between", operator=None, threshold=None, minimum=1.0, maximum=9.0,
        ma_enabled=True, ma_periods=4,
    )
    rows = sync_magnitude_row([], enabled=True, fields=fields)
    enabled, extracted = extract_magnitude_state(rows)
    assert enabled is True
    assert extracted == fields
