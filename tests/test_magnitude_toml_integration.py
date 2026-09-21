"""Bullet 6: integration round-trip for the Magnitude card path.

Builds a GuiFormState the way the widget layer would (characteristic_rows
assembled via sync_magnitude_row from typed MagnitudeFields), then exercises
the full existing pipeline: config_from_form_state -> dumps_config_toml,
and confirms the TOML the user would actually see matches expectations.
This is the regression net for Bullets 1-5 working together.
"""

import tomllib

from hydropattern_gui.gui_form import (
    CharacteristicRowState,
    GuiFormState,
    MagnitudeFields,
    config_from_form_state,
    sync_magnitude_row,
)
from hydropattern_gui.config_model import dumps_config_toml


def _base_state(characteristic_rows: list[CharacteristicRowState]) -> GuiFormState:
    return GuiFormState(
        timeseries_path="examples/single_timeseries.csv",
        date_format="%Y-%m-%d",
        first_day_of_water_year="1",
        sheet_name="0",
        output_directory="",
        excel=True,
        overwrite=True,
        metric_mode="portion",
        component_name="simple_component",
        component_verbose=False,
        component_success_pattern=True,
        characteristic_rows=characteristic_rows,
    )


def test_magnitude_simple_with_moving_average_round_trips_through_toml() -> None:
    fields = MagnitudeFields(
        mode="simple", operator=">", threshold=1.5, minimum=None, maximum=None,
        ma_enabled=True, ma_periods=5,
    )
    rows = sync_magnitude_row([], enabled=True, fields=fields)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")
    data = tomllib.loads(toml_text)

    assert data["components"]["simple_component"]["magnitude"] == [">", 1.5, 5]


def test_magnitude_between_without_moving_average_round_trips_through_toml() -> None:
    fields = MagnitudeFields(
        mode="between", operator=None, threshold=None, minimum=0.0, maximum=10.0,
        ma_enabled=False, ma_periods=None,
    )
    rows = sync_magnitude_row([], enabled=True, fields=fields)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")
    data = tomllib.loads(toml_text)

    assert data["components"]["simple_component"]["magnitude"] == [0.0, 10.0]


def test_magnitude_placed_between_other_characteristics_preserves_toml_order() -> None:
    fields = MagnitudeFields(
        mode="simple", operator=">", threshold=1.0, minimum=None, maximum=None,
        ma_enabled=False, ma_periods=None,
    )
    rows = [
        CharacteristicRowState(kind="timing", metrics_text="[1, 366]"),
        CharacteristicRowState(kind="duration", metrics_text='[">", 7]'),
    ]
    rows = sync_magnitude_row(rows, enabled=True, fields=fields, insert_at=1)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")

    magnitude_pos = toml_text.find("magnitude =")
    timing_pos = toml_text.find("timing =")
    duration_pos = toml_text.find("duration =")
    assert timing_pos < magnitude_pos < duration_pos


def test_magnitude_disabled_is_absent_from_toml() -> None:
    fields = MagnitudeFields(
        mode="simple", operator=None, threshold=None, minimum=None, maximum=None,
        ma_enabled=False, ma_periods=None,
    )
    rows = sync_magnitude_row(
        [CharacteristicRowState(kind="timing", metrics_text="[1, 366]")],
        enabled=False,
        fields=fields,
    )
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")

    assert "magnitude" not in toml_text
