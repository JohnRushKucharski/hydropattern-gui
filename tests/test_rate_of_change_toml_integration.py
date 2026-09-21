"""Bullet 6: integration round-trip for the Rate of Change card path.

Mirrors test_duration_toml_integration.py / test_timing_toml_integration.py,
plus covers the cascading optional params (ma_periods -> look_back -> min).
"""

import tomllib

from hydropattern_gui.gui_form import (
    CharacteristicRowState,
    GuiFormState,
    RateOfChangeFields,
    config_from_form_state,
    sync_rate_of_change_row,
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


def test_rate_of_change_simple_round_trips_through_toml() -> None:
    rows = sync_rate_of_change_row([], enabled=True, fields=_fields())
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")
    data = tomllib.loads(toml_text)

    assert data["components"]["simple_component"]["rate_of_change"] == [">", 1.5]


def test_rate_of_change_between_round_trips_through_toml() -> None:
    fields = _fields(mode="between", operator=None, threshold=None, minimum=1.0, maximum=5.0)
    rows = sync_rate_of_change_row([], enabled=True, fields=fields)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")
    data = tomllib.loads(toml_text)

    assert data["components"]["simple_component"]["rate_of_change"] == [1.0, 5.0]


def test_rate_of_change_full_cascade_round_trips_through_toml() -> None:
    fields = _fields(
        ma_enabled=True, ma_periods=3,
        look_back_enabled=True, look_back=2,
        min_enabled=True, min_value=0.0,
    )
    rows = sync_rate_of_change_row([], enabled=True, fields=fields)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")
    data = tomllib.loads(toml_text)

    assert data["components"]["simple_component"]["rate_of_change"] == [">", 1.5, 3, 2, 0.0]


def test_rate_of_change_placed_between_other_characteristics_preserves_toml_order() -> None:
    rows = [
        CharacteristicRowState(kind="timing", metrics_text="[1, 366]"),
        CharacteristicRowState(kind="duration", metrics_text='[">", 7]'),
    ]
    rows = sync_rate_of_change_row(rows, enabled=True, fields=_fields(), insert_at=1)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")

    timing_pos = toml_text.find("timing =")
    roc_pos = toml_text.find("rate_of_change =")
    duration_pos = toml_text.find("duration =")
    assert timing_pos < roc_pos < duration_pos


def test_rate_of_change_disabled_is_absent_from_toml() -> None:
    fields = _fields(mode="simple", operator=None, threshold=None)
    rows = sync_rate_of_change_row(
        [CharacteristicRowState(kind="timing", metrics_text="[1, 366]")],
        enabled=False,
        fields=fields,
    )
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")

    assert "rate_of_change" not in toml_text
