"""Bullet 6: integration round-trip for the Timing card path.

Mirrors test_magnitude_toml_integration.py / test_duration_toml_integration.py.
"""

import tomllib

from hydropattern_gui.gui_form import (
    CharacteristicRowState,
    GuiFormState,
    TimingFields,
    config_from_form_state,
    sync_timing_row,
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


def test_timing_round_trips_through_toml() -> None:
    fields = TimingFields(first_day_of_year=100, last_day_of_year=200)
    rows = sync_timing_row([], enabled=True, fields=fields)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")
    data = tomllib.loads(toml_text)

    assert data["components"]["simple_component"]["timing"] == [100, 200]


def test_timing_placed_before_other_characteristics_preserves_toml_order() -> None:
    fields = TimingFields(first_day_of_year=1, last_day_of_year=366)
    rows = [
        CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]'),
        CharacteristicRowState(kind="duration", metrics_text='[">", 7]'),
    ]
    rows = sync_timing_row(rows, enabled=True, fields=fields, insert_at=0)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")

    timing_pos = toml_text.find("timing =")
    magnitude_pos = toml_text.find("magnitude =")
    duration_pos = toml_text.find("duration =")
    assert timing_pos < magnitude_pos < duration_pos


def test_timing_disabled_is_absent_from_toml() -> None:
    fields = TimingFields(first_day_of_year=None, last_day_of_year=None)
    rows = sync_timing_row(
        [CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.0]')],
        enabled=False,
        fields=fields,
    )
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")

    assert "timing" not in toml_text
