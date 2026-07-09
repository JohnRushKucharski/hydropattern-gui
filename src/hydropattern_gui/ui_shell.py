from __future__ import annotations

import ast
import os
import tempfile
import threading
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty, Queue
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Literal, Protocol, cast

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
    DumpMode,
    HydropatternConfig,
    MetricMode,
    MetricOptions,
    OutputOptions,
    PlotOptions,
    TimeseriesConfig,
    dumps_config_toml,
    read_config_toml,
    write_config_toml,
)
from hydropattern_gui.release_info import build_about_text
from hydropattern_gui.runner_service import (
    InProcessHydropatternRunner,
    RunOptions,
    RunResult,
)

CharacteristicKind = Literal["timing", "magnitude", "duration", "rate_of_change", "frequency"]
_CHARACTERISTIC_KINDS: tuple[CharacteristicKind, ...] = (
    "timing",
    "magnitude",
    "duration",
    "rate_of_change",
    "frequency",
)
LogCallback = Callable[[str, str], None]


class RunnerBackend(Protocol):
    def run(
        self,
        config_path: str | Path,
        options: RunOptions | None = None,
        on_output: LogCallback | None = None,
        cwd: str | Path | None = None,
    ) -> RunResult: ...


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


class GuiController:
    def __init__(self, runner: RunnerBackend) -> None:
        self._runner = runner

    def load_form_state(self, path: str | Path) -> GuiFormState:
        config = read_config_toml(path)
        return form_state_from_config(config)

    def preview_toml(self, state: GuiFormState, mode: DumpMode = "minimal") -> str:
        config = config_from_form_state(state)
        return dumps_config_toml(config, mode=mode)

    def save(self, path: str | Path, state: GuiFormState, mode: DumpMode = "minimal") -> None:
        config = config_from_form_state(state)
        write_config_toml(path, config, mode=mode)

    def run(
        self,
        state: GuiFormState,
        on_log: LogCallback | None = None,
        working_dir: str | Path | None = None,
    ) -> RunResult:
        config = config_from_form_state(state)
        run_cwd = Path(working_dir).resolve() if working_dir is not None else Path.cwd()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".toml", delete=False, dir=run_cwd, encoding="utf-8"
        ) as temp_file:
            temp_path = Path(temp_file.name)
        try:
            write_config_toml(temp_path, config, mode="minimal")
            run_options = RunOptions(
                output_directory=state.output_directory.strip() or None,
                plot=state.plot_enabled,
                excel=state.excel,
                overwrite=state.overwrite,
                interp=state.climate_interpolate,
                show=state.climate_show,
                threshold=float(state.climate_threshold.strip())
                if state.climate_threshold.strip()
                else None,
                color_map=state.climate_color_map.strip() or None,
                color_map_ticks=_parse_ticks(
                    state.climate_color_map_ticks.strip(),
                    field_name="output.plot.climate-canvas.color_map_ticks",
                )
                if state.climate_color_map_ticks.strip()
                else None,
                run_toml_options=False,
            )
            return self._runner.run(
                temp_path.name,
                options=run_options,
                on_output=on_log,
                cwd=run_cwd,
            )
        finally:
            if temp_path.exists():
                temp_path.unlink()


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


