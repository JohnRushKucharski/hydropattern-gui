"""Bullet 6: integration round-trip for the Duration card path.

Mirrors test_magnitude_toml_integration.py. Builds a GuiFormState the way
the widget layer would (characteristic_rows assembled via sync_duration_row
from typed DurationFields), then exercises the full existing pipeline:
config_from_form_state -> dumps_config_toml, confirming the TOML the user
would actually see matches expectations. This is the regression net for
Duration's pure logic (translation + sync/extract + offset) working
together end-to-end.
"""

import tomllib

from hydropattern_gui.gui_form import (
    CharacteristicRowState,
    DurationFields,
    GuiFormState,
    config_from_form_state,
    sync_duration_row,
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


def test_duration_simple_round_trips_through_toml() -> None:
    fields = DurationFields(
        mode="simple", operator=">", steps=7, min_steps=None, max_steps=None
    )
    rows = sync_duration_row([], enabled=True, fields=fields)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")
    data = tomllib.loads(toml_text)

    assert data["components"]["simple_component"]["duration"] == [">", 7]


def test_duration_between_round_trips_through_toml() -> None:
    fields = DurationFields(
        mode="between", operator=None, steps=None, min_steps=3, max_steps=14
    )
    rows = sync_duration_row([], enabled=True, fields=fields)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")
    data = tomllib.loads(toml_text)

    assert data["components"]["simple_component"]["duration"] == [3, 14]


def test_duration_placed_between_other_characteristics_preserves_toml_order() -> None:
    fields = DurationFields(
        mode="simple", operator=">", steps=5, min_steps=None, max_steps=None
    )
    rows = [
        CharacteristicRowState(kind="timing", metrics_text="[1, 366]"),
        CharacteristicRowState(kind="frequency", metrics_text='[">", 1, 10]'),
    ]
    rows = sync_duration_row(rows, enabled=True, fields=fields, insert_at=1)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")

    duration_pos = toml_text.find("duration =")
    timing_pos = toml_text.find("timing =")
    frequency_pos = toml_text.find("frequency =")
    assert timing_pos < duration_pos < frequency_pos


def test_duration_disabled_is_absent_from_toml() -> None:
    fields = DurationFields(
        mode="simple", operator=None, steps=None, min_steps=None, max_steps=None
    )
    rows = sync_duration_row(
        [CharacteristicRowState(kind="timing", metrics_text="[1, 366]")],
        enabled=False,
        fields=fields,
    )
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")

    assert "duration" not in toml_text
