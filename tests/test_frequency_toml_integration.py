"""Bullet 7: integration round-trip for the Frequency card path.

Mirrors test_rate_of_change_toml_integration.py, plus covers the nested
COUNT/BETWEEN/PROBABILITY forms unique to Frequency.
"""

import tomllib

from hydropattern_gui.gui_form import (
    CharacteristicRowState,
    FrequencyFields,
    FrequencyPatternFields,
    GuiFormState,
    config_from_form_state,
    sync_frequency_row,
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


_BLANK_PATTERN: dict[str, object] = dict(
    mode="count",
    operator=">",
    count_n=None,
    probability=None,
    between_min=None,
    between_max=None,
    out_of_n=None,
    count_by_event=True,
)


def _pattern(**overrides: object) -> FrequencyPatternFields:
    base = dict(_BLANK_PATTERN)
    base.update(overrides)
    return FrequencyPatternFields(**base)  # type: ignore[arg-type]


def test_frequency_count_round_trips_through_toml() -> None:
    fields = FrequencyFields(
        nested_enabled=False,
        base=_pattern(mode="count", operator=">=", count_n=3, out_of_n=10),
        nested=_pattern(),
    )
    rows = sync_frequency_row([], enabled=True, fields=fields)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")
    data = tomllib.loads(toml_text)

    assert data["components"]["simple_component"]["frequency"] == [">=", 3, 10, True]


def test_frequency_between_round_trips_through_toml() -> None:
    fields = FrequencyFields(
        nested_enabled=False,
        base=_pattern(mode="between", operator=None, between_min=1, between_max=5, out_of_n=12),
        nested=_pattern(),
    )
    rows = sync_frequency_row([], enabled=True, fields=fields)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")
    data = tomllib.loads(toml_text)

    assert data["components"]["simple_component"]["frequency"] == [1, 5, 12, True]


def test_frequency_nested_between_in_count_round_trips_through_toml() -> None:
    fields = FrequencyFields(
        nested_enabled=True,
        base=_pattern(mode="count", operator=">=", count_n=3, out_of_n=10),
        nested=_pattern(mode="between", operator=None, between_min=1, between_max=5, out_of_n=12),
    )
    rows = sync_frequency_row([], enabled=True, fields=fields)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")
    data = tomllib.loads(toml_text)

    assert data["components"]["simple_component"]["frequency"] == [
        [">=", 3, 10, True],
        [1, 5, 12, True],
    ]


def test_frequency_nested_probability_base_round_trips_through_toml() -> None:
    fields = FrequencyFields(
        nested_enabled=True,
        base=_pattern(mode="probability", operator=">", probability=0.5),
        nested=_pattern(mode="count", operator=">=", count_n=2, out_of_n=6),
    )
    rows = sync_frequency_row([], enabled=True, fields=fields)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")
    data = tomllib.loads(toml_text)

    assert data["components"]["simple_component"]["frequency"] == [
        [">", 0.5, True],
        [">=", 2, 6, True],
    ]


def test_frequency_placed_between_other_characteristics_preserves_toml_order() -> None:
    fields = FrequencyFields(
        nested_enabled=False,
        base=_pattern(mode="count", operator=">=", count_n=3, out_of_n=10),
        nested=_pattern(),
    )
    rows = [
        CharacteristicRowState(kind="timing", metrics_text="[1, 366]"),
        CharacteristicRowState(kind="duration", metrics_text='[">", 7]'),
    ]
    rows = sync_frequency_row(rows, enabled=True, fields=fields, insert_at=1)
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")

    timing_pos = toml_text.find("timing =")
    freq_pos = toml_text.find("frequency =")
    duration_pos = toml_text.find("duration =")
    assert timing_pos < freq_pos < duration_pos


def test_frequency_disabled_is_absent_from_toml() -> None:
    fields = FrequencyFields(
        nested_enabled=False,
        base=_pattern(),
        nested=_pattern(),
    )
    rows = sync_frequency_row(
        [CharacteristicRowState(kind="timing", metrics_text="[1, 366]")],
        enabled=False,
        fields=fields,
    )
    state = _base_state(rows)

    config = config_from_form_state(state)
    toml_text = dumps_config_toml(config, mode="minimal")

    assert "frequency" not in toml_text