class HydropatternGuiApp:
    def __init__(self, root: tk.Tk, controller: GuiController) -> None:
        self._root = root
        self._controller = controller
        self._event_queue: Queue[tuple[str, object]] = Queue()
        self._status_var = tk.StringVar(value="Ready")
        self._path_var = tk.StringVar()
        self._date_format_var = tk.StringVar()
        self._first_day_var = tk.StringVar(value="1")
        self._sheet_name_var = tk.StringVar(value="0")
        self._output_dir_var = tk.StringVar()
        self._toml_path_var = tk.StringVar()
        self._excel_var = tk.BooleanVar(value=True)
        self._overwrite_var = tk.BooleanVar(value=True)
        self._metric_var = tk.StringVar(value="portion")
        self._component_name_var = tk.StringVar(value="simple_component")
        self._component_verbose_var = tk.BooleanVar(value=False)
        self._component_success_var = tk.BooleanVar(value=True)
        self._plot_enabled_var = tk.BooleanVar(value=False)
        self._climate_interpolate_var = tk.BooleanVar(value=True)
        self._climate_show_var = tk.BooleanVar(value=False)
        self._climate_title_var = tk.StringVar()
        self._climate_xlabel_var = tk.StringVar(value="Precipitation Delta (%)")
        self._climate_ylabel_var = tk.StringVar(value="Temperature Delta (C)")
        self._climate_zlabel_var = tk.StringVar()
        self._climate_threshold_var = tk.StringVar()
        self._climate_color_map_var = tk.StringVar(value="RdBu")
        self._climate_color_map_ticks_var = tk.StringVar()
        self._characteristic_vars: list[tuple[tk.StringVar, tk.StringVar]] = []
        self._characteristic_widgets: list[tuple[ttk.Combobox, ttk.Entry]] = []
        self._build_ui()
        self._path_var.trace_add("write", self._on_path_or_output_dir_changed)
        self._output_dir_var.trace_add("write", self._on_path_or_output_dir_changed)

    def _build_ui(self) -> None:
        self._root.title("hydropattern-gui")
        self._root.geometry("1100x850")
        outer = ttk.Frame(self._root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        container = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=container, anchor="nw")

        def _on_container_configure(_: tk.Event[tk.Misc]) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event: tk.Event[tk.Misc]) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        def _on_mousewheel(event: tk.Event[tk.Misc]) -> str:
            delta = int(getattr(event, "delta", 0))
            units = mousewheel_scroll_units(delta)
            if units:
                canvas.yview_scroll(units, "units")
            return "break"

        container.bind("<Configure>", _on_container_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        ts_frame = ttk.LabelFrame(container, text="Timeseries", padding=8)
        ts_frame.pack(fill=tk.X)
        _row_labeled_entry(ts_frame, 0, "Path", self._path_var, width=80)
        ttk.Button(ts_frame, text="Browse...", command=self._on_browse_timeseries).grid(
            row=0, column=2, sticky=tk.W, padx=4, pady=4
        )
        _row_labeled_entry(ts_frame, 1, "Date format (optional)", self._date_format_var, width=20)
        _row_labeled_entry(ts_frame, 2, "First day of WY", self._first_day_var, width=8)
        _row_labeled_entry(ts_frame, 3, "Sheet", self._sheet_name_var, width=12)

        component_frame = ttk.LabelFrame(container, text="Component editor", padding=8)
        component_frame.pack(fill=tk.X, pady=(8, 0))
        _row_labeled_entry(component_frame, 0, "Component", self._component_name_var, width=30)
        ttk.Checkbutton(
            component_frame, text="Verbose", variable=self._component_verbose_var
        ).grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        ttk.Checkbutton(
            component_frame, text="Success pattern", variable=self._component_success_var
        ).grid(row=1, column=1, sticky=tk.W, padx=4, pady=4)
        ttk.Label(component_frame, text="Characteristic rows (top->bottom = order)").grid(
            row=2, column=0, columnspan=3, sticky=tk.W, padx=4, pady=4
        )
        for index in range(5):
            kind_var = tk.StringVar(value=_CHARACTERISTIC_KINDS[index])
            metrics_var = tk.StringVar()
            self._characteristic_vars.append((kind_var, metrics_var))
            ttk.Label(component_frame, text=f"{index+1}.").grid(
                row=3 + index, column=0, sticky=tk.W, padx=4, pady=2
            )
            kind_box = ttk.Combobox(
                component_frame,
                textvariable=kind_var,
                values=_CHARACTERISTIC_KINDS,
                state="readonly",
                width=16,
            )
            kind_box.grid(row=3 + index, column=1, sticky=tk.W, padx=4, pady=2)
            metrics_entry = ttk.Entry(component_frame, textvariable=metrics_var, width=70)
            metrics_entry.grid(
                row=3 + index, column=2, sticky=tk.W, padx=4, pady=2
            )
            self._characteristic_widgets.append((kind_box, metrics_entry))
            metrics_var.trace_add("write", self._on_characteristic_metrics_changed)

        output_frame = ttk.LabelFrame(container, text="Output / Metric", padding=8)
        output_frame.pack(fill=tk.X, pady=(8, 0))
        _row_labeled_entry(output_frame, 0, "Output dir", self._output_dir_var, width=80)
        ttk.Button(output_frame, text="Browse...", command=self._on_browse_output_dir).grid(
            row=0, column=2, sticky=tk.W, padx=4, pady=4
        )
        ttk.Checkbutton(output_frame, text="Excel", variable=self._excel_var).grid(
            row=1, column=0, sticky=tk.W, padx=4, pady=4
        )
        ttk.Checkbutton(output_frame, text="Overwrite", variable=self._overwrite_var).grid(
            row=1, column=1, sticky=tk.W, padx=4, pady=4
        )
        ttk.Label(output_frame, text="Metric mode").grid(
            row=2, column=0, sticky=tk.W, padx=4, pady=4
        )
        ttk.Combobox(
            output_frame,
            textvariable=self._metric_var,
            values=("portion", "percentage", "return_period"),
            state="readonly",
            width=20,
        ).grid(row=2, column=1, sticky=tk.W, padx=4, pady=4)

        climate_frame = ttk.LabelFrame(container, text="Output climate-canvas", padding=8)
        climate_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Checkbutton(climate_frame, text="Plot enabled", variable=self._plot_enabled_var).grid(
            row=0, column=0, sticky=tk.W, padx=4, pady=4
        )
        ttk.Checkbutton(
            climate_frame, text="Interpolate", variable=self._climate_interpolate_var
        ).grid(row=0, column=1, sticky=tk.W, padx=4, pady=4)
        ttk.Checkbutton(climate_frame, text="Show", variable=self._climate_show_var).grid(
            row=0, column=2, sticky=tk.W, padx=4, pady=4
        )
        _row_labeled_entry(climate_frame, 1, "Title (optional)", self._climate_title_var, width=45)
        _row_labeled_entry(climate_frame, 2, "X label", self._climate_xlabel_var, width=45)
        _row_labeled_entry(climate_frame, 3, "Y label", self._climate_ylabel_var, width=45)
        _row_labeled_entry(
            climate_frame, 4, "Z label (optional)", self._climate_zlabel_var, width=45
        )
        _row_labeled_entry(
            climate_frame, 5, "Threshold (optional)", self._climate_threshold_var, width=12
        )
        _row_labeled_entry(climate_frame, 6, "Color map", self._climate_color_map_var, width=20)
        _row_labeled_entry(
            climate_frame,
            7,
            "Color map ticks (comma-separated, optional)",
            self._climate_color_map_ticks_var,
            width=45,
        )

        button_row_top = ttk.Frame(container)
        button_row_top.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(
            button_row_top, text="Preview TOML", command=self._on_preview
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_row_top, text="Open existing TOML", command=self._on_open).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(button_row_top, text="About", command=self._on_about).pack(side=tk.LEFT, padx=4)

        self._preview_text = tk.Text(container, height=12, wrap=tk.NONE)
        self._preview_text.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        save_row = ttk.Frame(container)
        save_row.pack(fill=tk.X, pady=(8, 0))
        _row_labeled_entry(save_row, 0, "TOML file path", self._toml_path_var, width=90)
        ttk.Button(save_row, text="Save TOML", command=self._on_save).grid(
            row=0, column=2, sticky=tk.W, padx=4, pady=4
        )

        run_row = ttk.Frame(container)
        run_row.pack(fill=tk.X, pady=(8, 0))
        self._run_button = ttk.Button(run_row, text="Run", command=self._on_run)
        self._run_button.pack(side=tk.LEFT, padx=4)
        self._run_progress = ttk.Progressbar(run_row, mode="indeterminate", length=220)
        ttk.Label(run_row, textvariable=self._status_var).pack(side=tk.RIGHT, padx=4)

        self._log_text = tk.Text(container, height=8, wrap=tk.NONE)
        self._log_text.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self._set_log_placeholder()
        self._update_characteristic_row_states()

    def _collect_state(self) -> GuiFormState:
        rows: list[CharacteristicRowState] = []
        for kind_var, metrics_var in self._characteristic_vars:
            metrics_text = metrics_var.get().strip()
            if not metrics_text:
                continue
            rows.append(
                CharacteristicRowState(
                    kind=cast(CharacteristicKind, kind_var.get()),
                    metrics_text=metrics_text,
                )
            )
        return GuiFormState(
            timeseries_path=self._path_var.get(),
            date_format=self._date_format_var.get(),
            first_day_of_water_year=self._first_day_var.get(),
            sheet_name=self._sheet_name_var.get(),
            output_directory=self._output_dir_var.get(),
            excel=self._excel_var.get(),
            overwrite=self._overwrite_var.get(),
            metric_mode=self._parse_metric_mode(self._metric_var.get()),
            component_name=self._component_name_var.get(),
            component_verbose=self._component_verbose_var.get(),
            component_success_pattern=self._component_success_var.get(),
            characteristic_rows=rows,
            plot_enabled=self._plot_enabled_var.get(),
            climate_interpolate=self._climate_interpolate_var.get(),
            climate_show=self._climate_show_var.get(),
            climate_title=self._climate_title_var.get(),
            climate_xlabel=self._climate_xlabel_var.get(),
            climate_ylabel=self._climate_ylabel_var.get(),
            climate_zlabel=self._climate_zlabel_var.get(),
            climate_threshold=self._climate_threshold_var.get(),
            climate_color_map=self._climate_color_map_var.get(),
            climate_color_map_ticks=self._climate_color_map_ticks_var.get(),
        )

    def _apply_state(self, state: GuiFormState) -> None:
        self._path_var.set(state.timeseries_path)
        self._date_format_var.set(state.date_format)
        self._first_day_var.set(state.first_day_of_water_year)
        self._sheet_name_var.set(state.sheet_name)
        self._output_dir_var.set(state.output_directory)
        self._excel_var.set(state.excel)
        self._overwrite_var.set(state.overwrite)
        self._metric_var.set(state.metric_mode)
        self._component_name_var.set(state.component_name)
        self._component_verbose_var.set(state.component_verbose)
        self._component_success_var.set(state.component_success_pattern)
        self._plot_enabled_var.set(state.plot_enabled)
        self._climate_interpolate_var.set(state.climate_interpolate)
        self._climate_show_var.set(state.climate_show)
        self._climate_title_var.set(state.climate_title)
        self._climate_xlabel_var.set(state.climate_xlabel)
        self._climate_ylabel_var.set(state.climate_ylabel)
        self._climate_zlabel_var.set(state.climate_zlabel)
        self._climate_threshold_var.set(state.climate_threshold)
        self._climate_color_map_var.set(state.climate_color_map)
        self._climate_color_map_ticks_var.set(state.climate_color_map_ticks)
        for index, (kind_var, metrics_var) in enumerate(self._characteristic_vars):
            if index < len(state.characteristic_rows):
                row = state.characteristic_rows[index]
                kind_var.set(row.kind)
                metrics_var.set(row.metrics_text)
            else:
                kind_var.set(_CHARACTERISTIC_KINDS[min(index, len(_CHARACTERISTIC_KINDS) - 1)])
                metrics_var.set("")
        self._sync_toml_path_default()
        self._update_characteristic_row_states()

    def _set_preview(self, text: str) -> None:
        self._preview_text.delete("1.0", tk.END)
        self._preview_text.insert("1.0", text)

    def _append_log(self, text: str) -> None:
        self._log_text.insert(tk.END, text)
        self._log_text.see(tk.END)

    def _set_log_placeholder(self) -> None:
        self._log_text.delete("1.0", tk.END)
        self._append_log(build_log_placeholder())

    def _show_run_progress(self) -> None:
        self._run_progress.pack(side=tk.LEFT, padx=8)
        self._run_progress.start(10)

    def _hide_run_progress(self) -> None:
        self._run_progress.stop()
        self._run_progress.pack_forget()

    def _on_open(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("TOML", "*.toml"), ("All files", "*.*")])
        if not path:
            return
        state = self._controller.load_form_state(path)
        self._apply_state(state)
        self._set_preview(self._controller.preview_toml(state))
        self._status_var.set(f"Loaded: {path}")

    def _on_browse_timeseries(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[
                ("Timeseries files", "*.csv *.xlsx *.xls"),
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx *.xls"),
                ("All files", "*.*"),
            ]
        )
        if not path:
            return
        self._path_var.set(normalize_path_for_display(path))
        self._status_var.set(f"Timeseries selected: {path}")

    def _on_browse_output_dir(self) -> None:
        path = filedialog.askdirectory()
        if not path:
            return
        self._output_dir_var.set(normalize_path_for_display(path))
        self._status_var.set(f"Output directory selected: {path}")

    def _on_save(self) -> None:
        current = self._toml_path_var.get().strip()
        initial_dir = str(Path(current).parent) if current else ""
        initial_file = Path(current).name if current else ""
        path = filedialog.asksaveasfilename(
            defaultextension=".toml",
            filetypes=[("TOML", "*.toml"), ("All files", "*.*")],
            initialdir=initial_dir,
            initialfile=initial_file,
        )
        if not path:
            return
        self._toml_path_var.set(normalize_path_for_display(path))
        state = self._collect_state()
        try:
            self._controller.save(path, state, mode="minimal")
        except FormValidationError as exc:
            self._status_var.set(f"Validation error: {exc}")
            return
        self._status_var.set(f"Saved: {path}")

    def _on_preview(self) -> None:
        state = self._collect_state()
        try:
            preview = self._controller.preview_toml(state, mode="minimal")
        except FormValidationError as exc:
            self._status_var.set(f"Validation error: {exc}")
            return
        self._set_preview(preview)
        self._status_var.set("Preview updated")

    def _on_run(self) -> None:
        state = self._collect_state()
        self._run_button.config(state=tk.DISABLED)
        self._status_var.set("Running...")
        self._set_log_placeholder()
        self._append_log("Run started. Waiting for hydropattern output...\n")
        self._show_run_progress()
        worker = threading.Thread(target=self._run_worker, args=(state,), daemon=True)
        worker.start()
        self._root.after(100, self._drain_events)

    def _on_about(self) -> None:
        messagebox.showinfo("About hydropattern-gui", build_about_text())

    def _on_characteristic_metrics_changed(self, *_: object) -> None:
        self._update_characteristic_row_states()

    def _on_path_or_output_dir_changed(self, *_: object) -> None:
        self._sync_toml_path_default()

    def _sync_toml_path_default(self) -> None:
        suggested = suggest_toml_path(self._output_dir_var.get(), self._path_var.get())
        self._toml_path_var.set(suggested)

    def _update_characteristic_row_states(self) -> None:
        first_text = self._characteristic_vars[0][1].get().strip()
        metrics_by_row = [metrics.get().strip() for _, metrics in self._characteristic_vars]
        for index, ((kind_widget, metrics_widget), (_kind_var, _metrics_var)) in enumerate(
            zip(self._characteristic_widgets, self._characteristic_vars)
        ):
            enabled = should_enable_characteristic_row(index, metrics_by_row)
            if enabled:
                kind_widget.configure(state="readonly")
                metrics_widget.configure(state="normal")
            else:
                kind_widget.configure(state="disabled")
                metrics_widget.configure(state="disabled")
        if not first_text:
            for index in range(1, len(self._characteristic_vars)):
                _kind_var, metrics_var = self._characteristic_vars[index]
                metrics_var.set("")

    def _run_worker(self, state: GuiFormState) -> None:
        def on_log(channel: str, line: str) -> None:
            self._event_queue.put(("log", f"[{channel}] {line}"))

        try:
            result = self._controller.run(state, on_log=on_log)
            self._event_queue.put(("done", result))
        except FormValidationError as exc:
            self._event_queue.put(("error", f"Validation error: {exc}"))
        except Exception as exc:  # noqa: BLE001
            self._event_queue.put(("error", str(exc)))

    def _drain_events(self) -> None:
        saw_terminal_event = False
        while True:
            try:
                event_type, payload = self._event_queue.get_nowait()
            except Empty:
                break
            if event_type == "log":
                self._append_log(str(payload))
            elif event_type == "done":
                result = payload
                assert isinstance(result, RunResult)
                self._status_var.set(f"Run done (exit={result.exit_code})")
                self._run_button.config(state=tk.NORMAL)
                self._hide_run_progress()
                saw_terminal_event = True
            elif event_type == "error":
                self._status_var.set(f"Run error: {payload}")
                self._run_button.config(state=tk.NORMAL)
                self._hide_run_progress()
                saw_terminal_event = True
        if not saw_terminal_event:
            self._root.after(100, self._drain_events)

    def _parse_metric_mode(self, raw: str) -> MetricMode:
        if raw not in ("portion", "percentage", "return_period"):
            raise ValueError(f"Unsupported metric mode: {raw}")
        return cast(MetricMode, raw)


