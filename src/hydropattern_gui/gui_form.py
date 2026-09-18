"""Form-state <-> domain-config mapping and validation for the GUI.

This module owns the translation between the raw, string-based Tkinter form
state (:class:`GuiFormState`) and the validated domain model
(:class:`hydropattern_gui.config_model.HydropatternConfig`), plus the
mapping from a validated config to :class:`hydropattern_gui.runner_service.RunOptions`.
It intentionally contains no Tkinter widget code so it can be tested and
reasoned about independently of the UI shell.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Literal, cast

from hydropattern.errors import HydropatternError
from hydropattern.parsers import (
    validate_duration_metrics,
    validate_frequency_metrics,
    validate_magnitude_metrics,
    validate_rate_of_change_metrics,
    validate_timing_metrics,
)

from hydropattern_gui.config_model import (
    ClimateCanvasPlotOptions,
    ComponentConfig,
    HydropatternConfig,
    MetricMode,
    MetricOptions,
    OutputOptions,
    PlotOptions,
    TimeseriesConfig,
)
from hydropattern_gui.runner_service import RunOptions

CharacteristicKind = Literal["timing", "magnitude", "duration", "rate_of_change", "frequency"]
_CHARACTERISTIC_KINDS: tuple[CharacteristicKind, ...] = (
    "timing",
    "magnitude",
    "duration",
    "rate_of_change",
    "frequency",
)


@dataclass(frozen=True)
class CharacteristicRowState:
    kind: CharacteristicKind
    metrics_text: str


class FormValidationError(ValueError):
    def __init__(self, field_errors: dict[str, str]) -> None:
        self.field_errors = field_errors
        message = "; ".join(f"{field}: {error}" for field, error in field_errors.items())
        super().__init__(message)


@dataclass
class GuiFormState:
    timeseries_path: str = ""
    date_format: str = ""
    first_day_of_water_year: str = "1"
    sheet_name: str = "0"
    output_directory: str = ""
    excel: bool = True
    overwrite: bool = True
    metric_mode: MetricMode = "portion"
    component_name: str = "simple_component"
    component_verbose: bool = False
    component_success_pattern: bool = True
    characteristic_rows: list[CharacteristicRowState] = field(
        default_factory=lambda: [CharacteristicRowState("magnitude", '[">", 1.0]')]
    )
    plot_enabled: bool = False
    climate_interpolate: bool = True
    climate_show: bool = False
    climate_title: str = ""
    climate_xlabel: str = "Precipitation Delta (%)"
    climate_ylabel: str = "Temperature Delta (C)"
    climate_zlabel: str = ""
    climate_threshold: str = ""
    climate_color_map: str = "RdBu"
    climate_color_map_ticks: str = ""


def config_from_form_state(state: GuiFormState) -> HydropatternConfig:
    field_errors: dict[str, str] = {}
    path = state.timeseries_path.strip()
    if not path:
        field_errors["timeseries.path"] = "required"

    first_day: int | None = None
    try:
        first_day = int(state.first_day_of_water_year.strip())
    except ValueError:
        field_errors["timeseries.first_day_of_water_year"] = "must be integer"

    sheet_name_value = state.sheet_name.strip()
    try:
        sheet_name: int | str = int(sheet_name_value)
    except ValueError:
        sheet_name = sheet_name_value

    component_name = state.component_name.strip()
    if not component_name:
        field_errors["components.name"] = "required"

    if not state.characteristic_rows:
        field_errors["components.rows"] = "at least one row required"

    characteristic_kwargs: dict[str, list[object] | None] = {
        key: None for key in _CHARACTERISTIC_KINDS
    }
    characteristic_order: list[str] = []
    for index, row in enumerate(state.characteristic_rows):
        field_prefix = f"components.{component_name or '<component>'}.rows[{index}]"
        if row.kind not in _CHARACTERISTIC_KINDS:
            field_errors[f"{field_prefix}.kind"] = "unknown characteristic kind"
            continue
        if row.kind in characteristic_order:
            field_errors[f"{field_prefix}.kind"] = f"duplicate characteristic kind '{row.kind}'"
            continue
        metrics_text = row.metrics_text.strip()
        if not metrics_text:
            field_errors[f"{field_prefix}.metrics"] = "required"
            continue
        try:
            parsed = ast.literal_eval(metrics_text)
        except (ValueError, SyntaxError):
            field_errors[f"{field_prefix}.metrics"] = "must be valid Python/TOML-like list literal"
            continue
        if not isinstance(parsed, list):
            field_errors[f"{field_prefix}.metrics"] = "must parse to list"
            continue
        try:
            _validate_characteristic_metrics(row.kind, parsed)
        except HydropatternError as exc:
            field_errors[f"{field_prefix}.metrics"] = str(exc)
            continue
        characteristic_kwargs[row.kind] = parsed
        characteristic_order.append(row.kind)

    metric_mode = state.metric_mode
    if metric_mode not in ("portion", "percentage", "return_period"):
        field_errors["output.metric.mode"] = "must be portion|percentage|return_period"

    threshold: float | None = None
    if state.climate_threshold.strip():
        try:
            threshold = float(state.climate_threshold.strip())
        except ValueError:
            field_errors["output.plot.climate-canvas.threshold"] = "must be float"

    ticks: list[float] | None = None
    if state.climate_color_map_ticks.strip():
        try:
            ticks = _parse_ticks(
                state.climate_color_map_ticks.strip(),
                field_name="output.plot.climate-canvas.color_map_ticks",
            )
        except FormValidationError as exc:
            field_errors.update(exc.field_errors)

    if field_errors:
        raise FormValidationError(field_errors)

    assert first_day is not None
    return HydropatternConfig(
        timeseries=TimeseriesConfig(
            path=path,
            date_format=state.date_format.strip(),
            first_day_of_water_year=first_day,
            sheet_name=sheet_name,
        ),
        components={
            component_name: ComponentConfig(
                timing=cast(list[object] | None, characteristic_kwargs["timing"]),
                magnitude=cast(list[object] | None, characteristic_kwargs["magnitude"]),
                duration=cast(list[object] | None, characteristic_kwargs["duration"]),
                rate_of_change=cast(list[object] | None, characteristic_kwargs["rate_of_change"]),
                frequency=cast(list[object] | None, characteristic_kwargs["frequency"]),
                verbose=state.component_verbose,
                success_pattern=state.component_success_pattern,
                characteristic_order=tuple(characteristic_order),
            )
        },
        output=OutputOptions(
            directory=state.output_directory.strip() or None,
            overwrite=state.overwrite,
            excel=state.excel,
            metric=MetricOptions(mode=metric_mode),
            plot=PlotOptions(
                enabled=state.plot_enabled,
                climate_canvas=ClimateCanvasPlotOptions(
                    interpolate=state.climate_interpolate,
                    show=state.climate_show,
                    title=state.climate_title.strip() or None,
                    xlabel=state.climate_xlabel.strip() or "Precipitation Delta (%)",
                    ylabel=state.climate_ylabel.strip() or "Temperature Delta (C)",
                    zlabel=state.climate_zlabel.strip() or None,
                    threshold=threshold,
                    color_map=state.climate_color_map.strip() or "RdBu",
                    color_map_ticks=ticks,
                ),
            ),
        ),
    )


def form_state_from_config(config: HydropatternConfig) -> GuiFormState:
    component_name, component = next(iter(config.components.items()))
    characteristic_order = list(component.characteristic_order or ())
    if not characteristic_order:
        characteristic_order = [
            key for key in _CHARACTERISTIC_KINDS if getattr(component, key) is not None
        ]
    rows: list[CharacteristicRowState] = []
    for kind in characteristic_order:
        value = getattr(component, kind)
        if value is None:
            continue
        rows.append(
            CharacteristicRowState(
                kind=cast(CharacteristicKind, kind),
                metrics_text=_metrics_to_text(value),
            )
        )

    climate = config.output.plot.climate_canvas
    ticks = ",".join(str(item) for item in climate.color_map_ticks or [])
    threshold = "" if climate.threshold is None else str(climate.threshold)
    return GuiFormState(
        timeseries_path=config.timeseries.path,
        date_format=config.timeseries.date_format,
        first_day_of_water_year=str(config.timeseries.first_day_of_water_year),
        sheet_name=str(config.timeseries.sheet_name),
        output_directory=config.output.directory or "",
        excel=config.output.excel,
        overwrite=config.output.overwrite,
        metric_mode=config.output.metric.mode,
        component_name=component_name,
        component_verbose=component.verbose,
        component_success_pattern=component.success_pattern,
        characteristic_rows=rows,
        plot_enabled=config.output.plot.enabled,
        climate_interpolate=climate.interpolate,
        climate_show=climate.show,
        climate_title=climate.title or "",
        climate_xlabel=climate.xlabel,
        climate_ylabel=climate.ylabel,
        climate_zlabel=climate.zlabel or "",
        climate_threshold=threshold,
        climate_color_map=climate.color_map,
        climate_color_map_ticks=ticks,
    )


def run_options_from_config(config: HydropatternConfig) -> RunOptions:
    """Build RunOptions from the already-validated config, so a run always
    uses the exact same values written to the TOML file (no re-parsing of
    raw form strings, which could silently diverge)."""
    output = config.output
    climate = output.plot.climate_canvas
    return RunOptions(
        output_directory=output.directory,
        plot=output.plot.enabled,
        excel=output.excel,
        overwrite=output.overwrite,
        interp=climate.interpolate,
        show=climate.show,
        threshold=climate.threshold,
        color_map=climate.color_map,
        color_map_ticks=climate.color_map_ticks,
        run_toml_options=False,
    )


def _parse_ticks(raw: str, field_name: str) -> list[float]:
    values: list[float] = []
    for part in [chunk.strip() for chunk in raw.split(",") if chunk.strip()]:
        try:
            values.append(float(part))
        except ValueError as exc:
            raise FormValidationError({field_name: "must be comma-separated floats"}) from exc
    return values


def _metrics_to_text(metrics: list[object]) -> str:
    rendered_parts: list[str] = []
    for item in metrics:
        if isinstance(item, str):
            rendered_parts.append(f'"{item}"')
        else:
            rendered_parts.append(str(item))
    return f"[{', '.join(rendered_parts)}]"


def _validate_characteristic_metrics(kind: CharacteristicKind, metrics: list[object]) -> None:
    if kind == "timing":
        validate_timing_metrics(metrics)
    elif kind == "magnitude":
        validate_magnitude_metrics(metrics)
    elif kind == "duration":
        validate_duration_metrics(metrics)
    elif kind == "rate_of_change":
        validate_rate_of_change_metrics(metrics)
    elif kind == "frequency":
        validate_frequency_metrics(metrics)
