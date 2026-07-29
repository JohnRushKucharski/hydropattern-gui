from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import tomli_w
from hydropattern.parsers import ClimateCanvasPlotOptions, PlotOptions

MetricMode = Literal["portion", "percentage", "return_period"]
DumpMode = Literal["minimal", "complete"]
Characteristic = list[Any]
_CHARACTERISTIC_KEYS = ("timing", "magnitude", "duration", "rate_of_change", "frequency")
_DEFAULT_DATE_FORMAT = ""
_DEFAULT_FIRST_DAY_OF_WATER_YEAR = 1
_DEFAULT_SHEET_NAME = 0


class ConfigModelError(ValueError):
    """Raised when TOML shape cannot map to GUI config model."""


@dataclass(frozen=True)
class TimeseriesConfig:
    path: str
    date_format: str = _DEFAULT_DATE_FORMAT
    first_day_of_water_year: int = _DEFAULT_FIRST_DAY_OF_WATER_YEAR
    sheet_name: int | str = _DEFAULT_SHEET_NAME


@dataclass(frozen=True)
class ComponentConfig:
    timing: Characteristic | None = None
    magnitude: Characteristic | None = None
    duration: Characteristic | None = None
    rate_of_change: Characteristic | None = None
    frequency: Characteristic | None = None
    verbose: bool = False
    success_pattern: bool = True
    characteristic_order: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        present_keys = [key for key in _CHARACTERISTIC_KEYS if getattr(self, key) is not None]
        if not present_keys:
            raise ConfigModelError("Component must define at least one characteristic.")
        if self.characteristic_order is None:
            object.__setattr__(self, "characteristic_order", tuple(present_keys))
            return
        if set(self.characteristic_order) != set(present_keys):
            raise ConfigModelError(
                "characteristic_order must include each present characteristic exactly once."
            )
        if any(key not in _CHARACTERISTIC_KEYS for key in self.characteristic_order):
            raise ConfigModelError("characteristic_order contains unknown characteristic.")


@dataclass(frozen=True)
class MetricOptions:
    mode: MetricMode = "portion"


@dataclass(frozen=True)
class OutputOptions:
    directory: str | None = None
    overwrite: bool = True
    excel: bool = True
    metric: MetricOptions = field(default_factory=MetricOptions)
    plot: PlotOptions = field(default_factory=PlotOptions)


@dataclass(frozen=True)
class HydropatternConfig:
    timeseries: TimeseriesConfig
    components: dict[str, ComponentConfig]
    output: OutputOptions = field(default_factory=OutputOptions)

    def __post_init__(self) -> None:
        if not self.components:
            raise ConfigModelError("Config must define at least one component.")


def dumps_config_toml(config: HydropatternConfig, mode: DumpMode = "minimal") -> str:
    include_defaults = mode == "complete"
    data: dict[str, Any] = {
        "timeseries": _timeseries_to_dict(config.timeseries, include_defaults),
        "components": _components_to_dict(config.components, include_defaults),
    }
    output_data = _output_to_dict(config.output, include_defaults)
    if output_data:
        data["output"] = output_data
    return tomli_w.dumps(data)


def loads_config_toml(text: str) -> HydropatternConfig:
    return _config_from_dict(tomllib.loads(text))


def write_config_toml(
    path: str | Path, config: HydropatternConfig, mode: DumpMode = "minimal"
) -> None:
    Path(path).write_text(dumps_config_toml(config, mode), encoding="utf-8")


def read_config_toml(path: str | Path) -> HydropatternConfig:
    return loads_config_toml(Path(path).read_text(encoding="utf-8"))


def _timeseries_to_dict(config: TimeseriesConfig, include_defaults: bool) -> dict[str, Any]:
    result: dict[str, Any] = {"path": config.path}
    if include_defaults or config.date_format != _DEFAULT_DATE_FORMAT:
        result["date_format"] = config.date_format
    if include_defaults or config.first_day_of_water_year != _DEFAULT_FIRST_DAY_OF_WATER_YEAR:
        result["first_day_of_water_year"] = config.first_day_of_water_year
    if include_defaults or config.sheet_name != _DEFAULT_SHEET_NAME:
        result["sheet_name"] = config.sheet_name
    return result


def _components_to_dict(
    components: dict[str, ComponentConfig], include_defaults: bool
) -> dict[str, dict[str, Any]]:
    section: dict[str, dict[str, Any]] = {}
    for component_name, component in components.items():
        component_data: dict[str, Any] = {}
        for key in component.characteristic_order or _CHARACTERISTIC_KEYS:
            value = getattr(component, key)
            if value is not None:
                component_data[key] = value
        if include_defaults or component.verbose is not False:
            component_data["verbose"] = component.verbose
        if include_defaults or component.success_pattern is not True:
            component_data["success_pattern"] = component.success_pattern
        section[component_name] = component_data
    return section