def launch_app() -> None:
    root = tk.Tk()
    app = HydropatternGuiApp(root, GuiController(InProcessHydropatternRunner()))
    _ = app
    root.mainloop()


def run_main() -> None:
    if os.getenv("HYDROPATTERN_GUI_HEADLESS") == "1":
        print("hydropattern-gui headless mode")
        return
    launch_app()


def normalize_path_for_display(path: str) -> str:
    return path.replace("/", "\\")


def suggest_toml_path(output_dir: str, timeseries_path: str) -> str:
    output_dir_clean = output_dir.strip()
    if not output_dir_clean:
        return ""
    timeseries_stem = Path(timeseries_path.strip()).stem if timeseries_path.strip() else "config"
    filename = f"{timeseries_stem}.toml"
    return normalize_path_for_display(str(Path(output_dir_clean) / filename))


def should_enable_characteristic_row(index: int, metrics_by_row: list[str]) -> bool:
    if index == 0:
        return True
    return bool(metrics_by_row and metrics_by_row[0].strip())


def build_log_placeholder() -> str:
    return (
        "Application logs appear here.\n"
        "When you click Run, output lines stream below with [stdout]/[stderr] tags.\n\n"
    )


def mousewheel_scroll_units(delta: int) -> int:
    if delta == 0:
        return 0
    steps = int(delta / 120)
    if steps == 0:
        steps = 1 if delta > 0 else -1
    return -steps


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


def _row_labeled_entry(
    frame: ttk.LabelFrame | ttk.Frame,
    row: int,
    label: str,
    variable: tk.StringVar,
    width: int = 30,
) -> None:
    ttk.Label(frame, text=label).grid(row=row, column=0, sticky=tk.W, padx=4, pady=4)
    ttk.Entry(frame, textvariable=variable, width=width).grid(
        row=row, column=1, sticky=tk.W, padx=4, pady=4
    )