def _output_to_dict(config: OutputOptions, include_defaults: bool) -> dict[str, Any]:
    output_data: dict[str, Any] = {}
    if config.directory is not None:
        output_data["directory"] = config.directory
    if include_defaults or config.overwrite is not True:
        output_data["overwrite"] = config.overwrite
    if include_defaults or config.excel is not True:
        output_data["excel"] = config.excel

    metric_data: dict[str, Any] = {}
    if include_defaults or config.metric.mode != "portion":
        metric_data["mode"] = config.metric.mode
    if metric_data:
        output_data["metric"] = metric_data

    climate_canvas_data: dict[str, Any] = {}
    if include_defaults or config.plot.climate_canvas.interpolate is not True:
        climate_canvas_data["interpolate"] = config.plot.climate_canvas.interpolate
    if include_defaults or config.plot.climate_canvas.show is not False:
        climate_canvas_data["show"] = config.plot.climate_canvas.show
    if config.plot.climate_canvas.title is not None:
        climate_canvas_data["title"] = config.plot.climate_canvas.title
    if include_defaults or config.plot.climate_canvas.xlabel != "Precipitation Delta (%)":
        climate_canvas_data["xlabel"] = config.plot.climate_canvas.xlabel
    if include_defaults or config.plot.climate_canvas.ylabel != "Temperature Delta (C)":
        climate_canvas_data["ylabel"] = config.plot.climate_canvas.ylabel
    if config.plot.climate_canvas.zlabel is not None:
        climate_canvas_data["zlabel"] = config.plot.climate_canvas.zlabel
    if config.plot.climate_canvas.threshold is not None:
        climate_canvas_data["threshold"] = config.plot.climate_canvas.threshold
    if include_defaults or config.plot.climate_canvas.color_map != "RdBu":
        climate_canvas_data["color_map"] = config.plot.climate_canvas.color_map
    if config.plot.climate_canvas.color_map_ticks is not None:
        climate_canvas_data["color_map_ticks"] = config.plot.climate_canvas.color_map_ticks
    if include_defaults or config.plot.climate_canvas.fillin is not False:
        climate_canvas_data["fillin"] = config.plot.climate_canvas.fillin

    plot_data: dict[str, Any] = {}
    if include_defaults or config.plot.enabled is not False:
        plot_data["enabled"] = config.plot.enabled
    if climate_canvas_data:
        plot_data["climate-canvas"] = climate_canvas_data
    if plot_data:
        output_data["plot"] = plot_data
    return output_data


def _config_from_dict(data: dict[str, Any]) -> HydropatternConfig:
    timeseries_data = _require_table(data, "timeseries")
    if "path" not in timeseries_data or not isinstance(timeseries_data["path"], str):
        raise ConfigModelError("[timeseries].path must be string.")
    timeseries = TimeseriesConfig(
        path=timeseries_data["path"],
        date_format=_optional_str_default(timeseries_data, "date_format", _DEFAULT_DATE_FORMAT),
        first_day_of_water_year=_optional_int(
            timeseries_data, "first_day_of_water_year", _DEFAULT_FIRST_DAY_OF_WATER_YEAR
        ),
        sheet_name=_optional_sheet_name(timeseries_data),
    )

    components_data = _require_table(data, "components")
    components: dict[str, ComponentConfig] = {}
    for name, component_data_raw in components_data.items():
        if not isinstance(component_data_raw, dict):
            raise ConfigModelError(f"[components.{name}] must be table.")
        allowed = set(_CHARACTERISTIC_KEYS) | {"verbose", "success_pattern"}
        unknown_keys = set(component_data_raw) - allowed
        if unknown_keys:
            raise ConfigModelError(
                f"[components.{name}] unknown key(s): {sorted(unknown_keys)}."
            )
        kwargs: dict[str, Any] = {
            key: _optional_list(component_data_raw, key) for key in _CHARACTERISTIC_KEYS
        }
        kwargs["verbose"] = _optional_bool(component_data_raw, "verbose", False)
        kwargs["success_pattern"] = _optional_bool(component_data_raw, "success_pattern", True)
        kwargs["characteristic_order"] = tuple(
            key for key in component_data_raw.keys() if key in _CHARACTERISTIC_KEYS
        )
        components[name] = ComponentConfig(**kwargs)

    output = _parse_output(data.get("output"))
    return HydropatternConfig(timeseries=timeseries, components=components, output=output)


def _parse_output(section: Any) -> OutputOptions:
    if section is None:
        return OutputOptions()
    if not isinstance(section, dict):
        raise ConfigModelError("[output] must be table.")
    allowed = {"directory", "overwrite", "excel", "metric", "plot"}
    unknown_keys = set(section) - allowed
    if unknown_keys:
        raise ConfigModelError(f"[output] unknown key(s): {sorted(unknown_keys)}.")
    metric = _parse_metric(section.get("metric"))
    plot = _parse_plot(section.get("plot"))
    return OutputOptions(
        directory=_optional_str(section, "directory", None),
        overwrite=_optional_bool(section, "overwrite", True),
        excel=_optional_bool(section, "excel", True),
        metric=metric,
        plot=plot,
    )


def _parse_metric(section: Any) -> MetricOptions:
    if section is None:
        return MetricOptions()
    if not isinstance(section, dict):
        raise ConfigModelError("[output.metric] must be table.")
    unknown_keys = set(section) - {"mode"}
    if unknown_keys:
        raise ConfigModelError(f"[output.metric] unknown key(s): {sorted(unknown_keys)}.")
    mode = section.get("mode", "portion")
    if mode not in {"portion", "percentage", "return_period"}:
        raise ConfigModelError(
            "[output.metric].mode must be one of ['percentage', 'portion', 'return_period']."
        )
    return MetricOptions(mode=mode)


def _parse_plot(section: Any) -> PlotOptions:
    if section is None:
        return PlotOptions()
    if not isinstance(section, dict):
        raise ConfigModelError("[output.plot] must be table.")
    unknown_keys = set(section) - {"enabled", "climate-canvas"}
    if unknown_keys:
        raise ConfigModelError(f"[output.plot] unknown key(s): {sorted(unknown_keys)}.")
    return PlotOptions(
        enabled=_optional_bool(section, "enabled", False),
        climate_canvas=_parse_climate_canvas(section.get("climate-canvas")),
    )


def _parse_climate_canvas(section: Any) -> ClimateCanvasPlotOptions:
    if section is None:
        return ClimateCanvasPlotOptions()
    if not isinstance(section, dict):
        raise ConfigModelError("[output.plot.climate-canvas] must be table.")
    allowed = {
        "interpolate",
        "show",
        "title",
        "xlabel",
        "ylabel",
        "zlabel",
        "threshold",
        "color_map",
        "color_map_ticks",
        "fillin",
    }
    unknown_keys = set(section) - allowed
    if unknown_keys:
        raise ConfigModelError(
            f"[output.plot.climate-canvas] unknown key(s): {sorted(unknown_keys)}."
        )
    color_map_ticks = section.get("color_map_ticks")
    if color_map_ticks is not None:
        if not isinstance(color_map_ticks, list):
            raise ConfigModelError("[output.plot.climate-canvas].color_map_ticks must be list.")
        ticks: list[float] = []
        for tick in color_map_ticks:
            if not isinstance(tick, (int, float)):
                raise ConfigModelError(
                    "[output.plot.climate-canvas].color_map_ticks entries must be numbers."
                )
            ticks.append(float(tick))
        color_map_ticks = ticks
    threshold = section.get("threshold")
    if threshold is not None and not isinstance(threshold, (int, float)):
        raise ConfigModelError("[output.plot.climate-canvas].threshold must be number.")

    return ClimateCanvasPlotOptions(
        interpolate=_optional_bool(section, "interpolate", True),
        show=_optional_bool(section, "show", False),
        title=_optional_str(section, "title", None),
        xlabel=_optional_str_default(section, "xlabel", "Precipitation Delta (%)"),
        ylabel=_optional_str_default(section, "ylabel", "Temperature Delta (C)"),
        zlabel=_optional_str(section, "zlabel", None),
        threshold=float(threshold) if threshold is not None else None,
        color_map=_optional_str_default(section, "color_map", "RdBu"),
        color_map_ticks=color_map_ticks,
        fillin=_optional_bool(section, "fillin", False),
    )


def _require_table(data: dict[str, Any], key: str) -> dict[str, Any]:
    if key not in data:
        raise ConfigModelError(f"Missing required section [{key}].")
    section = data[key]
    if not isinstance(section, dict):
        raise ConfigModelError(f"[{key}] must be table.")
    return section


def _optional_str(section: dict[str, Any], key: str, default: str | None) -> str | None:
    value = section.get(key, default)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigModelError(f"{key} must be string.")
    return value


def _optional_str_default(section: dict[str, Any], key: str, default: str) -> str:
    value = section.get(key, default)
    if not isinstance(value, str):
        raise ConfigModelError(f"{key} must be string.")
    return value


def _optional_int(section: dict[str, Any], key: str, default: int) -> int:
    value = section.get(key, default)
    if not isinstance(value, int):
        raise ConfigModelError(f"{key} must be integer.")
    return value


def _optional_sheet_name(section: dict[str, Any]) -> int | str:
    value = section.get("sheet_name", _DEFAULT_SHEET_NAME)
    if not isinstance(value, (int, str)):
        raise ConfigModelError("sheet_name must be integer or string.")
    return value


def _optional_bool(section: dict[str, Any], key: str, default: bool) -> bool:
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise ConfigModelError(f"{key} must be boolean.")
    return value


def _optional_list(section: dict[str, Any], key: str) -> list[Any] | None:
    value = section.get(key)
    if value is None:
        return None
    if not isinstance(value, list):
        raise ConfigModelError(f"{key} must be list.")
    return value
