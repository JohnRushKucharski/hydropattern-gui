from __future__ import annotations

import os
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from queue import Empty, Queue
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Protocol, cast

from hydropattern_gui.config_model import (
    DumpMode,
    MetricMode,
    dumps_config_toml,
    read_config_toml,
    write_config_toml,
)
from hydropattern_gui.gui_form import (
    _CHARACTERISTIC_KINDS,
    CharacteristicKind,
    CharacteristicRowState,
    DurationFields,
    DurationMode,
    FormValidationError,
    FrequencyFields,
    FrequencyPatternFields,
    FrequencyPatternMode,
    GuiFormState,
    MagnitudeFields,
    MagnitudeMode,
    RateOfChangeFields,
    RateOfChangeMode,
    TimingFields,
    config_from_form_state,
    duration_fields_to_metrics,
    extract_duration_state,
    extract_frequency_state,
    extract_magnitude_state,
    extract_rate_of_change_state,
    extract_timing_state,
    form_state_from_config,
    frequency_fields_to_metrics,
    magnitude_fields_to_metrics,
    rate_of_change_fields_to_metrics,
    run_options_from_config,
    timing_fields_to_metrics,
)
from hydropattern_gui.release_info import build_about_text
from hydropattern_gui.runner_service import (
    InProcessHydropatternRunner,
    LogCallback,
    LogChannel,
    RunOptions,
    RunResult,
)


class RunnerBackend(Protocol):
    def run(
        self,
        config_path: str | Path,
        options: RunOptions | None = None,
        on_output: LogCallback | None = None,
        cwd: str | Path | None = None,
    ) -> RunResult: ...


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
            run_options = run_options_from_config(config)
            return self._runner.run(
                temp_path.name,
                options=run_options,
                on_output=on_log,
                cwd=run_cwd,
            )
        finally:
            if temp_path.exists():
                temp_path.unlink()


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
        self._data_units_var = tk.StringVar()
        self._magnitude_enabled_var = tk.BooleanVar(value=False)
        self._magnitude_mode_var = tk.StringVar(value="simple")
        self._magnitude_operator_var = tk.StringVar(value=">")
        self._magnitude_threshold_var = tk.StringVar()
        self._magnitude_min_var = tk.StringVar()
        self._magnitude_max_var = tk.StringVar()
        self._magnitude_ma_enabled_var = tk.BooleanVar(value=False)
        self._magnitude_ma_periods_var = tk.StringVar()
        self._duration_enabled_var = tk.BooleanVar(value=False)
        self._duration_mode_var = tk.StringVar(value="simple")
        self._duration_operator_var = tk.StringVar(value=">")
        self._duration_steps_var = tk.StringVar()
        self._duration_min_var = tk.StringVar()
        self._duration_max_var = tk.StringVar()
        self._timing_enabled_var = tk.BooleanVar(value=False)
        self._timing_first_day_var = tk.StringVar()
        self._timing_last_day_var = tk.StringVar()
        self._roc_enabled_var = tk.BooleanVar(value=False)
        self._roc_mode_var = tk.StringVar(value="simple")
        self._roc_operator_var = tk.StringVar(value=">")
        self._roc_threshold_var = tk.StringVar()
        self._roc_min_var = tk.StringVar()
        self._roc_max_var = tk.StringVar()
        self._roc_ma_enabled_var = tk.BooleanVar(value=False)
        self._roc_ma_periods_var = tk.StringVar()
        self._roc_look_back_enabled_var = tk.BooleanVar(value=False)
        self._roc_look_back_var = tk.StringVar()
        self._roc_min_enabled_var = tk.BooleanVar(value=False)
        self._roc_min_value_var = tk.StringVar()
        self._freq_enabled_var = tk.BooleanVar(value=False)
        self._freq_nested_enabled_var = tk.BooleanVar(value=False)
        # One var-set per pattern ("base"/"nested") rather than ~8 separately
        # named attributes each (mirrors the Rate of Change cascade fields,
        # but Frequency needs 2 independent pattern editors: the always-
        # present base pattern, and an optional nested pattern).
        self._freq_vars: dict[str, dict[str, tk.Variable]] = {
            prefix: {
                "mode": tk.StringVar(value="count"),
                "operator": tk.StringVar(value=">"),
                "count_n": tk.StringVar(),
                "probability": tk.StringVar(),
                "between_min": tk.StringVar(),
                "between_max": tk.StringVar(),
                "out_of_n": tk.StringVar(),
                "count_by_event": tk.BooleanVar(value=True),
            }
            for prefix in ("base", "nested")
        }
        self._characteristic_vars: list[tuple[tk.StringVar, tk.StringVar]] = []
        self._characteristic_widgets: list[tuple[ttk.Combobox, ttk.Entry]] = []
        self._build_ui()
        # Single source of truth for characteristic row order: a permutation
        # of the 5 typed-card kind names plus one "generic:{i}" id per
        # generic freeform slot. Up/down buttons swap adjacent *active*
        # entries directly in this list -- this replaced a per-card integer
        # offset design where each card computed its own insertion point
        # independently; with >=2 typed cards enabled, cards processed
        # earlier in a fixed sequence could never end up positioned after
        # ones processed later, so their own offset had no visible effect.
        self._row_order: list[str] = [
            "timing",
            "magnitude",
            "rate_of_change",
            "duration",
            "frequency",
            *(f"generic:{i}" for i in range(len(self._characteristic_vars))),
        ]
        self._path_var.trace_add("write", self._on_path_or_output_dir_changed)
        self._output_dir_var.trace_add("write", self._on_path_or_output_dir_changed)
        self._data_units_var.trace_add("write", self._on_data_units_changed)
        self._magnitude_enabled_var.trace_add(
            "write", lambda *_: self._on_card_enabled_changed("magnitude")
        )
        self._magnitude_mode_var.trace_add("write", self._on_magnitude_mode_changed)
        self._magnitude_ma_enabled_var.trace_add("write", self._on_magnitude_ma_enabled_changed)
        self._duration_enabled_var.trace_add(
            "write", lambda *_: self._on_card_enabled_changed("duration")
        )
        self._duration_mode_var.trace_add("write", self._on_duration_mode_changed)
        self._timing_enabled_var.trace_add(
            "write", lambda *_: self._on_card_enabled_changed("timing")
        )
        self._roc_enabled_var.trace_add(
            "write", lambda *_: self._on_card_enabled_changed("rate_of_change")
        )
        self._roc_mode_var.trace_add("write", self._on_roc_mode_changed)
        self._roc_ma_enabled_var.trace_add("write", self._on_roc_ma_enabled_changed)
        self._roc_look_back_enabled_var.trace_add("write", self._on_roc_look_back_enabled_changed)
        self._roc_min_enabled_var.trace_add("write", self._on_roc_min_enabled_changed)
        self._freq_enabled_var.trace_add(
            "write", lambda *_: self._on_card_enabled_changed("frequency")
        )
        self._freq_nested_enabled_var.trace_add("write", self._on_freq_nested_enabled_changed)
        self._freq_vars["base"]["mode"].trace_add(
            "write", lambda *_: self._on_freq_mode_changed("base")
        )
        self._freq_vars["nested"]["mode"].trace_add(
            "write", lambda *_: self._on_freq_mode_changed("nested")
        )

    def _build_ui(self) -> None:
        self._root.title("hydropattern-gui")
        self._root.geometry("1100x850")
        container = self._build_scrollable_container()
        self._build_timeseries_section(container)
        self._build_component_section(container)
        self._build_output_section(container)
        self._build_climate_section(container)
        self._build_preview_section(container)
        self._build_save_section(container)
        self._build_run_section(container)
        self._set_log_placeholder()
        self._update_characteristic_row_states()

    def _build_scrollable_container(self) -> ttk.Frame:
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
        return container

    def _build_timeseries_section(self, container: ttk.Frame) -> None:
        ts_frame = ttk.LabelFrame(container, text="Timeseries", padding=8)
        ts_frame.pack(fill=tk.X)
        _row_labeled_entry(ts_frame, 0, "Path", self._path_var, width=80)
        ttk.Button(ts_frame, text="Browse...", command=self._on_browse_timeseries).grid(
            row=0, column=2, sticky=tk.W, padx=4, pady=4
        )
        _row_labeled_entry(ts_frame, 1, "Date format (optional)", self._date_format_var, width=20)
        _row_labeled_entry(ts_frame, 2, "First day of WY", self._first_day_var, width=8)
        _row_labeled_entry(ts_frame, 3, "Sheet", self._sheet_name_var, width=12)
        _row_labeled_entry(
            ts_frame, 4, "Data units (optional, e.g. cfs)", self._data_units_var, width=20
        )

    def _build_component_section(self, container: ttk.Frame) -> None:
        component_frame = ttk.LabelFrame(container, text="Component editor", padding=8)
        component_frame.pack(fill=tk.X, pady=(8, 0))
        _row_labeled_entry(component_frame, 0, "Component", self._component_name_var, width=30)
        ttk.Checkbutton(
            component_frame, text="Verbose", variable=self._component_verbose_var
        ).grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        ttk.Checkbutton(
            component_frame, text="Success pattern", variable=self._component_success_var
        ).grid(row=1, column=1, sticky=tk.W, padx=4, pady=4)
        ttk.Label(component_frame, text="Characteristics").grid(
            row=2, column=0, columnspan=3, sticky=tk.W, padx=4, pady=4
        )
        self._build_timing_card(component_frame, row=3)
        self._build_magnitude_card(component_frame, row=4)
        self._build_rate_of_change_card(component_frame, row=5)
        self._build_duration_card(component_frame, row=6)
        self._build_frequency_card(component_frame, row=7)
        self._typed_cards: dict[str, ttk.LabelFrame] = {
            "timing": self._timing_card,
            "magnitude": self._magnitude_card,
            "rate_of_change": self._roc_card,
            "duration": self._duration_card,
            "frequency": self._freq_card,
        }
        # Generic lookups backing the reorder/enable-state helpers below, so
        # each typed card no longer needs its own copy-pasted method family
        # (_update_X_card_enabled_state / _update_X_reorder_buttons / etc.).
        self._card_bodies: dict[str, ttk.Frame] = {
            "timing": self._timing_body,
            "magnitude": self._magnitude_body,
            "rate_of_change": self._roc_body,
            "duration": self._duration_body,
            "frequency": self._freq_body,
        }
        self._reorder_buttons: dict[str, tuple[ttk.Button, ttk.Button]] = {
            "timing": (self._timing_up_button, self._timing_down_button),
            "magnitude": (self._magnitude_up_button, self._magnitude_down_button),
            "rate_of_change": (self._roc_up_button, self._roc_down_button),
            "duration": (self._duration_up_button, self._duration_down_button),
            "frequency": (self._freq_up_button, self._freq_down_button),
        }
        self._enabled_vars: dict[str, tk.BooleanVar] = {
            "timing": self._timing_enabled_var,
            "magnitude": self._magnitude_enabled_var,
            "rate_of_change": self._roc_enabled_var,
            "duration": self._duration_enabled_var,
            "frequency": self._freq_enabled_var,
        }
        for kind in self._typed_cards:
            self._update_reorder_buttons(kind)
        generic_kinds = tuple(
            kind
            for kind in _CHARACTERISTIC_KINDS
            if kind not in ("timing", "magnitude", "rate_of_change", "duration", "frequency")
        )
        # All 5 canonical characteristic kinds now have dedicated typed
        # cards, so this freeform pool is currently always empty; kept as
        # the extension point for any future characteristic kind hydropattern
        # adds that doesn't yet have a typed card.
        if generic_kinds:
            ttk.Label(
                component_frame, text="Other characteristic rows (top->bottom = order)"
            ).grid(row=8, column=0, columnspan=3, sticky=tk.W, padx=4, pady=(12, 4))
        for index, default_kind in enumerate(generic_kinds):
            kind_var = tk.StringVar(value=default_kind)
            metrics_var = tk.StringVar()
            self._characteristic_vars.append((kind_var, metrics_var))
            row = 9 + index
            ttk.Label(component_frame, text=f"{index+1}.").grid(
                row=row, column=0, sticky=tk.W, padx=4, pady=2
            )
            kind_box = ttk.Combobox(
                component_frame,
                textvariable=kind_var,
                values=generic_kinds,
                state="readonly",
                width=16,
            )
            kind_box.grid(row=row, column=1, sticky=tk.W, padx=4, pady=2)
            metrics_entry = ttk.Entry(component_frame, textvariable=metrics_var, width=70)
            metrics_entry.grid(row=row, column=2, sticky=tk.W, padx=4, pady=2)
            self._characteristic_widgets.append((kind_box, metrics_entry))
            metrics_var.trace_add("write", self._on_characteristic_metrics_changed)

    def _build_timing_card(self, parent: ttk.LabelFrame | ttk.Frame, row: int) -> None:
        card = ttk.LabelFrame(parent, text="", padding=6)
        card.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=4, pady=2)
        self._timing_card = card
        header_row = ttk.Frame(card)
        header_row.grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(
            header_row, text="Timing", variable=self._timing_enabled_var
        ).pack(side=tk.LEFT)
        self._timing_up_button = ttk.Button(
            header_row, text="\u25b2", width=2, command=lambda: self._move_row("timing", -1)
        )
        self._timing_up_button.pack(side=tk.LEFT, padx=(8, 0))
        self._timing_down_button = ttk.Button(
            header_row, text="\u25bc", width=2, command=lambda: self._move_row("timing", 1)
        )
        self._timing_down_button.pack(side=tk.LEFT, padx=(2, 0))

        self._timing_body = ttk.Frame(card, padding=(20, 4, 0, 0))
        self._timing_body.grid(row=1, column=0, sticky=tk.W)

        fields_row = ttk.Frame(self._timing_body)
        fields_row.grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(fields_row, text="First day of year").grid(row=0, column=0, padx=4)
        ttk.Entry(
            fields_row, textvariable=self._timing_first_day_var, width=8
        ).grid(row=0, column=1, padx=4)
        ttk.Label(fields_row, text="Last day of year").grid(row=0, column=2, padx=4)
        ttk.Entry(
            fields_row, textvariable=self._timing_last_day_var, width=8
        ).grid(row=0, column=3, padx=4)
        ttk.Label(fields_row, text="(1-366)").grid(row=0, column=4, padx=4)

        if self._timing_enabled_var.get():
            self._timing_body.grid()
        else:
            self._timing_body.grid_remove()

    def _build_magnitude_card(self, parent: ttk.LabelFrame | ttk.Frame, row: int) -> None:
        card = ttk.LabelFrame(parent, text="", padding=6)
        card.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=4, pady=2)
        self._magnitude_card = card
        header_row = ttk.Frame(card)
        header_row.grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(
            header_row, text="Magnitude", variable=self._magnitude_enabled_var
        ).pack(side=tk.LEFT)
        self._magnitude_up_button = ttk.Button(
            header_row, text="\u25b2", width=2, command=lambda: self._move_row("magnitude", -1)
        )
        self._magnitude_up_button.pack(side=tk.LEFT, padx=(8, 0))
        self._magnitude_down_button = ttk.Button(
            header_row, text="\u25bc", width=2, command=lambda: self._move_row("magnitude", 1)
        )
        self._magnitude_down_button.pack(side=tk.LEFT, padx=(2, 0))

        self._magnitude_body = ttk.Frame(card, padding=(20, 4, 0, 0))
        self._magnitude_body.grid(row=1, column=0, sticky=tk.W)

        mode_row = ttk.Frame(self._magnitude_body)
        mode_row.grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(mode_row, text="Mode:").pack(side=tk.LEFT)
        ttk.Radiobutton(
            mode_row, text="Simple", value="simple", variable=self._magnitude_mode_var
        ).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Radiobutton(
            mode_row, text="Between", value="between", variable=self._magnitude_mode_var
        ).pack(side=tk.LEFT, padx=(4, 0))

        self._magnitude_simple_frame = ttk.Frame(self._magnitude_body)
        self._magnitude_simple_frame.grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(self._magnitude_simple_frame, text="Operator").grid(row=0, column=0, padx=4)
        ttk.Combobox(
            self._magnitude_simple_frame,
            textvariable=self._magnitude_operator_var,
            values=("<", "<=", ">", ">=", "=", "!="),
            state="readonly",
            width=6,
        ).grid(row=0, column=1, padx=4)
        ttk.Label(self._magnitude_simple_frame, text="Threshold").grid(row=0, column=2, padx=4)
        ttk.Entry(
            self._magnitude_simple_frame, textvariable=self._magnitude_threshold_var, width=12
        ).grid(row=0, column=3, padx=4)
        self._magnitude_threshold_unit_label = ttk.Label(self._magnitude_simple_frame, text="")
        self._magnitude_threshold_unit_label.grid(row=0, column=4, padx=4)

        self._magnitude_between_frame = ttk.Frame(self._magnitude_body)
        self._magnitude_between_frame.grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(self._magnitude_between_frame, text="Min").grid(row=0, column=0, padx=4)
        ttk.Entry(
            self._magnitude_between_frame, textvariable=self._magnitude_min_var, width=12
        ).grid(row=0, column=1, padx=4)
        self._magnitude_min_unit_label = ttk.Label(self._magnitude_between_frame, text="")
        self._magnitude_min_unit_label.grid(row=0, column=2, padx=4)
        ttk.Label(self._magnitude_between_frame, text="Max").grid(row=0, column=3, padx=4)
        ttk.Entry(
            self._magnitude_between_frame, textvariable=self._magnitude_max_var, width=12
        ).grid(row=0, column=4, padx=4)
        self._magnitude_max_unit_label = ttk.Label(self._magnitude_between_frame, text="")
        self._magnitude_max_unit_label.grid(row=0, column=5, padx=4)

        ma_row = ttk.Frame(self._magnitude_body)
        ma_row.grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(
            ma_row, text="Moving average", variable=self._magnitude_ma_enabled_var
        ).pack(side=tk.LEFT)
        ttk.Label(ma_row, text="Periods").pack(side=tk.LEFT, padx=(8, 4))
        self._magnitude_ma_periods_entry = ttk.Entry(
            ma_row, textvariable=self._magnitude_ma_periods_var, width=8
        )
        self._magnitude_ma_periods_entry.pack(side=tk.LEFT)
        ttk.Label(ma_row, text="(timesteps)").pack(side=tk.LEFT, padx=(4, 0))

        self._update_magnitude_unit_labels()
        self._update_magnitude_mode_visibility()
        if self._magnitude_enabled_var.get():
            self._magnitude_body.grid()
        else:
            self._magnitude_body.grid_remove()

    def _build_duration_card(self, parent: ttk.LabelFrame | ttk.Frame, row: int) -> None:
        card = ttk.LabelFrame(parent, text="", padding=6)
        card.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=4, pady=2)
        self._duration_card = card
        header_row = ttk.Frame(card)
        header_row.grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(
            header_row, text="Duration", variable=self._duration_enabled_var
        ).pack(side=tk.LEFT)
        self._duration_up_button = ttk.Button(
            header_row, text="\u25b2", width=2, command=lambda: self._move_row("duration", -1)
        )
        self._duration_up_button.pack(side=tk.LEFT, padx=(8, 0))
        self._duration_down_button = ttk.Button(
            header_row, text="\u25bc", width=2, command=lambda: self._move_row("duration", 1)
        )
        self._duration_down_button.pack(side=tk.LEFT, padx=(2, 0))

        self._duration_body = ttk.Frame(card, padding=(20, 4, 0, 0))
        self._duration_body.grid(row=1, column=0, sticky=tk.W)

        mode_row = ttk.Frame(self._duration_body)
        mode_row.grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(mode_row, text="Mode:").pack(side=tk.LEFT)
        ttk.Radiobutton(
            mode_row, text="Simple", value="simple", variable=self._duration_mode_var
        ).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Radiobutton(
            mode_row, text="Between", value="between", variable=self._duration_mode_var
        ).pack(side=tk.LEFT, padx=(4, 0))

        self._duration_simple_frame = ttk.Frame(self._duration_body)
        self._duration_simple_frame.grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(self._duration_simple_frame, text="Operator").grid(row=0, column=0, padx=4)
        ttk.Combobox(
            self._duration_simple_frame,
            textvariable=self._duration_operator_var,
            values=("<", "<=", ">", ">=", "=", "!="),
            state="readonly",
            width=6,
        ).grid(row=0, column=1, padx=4)
        ttk.Label(self._duration_simple_frame, text="Steps").grid(row=0, column=2, padx=4)
        ttk.Entry(
            self._duration_simple_frame, textvariable=self._duration_steps_var, width=12
        ).grid(row=0, column=3, padx=4)
        ttk.Label(self._duration_simple_frame, text="(timesteps)").grid(row=0, column=4, padx=4)

        self._duration_between_frame = ttk.Frame(self._duration_body)
        self._duration_between_frame.grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(self._duration_between_frame, text="Min").grid(row=0, column=0, padx=4)
        ttk.Entry(
            self._duration_between_frame, textvariable=self._duration_min_var, width=12
        ).grid(row=0, column=1, padx=4)
        ttk.Label(self._duration_between_frame, text="(timesteps)").grid(row=0, column=2, padx=4)
        ttk.Label(self._duration_between_frame, text="Max").grid(row=0, column=3, padx=4)
        ttk.Entry(
            self._duration_between_frame, textvariable=self._duration_max_var, width=12
        ).grid(row=0, column=4, padx=4)
        ttk.Label(self._duration_between_frame, text="(timesteps)").grid(row=0, column=5, padx=4)

        self._update_duration_mode_visibility()
        if self._duration_enabled_var.get():
            self._duration_body.grid()
        else:
            self._duration_body.grid_remove()

    def _build_rate_of_change_card(self, parent: ttk.LabelFrame | ttk.Frame, row: int) -> None:
        card = ttk.LabelFrame(parent, text="", padding=6)
        card.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=4, pady=2)
        self._roc_card = card
        header_row = ttk.Frame(card)
        header_row.grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(
            header_row, text="Rate of change", variable=self._roc_enabled_var
        ).pack(side=tk.LEFT)
        self._roc_up_button = ttk.Button(
            header_row, text="\u25b2", width=2, command=lambda: self._move_row("rate_of_change", -1)
        )
        self._roc_up_button.pack(side=tk.LEFT, padx=(8, 0))
        self._roc_down_button = ttk.Button(
            header_row, text="\u25bc", width=2, command=lambda: self._move_row("rate_of_change", 1)
        )
        self._roc_down_button.pack(side=tk.LEFT, padx=(2, 0))

        self._roc_body = ttk.Frame(card, padding=(20, 4, 0, 0))
        self._roc_body.grid(row=1, column=0, sticky=tk.W)

        mode_row = ttk.Frame(self._roc_body)
        mode_row.grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(mode_row, text="Mode:").pack(side=tk.LEFT)
        ttk.Radiobutton(
            mode_row, text="Simple", value="simple", variable=self._roc_mode_var
        ).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Radiobutton(
            mode_row, text="Between", value="between", variable=self._roc_mode_var
        ).pack(side=tk.LEFT, padx=(4, 0))

        self._roc_simple_frame = ttk.Frame(self._roc_body)
        self._roc_simple_frame.grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(self._roc_simple_frame, text="Operator").grid(row=0, column=0, padx=4)
        ttk.Combobox(
            self._roc_simple_frame,
            textvariable=self._roc_operator_var,
            values=("<", "<=", ">", ">=", "=", "!="),
            state="readonly",
            width=6,
        ).grid(row=0, column=1, padx=4)
        ttk.Label(self._roc_simple_frame, text="Threshold").grid(row=0, column=2, padx=4)
        ttk.Entry(
            self._roc_simple_frame, textvariable=self._roc_threshold_var, width=12
        ).grid(row=0, column=3, padx=4)

        self._roc_between_frame = ttk.Frame(self._roc_body)
        self._roc_between_frame.grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(self._roc_between_frame, text="Min").grid(row=0, column=0, padx=4)
        ttk.Entry(
            self._roc_between_frame, textvariable=self._roc_min_var, width=12
        ).grid(row=0, column=1, padx=4)
        ttk.Label(self._roc_between_frame, text="Max").grid(row=0, column=2, padx=4)
        ttk.Entry(
            self._roc_between_frame, textvariable=self._roc_max_var, width=12
        ).grid(row=0, column=3, padx=4)

        # Cascading optionals: hydropattern requires each earlier optional
        # (ma_periods -> look_back -> min) to be a real value before a later
        # one can be supplied, so each checkbox below is only enabled once
        # the prior one is checked (see rate-of-change-independent-optional-params todo).
        ma_row = ttk.Frame(self._roc_body)
        ma_row.grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(
            ma_row, text="Moving average", variable=self._roc_ma_enabled_var
        ).pack(side=tk.LEFT)
        ttk.Label(ma_row, text="Periods").pack(side=tk.LEFT, padx=(8, 4))
        self._roc_ma_periods_entry = ttk.Entry(
            ma_row, textvariable=self._roc_ma_periods_var, width=8
        )
        self._roc_ma_periods_entry.pack(side=tk.LEFT)
        ttk.Label(ma_row, text="(timesteps)").pack(side=tk.LEFT, padx=(4, 0))

        look_back_row = ttk.Frame(self._roc_body)
        look_back_row.grid(row=3, column=0, sticky=tk.W, pady=2)
        self._roc_look_back_checkbutton = ttk.Checkbutton(
            look_back_row, text="Look back", variable=self._roc_look_back_enabled_var
        )
        self._roc_look_back_checkbutton.pack(side=tk.LEFT)
        ttk.Label(look_back_row, text="Steps").pack(side=tk.LEFT, padx=(8, 4))
        self._roc_look_back_entry = ttk.Entry(
            look_back_row, textvariable=self._roc_look_back_var, width=8
        )
        self._roc_look_back_entry.pack(side=tk.LEFT)
        ttk.Label(look_back_row, text="(timesteps)").pack(side=tk.LEFT, padx=(4, 0))

        min_row = ttk.Frame(self._roc_body)
        min_row.grid(row=4, column=0, sticky=tk.W, pady=2)
        self._roc_min_checkbutton = ttk.Checkbutton(
            min_row, text="Min y[t-n]", variable=self._roc_min_enabled_var
        )
        self._roc_min_checkbutton.pack(side=tk.LEFT)
        self._roc_min_value_entry = ttk.Entry(
            min_row, textvariable=self._roc_min_value_var, width=12
        )
        self._roc_min_value_entry.pack(side=tk.LEFT, padx=(8, 0))

        self._update_roc_mode_visibility()
        self._update_roc_cascade_state()
        if self._roc_enabled_var.get():
            self._roc_body.grid()
        else:
            self._roc_body.grid_remove()

    def _build_frequency_card(self, parent: ttk.LabelFrame | ttk.Frame, row: int) -> None:
        card = ttk.LabelFrame(parent, text="", padding=6)
        card.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=4, pady=2)
        self._freq_card = card
        header_row = ttk.Frame(card)
        header_row.grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(
            header_row, text="Frequency", variable=self._freq_enabled_var
        ).pack(side=tk.LEFT)
        self._freq_up_button = ttk.Button(
            header_row, text="\u25b2", width=2, command=lambda: self._move_row("frequency", -1)
        )
        self._freq_up_button.pack(side=tk.LEFT, padx=(8, 0))
        self._freq_down_button = ttk.Button(
            header_row, text="\u25bc", width=2, command=lambda: self._move_row("frequency", 1)
        )
        self._freq_down_button.pack(side=tk.LEFT, padx=(2, 0))

        self._freq_body = ttk.Frame(card, padding=(20, 4, 0, 0))
        self._freq_body.grid(row=1, column=0, sticky=tk.W)

        self._freq_nested_checkbutton = ttk.Checkbutton(
            self._freq_body, text="Nested pattern", variable=self._freq_nested_enabled_var
        )
        self._freq_nested_checkbutton.grid(row=0, column=0, sticky=tk.W, pady=(0, 4))

        ttk.Label(self._freq_body, text="Base pattern:").grid(
            row=1, column=0, sticky=tk.W, pady=(4, 0)
        )
        self._freq_frames: dict[str, ttk.Widget] = {}
        self._build_frequency_pattern_editor(
            self._freq_body, prefix="base", row=2, allow_probability=True
        )

        self._freq_nested_label = ttk.Label(self._freq_body, text="Nested pattern:")
        self._freq_nested_label.grid(row=3, column=0, sticky=tk.W, pady=(8, 0))
        self._build_frequency_pattern_editor(
            self._freq_body, prefix="nested", row=4, allow_probability=False
        )

        self._update_freq_mode_visibility("base")
        self._update_freq_mode_visibility("nested")
        self._update_freq_nested_visibility()
        if self._freq_enabled_var.get():
            self._freq_body.grid()
        else:
            self._freq_body.grid_remove()

    def _build_frequency_pattern_editor(
        self, parent: ttk.Frame, prefix: str, row: int, allow_probability: bool
    ) -> None:
        """Builds one Frequency pattern's mode-picker + per-mode field rows.
        Shared by the always-present base pattern and the optional nested
        pattern (which never allows PROBABILITY mode)."""
        pattern_vars = self._freq_vars[prefix]
        wrapper = ttk.Frame(parent)
        wrapper.grid(row=row, column=0, sticky=tk.W, pady=2)
        self._freq_frames[f"{prefix}_wrapper"] = wrapper

        mode_row = ttk.Frame(wrapper)
        mode_row.grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(mode_row, text="Mode:").pack(side=tk.LEFT)
        ttk.Radiobutton(
            mode_row, text="Count", value="count", variable=pattern_vars["mode"]
        ).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Radiobutton(
            mode_row, text="Between", value="between", variable=pattern_vars["mode"]
        ).pack(side=tk.LEFT, padx=(4, 0))
        probability_radio = ttk.Radiobutton(
            mode_row, text="Probability", value="probability", variable=pattern_vars["mode"]
        )
        probability_radio.pack(side=tk.LEFT, padx=(4, 0))
        if not allow_probability:
            probability_radio.configure(state="disabled")
        self._freq_frames[f"{prefix}_probability_radio"] = probability_radio

        count_frame = ttk.Frame(wrapper)
        count_frame.grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(count_frame, text="Operator").grid(row=0, column=0, padx=4)
        ttk.Combobox(
            count_frame,
            textvariable=pattern_vars["operator"],
            values=("<", "<=", ">", ">=", "=", "!="),
            state="readonly",
            width=6,
        ).grid(row=0, column=1, padx=4)
        ttk.Label(count_frame, text="Count (n)").grid(row=0, column=2, padx=4)
        ttk.Entry(count_frame, textvariable=pattern_vars["count_n"], width=8).grid(
            row=0, column=3, padx=4
        )
        ttk.Label(count_frame, text="Out of (N)").grid(row=0, column=4, padx=4)
        ttk.Entry(count_frame, textvariable=pattern_vars["out_of_n"], width=8).grid(
            row=0, column=5, padx=4
        )
        self._freq_frames[f"{prefix}_count"] = count_frame

        between_frame = ttk.Frame(wrapper)
        between_frame.grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(between_frame, text="Min").grid(row=0, column=0, padx=4)
        ttk.Entry(between_frame, textvariable=pattern_vars["between_min"], width=8).grid(
            row=0, column=1, padx=4
        )
        ttk.Label(between_frame, text="Max").grid(row=0, column=2, padx=4)
        ttk.Entry(between_frame, textvariable=pattern_vars["between_max"], width=8).grid(
            row=0, column=3, padx=4
        )
        ttk.Label(between_frame, text="Out of (N)").grid(row=0, column=4, padx=4)
        ttk.Entry(between_frame, textvariable=pattern_vars["out_of_n"], width=8).grid(
            row=0, column=5, padx=4
        )
        self._freq_frames[f"{prefix}_between"] = between_frame

        probability_frame = ttk.Frame(wrapper)
        probability_frame.grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(probability_frame, text="Operator").grid(row=0, column=0, padx=4)
        ttk.Combobox(
            probability_frame,
            textvariable=pattern_vars["operator"],
            values=("<", "<=", ">", ">=", "=", "!="),
            state="readonly",
            width=6,
        ).grid(row=0, column=1, padx=4)
        ttk.Label(probability_frame, text="Probability").grid(row=0, column=2, padx=4)
        ttk.Entry(probability_frame, textvariable=pattern_vars["probability"], width=8).grid(
            row=0, column=3, padx=4
        )
        ttk.Label(probability_frame, text="(0-1)").grid(row=0, column=4, padx=4)
        self._freq_frames[f"{prefix}_probability"] = probability_frame

        ttk.Checkbutton(
            wrapper,
            text="Count by event (uncheck for interval)",
            variable=pattern_vars["count_by_event"],
        ).grid(row=2, column=0, sticky=tk.W, pady=(2, 0))

    def _build_output_section(self, container: ttk.Frame) -> None:
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

    def _build_climate_section(self, container: ttk.Frame) -> None:
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

    def _build_preview_section(self, container: ttk.Frame) -> None:
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

    def _build_save_section(self, container: ttk.Frame) -> None:
        save_row = ttk.Frame(container)
        save_row.pack(fill=tk.X, pady=(8, 0))
        _row_labeled_entry(save_row, 0, "TOML file path", self._toml_path_var, width=90)
        ttk.Button(save_row, text="Save TOML", command=self._on_save).grid(
            row=0, column=2, sticky=tk.W, padx=4, pady=4
        )

    def _build_run_section(self, container: ttk.Frame) -> None:
        run_row = ttk.Frame(container)
        run_row.pack(fill=tk.X, pady=(8, 0))
        self._run_button = ttk.Button(run_row, text="Run", command=self._on_run)
        self._run_button.pack(side=tk.LEFT, padx=4)
        self._run_progress = ttk.Progressbar(run_row, mode="indeterminate", length=220)
        ttk.Label(run_row, textvariable=self._status_var).pack(side=tk.RIGHT, padx=4)

        self._log_text = tk.Text(container, height=8, wrap=tk.NONE)
        self._log_text.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

    def _typed_card_specs(self) -> dict[str, tuple[tk.BooleanVar, Callable[[], str]]]:
        """Per-typed-kind (enabled_var, read_and_convert_to_metrics_text)
        used by both _collect_state (row order) and reorder/active-state
        helpers."""
        return {
            "timing": (
                self._timing_enabled_var,
                lambda: timing_fields_to_metrics(self._read_timing_fields()),
            ),
            "magnitude": (
                self._magnitude_enabled_var,
                lambda: magnitude_fields_to_metrics(self._read_magnitude_fields()),
            ),
            "rate_of_change": (
                self._roc_enabled_var,
                lambda: rate_of_change_fields_to_metrics(self._read_roc_fields()),
            ),
            "duration": (
                self._duration_enabled_var,
                lambda: duration_fields_to_metrics(self._read_duration_fields()),
            ),
            "frequency": (
                self._freq_enabled_var,
                lambda: frequency_fields_to_metrics(self._read_frequency_fields()),
            ),
        }

    def _collect_state(self) -> GuiFormState:
        typed_specs = self._typed_card_specs()
        rows: list[CharacteristicRowState] = []
        for row_id in self._row_order:
            if row_id.startswith("generic:"):
                index = int(row_id.split(":", 1)[1])
                kind_var, metrics_var = self._characteristic_vars[index]
                metrics_text = metrics_var.get().strip()
                if metrics_text:
                    rows.append(
                        CharacteristicRowState(
                            kind=cast(CharacteristicKind, kind_var.get()),
                            metrics_text=metrics_text,
                        )
                    )
                continue
            enabled_var, to_metrics_text = typed_specs[row_id]
            if not enabled_var.get():
                continue
            try:
                metrics_text = to_metrics_text()
            except FormValidationError:
                # Incomplete/invalid typed input while the user is still
                # editing; fall back to an empty metrics_text so downstream
                # config validation reports the standard "required" field
                # error instead of silently dropping the row.
                metrics_text = ""
            kind = cast(CharacteristicKind, row_id)
            rows.append(CharacteristicRowState(kind=kind, metrics_text=metrics_text))
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
        magnitude_enabled, magnitude_fields = extract_magnitude_state(state.characteristic_rows)
        self._write_magnitude_fields(magnitude_enabled, magnitude_fields)
        duration_enabled, duration_fields = extract_duration_state(state.characteristic_rows)
        self._write_duration_fields(duration_enabled, duration_fields)
        timing_enabled, timing_fields = extract_timing_state(state.characteristic_rows)
        self._write_timing_fields(timing_enabled, timing_fields)
        roc_enabled, roc_fields = extract_rate_of_change_state(state.characteristic_rows)
        self._write_roc_fields(roc_enabled, roc_fields)
        freq_enabled, freq_fields = extract_frequency_state(state.characteristic_rows)
        self._write_frequency_fields(freq_enabled, freq_fields)
        typed_kinds = ("timing", "magnitude", "rate_of_change", "duration", "frequency")
        generic_rows = [row for row in state.characteristic_rows if row.kind not in typed_kinds]
        for index, (kind_var, metrics_var) in enumerate(self._characteristic_vars):
            if index < len(generic_rows):
                row = generic_rows[index]
                kind_var.set(row.kind)
                metrics_var.set(row.metrics_text)
            else:
                generic_kinds = tuple(k for k in _CHARACTERISTIC_KINDS if k not in typed_kinds)
                kind_var.set(generic_kinds[min(index, len(generic_kinds) - 1)])
                metrics_var.set("")
        # Rebuild the shared row-order list from the loaded row order itself
        # (each typed kind's own position, each generic row mapped to its
        # slot index above), then append any identifiers absent from the
        # loaded config (e.g. a disabled typed card) at the end so the list
        # always stays a complete permutation of all row identifiers.
        row_order: list[str] = []
        generic_counter = 0
        for row in state.characteristic_rows:
            if row.kind in typed_kinds:
                row_order.append(row.kind)
            else:
                row_order.append(f"generic:{generic_counter}")
                generic_counter += 1
        for kind in typed_kinds:
            if kind not in row_order:
                row_order.append(kind)
        for index in range(len(self._characteristic_vars)):
            generic_id = f"generic:{index}"
            if generic_id not in row_order:
                row_order.append(generic_id)
        self._row_order = row_order
        self._sync_toml_path_default()
        self._update_characteristic_row_states()
        self._refresh_all_reorder_buttons()

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
            messagebox.showerror("Cannot save TOML", f"Validation error:\n{exc}")
            return
        self._status_var.set(f"Saved: {path}")

    def _on_preview(self) -> None:
        state = self._collect_state()
        try:
            preview = self._controller.preview_toml(state, mode="minimal")
        except FormValidationError as exc:
            self._status_var.set(f"Validation error: {exc}")
            messagebox.showerror("Cannot preview TOML", f"Validation error:\n{exc}")
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
        self._refresh_all_reorder_buttons()

    def _on_data_units_changed(self, *_: object) -> None:
        self._update_magnitude_unit_labels()

    def _on_card_enabled_changed(self, kind: str) -> None:
        self._update_card_enabled_state(kind)
        self._refresh_all_reorder_buttons()

    def _on_magnitude_mode_changed(self, *_: object) -> None:
        # Reset the fields belonging to the mode being left, per the locked
        # design decision: Simple<->Between values are not auto-mapped into
        # one another (threshold != min/max semantically).
        if self._magnitude_mode_var.get() == "simple":
            self._magnitude_min_var.set("")
            self._magnitude_max_var.set("")
        else:
            self._magnitude_operator_var.set(">")
            self._magnitude_threshold_var.set("")
        self._update_magnitude_mode_visibility()

    def _on_magnitude_ma_enabled_changed(self, *_: object) -> None:
        state = "normal" if self._magnitude_ma_enabled_var.get() else "disabled"
        self._magnitude_ma_periods_entry.configure(state=state)
        if state == "disabled":
            self._magnitude_ma_periods_var.set("")

    def _row_is_active(self, row_id: str) -> bool:
        """True if the given row identifier ("timing"/"magnitude"/... or
        "generic:{i}") currently represents a row that would appear in the
        exported TOML: an enabled typed card, or a generic row with
        non-empty metrics text."""
        if row_id.startswith("generic:"):
            index = int(row_id.split(":", 1)[1])
            return bool(self._characteristic_vars[index][1].get().strip())
        enabled_var, _to_metrics_text = self._typed_card_specs()[row_id]
        return bool(enabled_var.get())

    def _active_row_order(self) -> list[str]:
        return [row_id for row_id in self._row_order if self._row_is_active(row_id)]

    def _move_row(self, kind: CharacteristicKind, direction: int) -> None:
        """Swap `kind`'s position with the adjacent *active* row (direction
        -1 = up, +1 = down) within the single shared self._row_order list.
        Replaces the old per-card integer-offset design, which could not
        represent "typed card A after typed card B" once both defaulted to
        the same offset (e.g. two typed cards enabled, no generic rows)."""
        active = self._active_row_order()
        position = active.index(kind)
        new_position = position + direction
        if new_position < 0 or new_position >= len(active):
            return
        other = active[new_position]
        i, j = self._row_order.index(kind), self._row_order.index(other)
        self._row_order[i], self._row_order[j] = self._row_order[j], self._row_order[i]
        self._refresh_all_reorder_buttons()

    def _refresh_card_grid_rows(self) -> None:
        """Re-grid the 4 typed card widgets to match their relative order
        within self._row_order. Fixing _collect_state alone changed the
        exported TOML order but left the cards visually frozen in their
        original build-time rows -- this keeps the on-screen stack in sync
        too."""
        # Disabled typed cards sink below enabled ones (matching how
        # unused/empty generic rows are already excluded from the exported
        # TOML) rather than staying frozen at their canonical build-time
        # slot, which could visually wedge a disabled card between two
        # enabled ones the user just swapped.
        typed_ids = [row_id for row_id in self._row_order if row_id in self._typed_cards]
        active_typed = [row_id for row_id in typed_ids if self._row_is_active(row_id)]
        inactive_typed = [row_id for row_id in typed_ids if not self._row_is_active(row_id)]
        typed_order = active_typed + inactive_typed
        for position, kind in enumerate(typed_order):
            self._typed_cards[kind].grid(
                row=3 + position, column=0, columnspan=3, sticky=tk.EW, padx=4, pady=2
            )

    def _update_reorder_buttons(self, kind: str) -> None:
        """Generic replacement for the 5 near-identical _update_X_reorder_buttons
        methods: pack/hide a typed card's up/down buttons and enable/disable
        them based on its position among currently-active rows."""
        up_button, down_button = self._reorder_buttons[kind]
        if not self._enabled_vars[kind].get():
            up_button.pack_forget()
            down_button.pack_forget()
            return
        up_button.pack(side=tk.LEFT, padx=(8, 0))
        down_button.pack(side=tk.LEFT, padx=(2, 0))
        active = self._active_row_order()
        position = active.index(kind)
        up_button.configure(state="disabled" if position <= 0 else "normal")
        down_button.configure(state="disabled" if position >= len(active) - 1 else "normal")

    def _update_card_enabled_state(self, kind: str) -> None:
        """Generic replacement for the 5 near-identical
        _update_X_card_enabled_state methods."""
        if self._enabled_vars[kind].get():
            self._card_bodies[kind].grid()
        else:
            self._card_bodies[kind].grid_remove()
        self._update_reorder_buttons(kind)

    def _refresh_all_reorder_buttons(self) -> None:
        """Re-evaluate every typed card's up/down button bound; each card's
        bound depends on its position among *all* currently-active rows."""
        for kind in self._typed_cards:
            self._update_reorder_buttons(kind)
        self._refresh_card_grid_rows()

    def _update_magnitude_mode_visibility(self) -> None:
        if self._magnitude_mode_var.get() == "simple":
            self._magnitude_simple_frame.grid()
            self._magnitude_between_frame.grid_remove()
        else:
            self._magnitude_simple_frame.grid_remove()
            self._magnitude_between_frame.grid()

    def _update_magnitude_unit_labels(self) -> None:
        unit_text = f"({self._data_units_var.get().strip() or 'data units'})"
        self._magnitude_threshold_unit_label.configure(text=unit_text)
        self._magnitude_min_unit_label.configure(text=unit_text)
        self._magnitude_max_unit_label.configure(text=unit_text)

    def _read_magnitude_fields(self) -> MagnitudeFields:
        mode = cast(MagnitudeMode, self._magnitude_mode_var.get())
        return MagnitudeFields(
            mode=mode,
            operator=self._magnitude_operator_var.get() or None,
            threshold=_parse_optional_float(self._magnitude_threshold_var.get()),
            minimum=_parse_optional_float(self._magnitude_min_var.get()),
            maximum=_parse_optional_float(self._magnitude_max_var.get()),
            ma_enabled=self._magnitude_ma_enabled_var.get(),
            ma_periods=_parse_optional_int(self._magnitude_ma_periods_var.get()),
        )

    def _write_magnitude_fields(self, enabled: bool, fields: MagnitudeFields) -> None:
        self._magnitude_enabled_var.set(enabled)
        self._magnitude_mode_var.set(fields.mode)
        self._magnitude_operator_var.set(fields.operator or ">")
        self._magnitude_threshold_var.set(
            "" if fields.threshold is None else str(fields.threshold)
        )
        self._magnitude_min_var.set("" if fields.minimum is None else str(fields.minimum))
        self._magnitude_max_var.set("" if fields.maximum is None else str(fields.maximum))
        self._magnitude_ma_enabled_var.set(fields.ma_enabled)
        self._magnitude_ma_periods_var.set(
            "" if fields.ma_periods is None else str(fields.ma_periods)
        )
        self._update_card_enabled_state("magnitude")
        self._update_magnitude_mode_visibility()

    def _on_duration_mode_changed(self, *_: object) -> None:
        if self._duration_mode_var.get() == "simple":
            self._duration_min_var.set("")
            self._duration_max_var.set("")
        else:
            self._duration_operator_var.set(">")
            self._duration_steps_var.set("")
        self._update_duration_mode_visibility()

    def _update_duration_mode_visibility(self) -> None:
        if self._duration_mode_var.get() == "simple":
            self._duration_simple_frame.grid()
            self._duration_between_frame.grid_remove()
        else:
            self._duration_simple_frame.grid_remove()
            self._duration_between_frame.grid()

    def _read_duration_fields(self) -> DurationFields:
        mode = cast(DurationMode, self._duration_mode_var.get())
        return DurationFields(
            mode=mode,
            operator=self._duration_operator_var.get() or None,
            steps=_parse_optional_int(self._duration_steps_var.get()),
            min_steps=_parse_optional_int(self._duration_min_var.get()),
            max_steps=_parse_optional_int(self._duration_max_var.get()),
        )

    def _write_duration_fields(self, enabled: bool, fields: DurationFields) -> None:
        self._duration_enabled_var.set(enabled)
        self._duration_mode_var.set(fields.mode)
        self._duration_operator_var.set(fields.operator or ">")
        self._duration_steps_var.set("" if fields.steps is None else str(fields.steps))
        self._duration_min_var.set("" if fields.min_steps is None else str(fields.min_steps))
        self._duration_max_var.set("" if fields.max_steps is None else str(fields.max_steps))
        self._update_card_enabled_state("duration")
        self._update_duration_mode_visibility()

    def _read_timing_fields(self) -> TimingFields:
        return TimingFields(
            first_day_of_year=_parse_optional_int(self._timing_first_day_var.get()),
            last_day_of_year=_parse_optional_int(self._timing_last_day_var.get()),
        )

    def _write_timing_fields(self, enabled: bool, fields: TimingFields) -> None:
        self._timing_enabled_var.set(enabled)
        self._timing_first_day_var.set(
            "" if fields.first_day_of_year is None else str(fields.first_day_of_year)
        )
        self._timing_last_day_var.set(
            "" if fields.last_day_of_year is None else str(fields.last_day_of_year)
        )
        self._update_card_enabled_state("timing")

    def _on_roc_mode_changed(self, *_: object) -> None:
        if self._roc_mode_var.get() == "simple":
            self._roc_min_var.set("")
            self._roc_max_var.set("")
        else:
            self._roc_operator_var.set(">")
            self._roc_threshold_var.set("")
        self._update_roc_mode_visibility()

    def _on_roc_ma_enabled_changed(self, *_: object) -> None:
        if not self._roc_ma_enabled_var.get():
            self._roc_ma_periods_var.set("")
            # Cascade: disabling ma_periods forces off (and clears) the
            # dependent look_back and min optionals too.
            self._roc_look_back_enabled_var.set(False)
        self._update_roc_cascade_state()

    def _on_roc_look_back_enabled_changed(self, *_: object) -> None:
        if not self._roc_look_back_enabled_var.get():
            self._roc_look_back_var.set("")
            self._roc_min_enabled_var.set(False)
        self._update_roc_cascade_state()

    def _on_roc_min_enabled_changed(self, *_: object) -> None:
        if not self._roc_min_enabled_var.get():
            self._roc_min_value_var.set("")
        self._update_roc_cascade_state()

    def _update_roc_cascade_state(self) -> None:
        ma_enabled = self._roc_ma_enabled_var.get()
        self._roc_ma_periods_entry.configure(state="normal" if ma_enabled else "disabled")
        self._roc_look_back_checkbutton.configure(state="normal" if ma_enabled else "disabled")

        look_back_enabled = self._roc_look_back_enabled_var.get()
        look_back_active = ma_enabled and look_back_enabled
        self._roc_look_back_entry.configure(state="normal" if look_back_active else "disabled")
        self._roc_min_checkbutton.configure(
            state="normal" if look_back_active else "disabled"
        )

        min_enabled = self._roc_min_enabled_var.get()
        min_active = look_back_active and min_enabled
        self._roc_min_value_entry.configure(state="normal" if min_active else "disabled")

    def _update_roc_mode_visibility(self) -> None:
        if self._roc_mode_var.get() == "simple":
            self._roc_simple_frame.grid()
            self._roc_between_frame.grid_remove()
        else:
            self._roc_simple_frame.grid_remove()
            self._roc_between_frame.grid()

    def _read_roc_fields(self) -> RateOfChangeFields:
        mode = cast(RateOfChangeMode, self._roc_mode_var.get())
        return RateOfChangeFields(
            mode=mode,
            operator=self._roc_operator_var.get() or None,
            threshold=_parse_optional_float(self._roc_threshold_var.get()),
            minimum=_parse_optional_float(self._roc_min_var.get()),
            maximum=_parse_optional_float(self._roc_max_var.get()),
            ma_enabled=self._roc_ma_enabled_var.get(),
            ma_periods=_parse_optional_int(self._roc_ma_periods_var.get()),
            look_back_enabled=self._roc_look_back_enabled_var.get(),
            look_back=_parse_optional_int(self._roc_look_back_var.get()),
            min_enabled=self._roc_min_enabled_var.get(),
            min_value=_parse_optional_float(self._roc_min_value_var.get()),
        )

    def _write_roc_fields(self, enabled: bool, fields: RateOfChangeFields) -> None:
        self._roc_enabled_var.set(enabled)
        self._roc_mode_var.set(fields.mode)
        self._roc_operator_var.set(fields.operator or ">")
        self._roc_threshold_var.set("" if fields.threshold is None else str(fields.threshold))
        self._roc_min_var.set("" if fields.minimum is None else str(fields.minimum))
        self._roc_max_var.set("" if fields.maximum is None else str(fields.maximum))
        self._roc_ma_enabled_var.set(fields.ma_enabled)
        self._roc_ma_periods_var.set(
            "" if fields.ma_periods is None else str(fields.ma_periods)
        )
        self._roc_look_back_enabled_var.set(fields.look_back_enabled)
        self._roc_look_back_var.set("" if fields.look_back is None else str(fields.look_back))
        self._roc_min_enabled_var.set(fields.min_enabled)
        self._roc_min_value_var.set(
            "" if fields.min_value is None else str(fields.min_value)
        )
        self._update_card_enabled_state("rate_of_change")
        self._update_roc_mode_visibility()
        self._update_roc_cascade_state()

    def _on_freq_nested_enabled_changed(self, *_: object) -> None:
        if not self._freq_nested_enabled_var.get():
            # Probability is only valid as a nested base; force the base
            # mode back to Count (mirrors the mode-switch reset convention)
            # and clear the now-hidden nested pattern's fields.
            if self._freq_vars["base"]["mode"].get() == "probability":
                self._freq_vars["base"]["mode"].set("count")
            self._clear_freq_pattern_fields("nested")
        self._update_freq_nested_visibility()

    def _clear_freq_pattern_fields(self, prefix: str) -> None:
        pattern_vars = self._freq_vars[prefix]
        pattern_vars["operator"].set(">")
        pattern_vars["count_n"].set("")
        pattern_vars["probability"].set("")
        pattern_vars["between_min"].set("")
        pattern_vars["between_max"].set("")
        pattern_vars["out_of_n"].set("")
        pattern_vars["count_by_event"].set(True)

    def _on_freq_mode_changed(self, prefix: str) -> None:
        # Reset the fields belonging to modes being left, matching the
        # Simple<->Between reset convention used by Magnitude/Duration/RoC.
        pattern_vars = self._freq_vars[prefix]
        mode = pattern_vars["mode"].get()
        if mode != "count":
            pattern_vars["count_n"].set("")
        if mode != "between":
            pattern_vars["between_min"].set("")
            pattern_vars["between_max"].set("")
        if mode != "probability":
            pattern_vars["probability"].set("")
        if mode == "probability":
            pattern_vars["out_of_n"].set("")
        self._update_freq_mode_visibility(prefix)

    def _update_freq_mode_visibility(self, prefix: str) -> None:
        mode = self._freq_vars[prefix]["mode"].get()
        frames = self._freq_frames
        if mode == "count":
            frames[f"{prefix}_count"].grid()
            frames[f"{prefix}_between"].grid_remove()
            frames[f"{prefix}_probability"].grid_remove()
        elif mode == "between":
            frames[f"{prefix}_count"].grid_remove()
            frames[f"{prefix}_between"].grid()
            frames[f"{prefix}_probability"].grid_remove()
        else:
            frames[f"{prefix}_count"].grid_remove()
            frames[f"{prefix}_between"].grid_remove()
            frames[f"{prefix}_probability"].grid()

    def _update_freq_nested_visibility(self) -> None:
        nested_enabled = self._freq_nested_enabled_var.get()
        base_probability_radio = cast(
            ttk.Radiobutton, self._freq_frames["base_probability_radio"]
        )
        base_probability_radio.configure(state="normal" if nested_enabled else "disabled")
        if nested_enabled:
            self._freq_nested_label.grid()
            self._freq_frames["nested_wrapper"].grid()
        else:
            self._freq_nested_label.grid_remove()
            self._freq_frames["nested_wrapper"].grid_remove()

    def _read_freq_pattern_fields(self, prefix: str) -> FrequencyPatternFields:
        pattern_vars = self._freq_vars[prefix]
        mode = cast(FrequencyPatternMode, pattern_vars["mode"].get())
        return FrequencyPatternFields(
            mode=mode,
            operator=pattern_vars["operator"].get() or None,
            count_n=_parse_optional_int(pattern_vars["count_n"].get()),
            probability=_parse_optional_float(pattern_vars["probability"].get()),
            between_min=_parse_optional_int(pattern_vars["between_min"].get()),
            between_max=_parse_optional_int(pattern_vars["between_max"].get()),
            out_of_n=_parse_optional_int(pattern_vars["out_of_n"].get()),
            count_by_event=bool(pattern_vars["count_by_event"].get()),
        )

    def _write_freq_pattern_fields(self, prefix: str, fields: FrequencyPatternFields) -> None:
        pattern_vars = self._freq_vars[prefix]
        pattern_vars["mode"].set(fields.mode)
        pattern_vars["operator"].set(fields.operator or ">")
        pattern_vars["count_n"].set("" if fields.count_n is None else str(fields.count_n))
        pattern_vars["probability"].set(
            "" if fields.probability is None else str(fields.probability)
        )
        pattern_vars["between_min"].set(
            "" if fields.between_min is None else str(fields.between_min)
        )
        pattern_vars["between_max"].set(
            "" if fields.between_max is None else str(fields.between_max)
        )
        pattern_vars["out_of_n"].set("" if fields.out_of_n is None else str(fields.out_of_n))
        pattern_vars["count_by_event"].set(fields.count_by_event)
        self._update_freq_mode_visibility(prefix)

    def _read_frequency_fields(self) -> FrequencyFields:
        return FrequencyFields(
            nested_enabled=self._freq_nested_enabled_var.get(),
            base=self._read_freq_pattern_fields("base"),
            nested=self._read_freq_pattern_fields("nested"),
        )

    def _write_frequency_fields(self, enabled: bool, fields: FrequencyFields) -> None:
        self._freq_enabled_var.set(enabled)
        self._freq_nested_enabled_var.set(fields.nested_enabled)
        self._write_freq_pattern_fields("base", fields.base)
        self._write_freq_pattern_fields("nested", fields.nested)
        self._update_card_enabled_state("frequency")
        self._update_freq_nested_visibility()

    def _on_path_or_output_dir_changed(self, *_: object) -> None:
        self._sync_toml_path_default()

    def _sync_toml_path_default(self) -> None:
        suggested = suggest_toml_path(self._output_dir_var.get(), self._path_var.get())
        self._toml_path_var.set(suggested)

    def _update_characteristic_row_states(self) -> None:
        if not self._characteristic_vars:
            # All 5 canonical kinds now have typed cards; the generic
            # freeform pool is empty until hydropattern adds a new kind.
            return
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
        def on_log(channel: LogChannel, line: str) -> None:
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


def is_characteristic_enabled(
    rows: list[CharacteristicRowState], kind: CharacteristicKind
) -> bool:
    return any(row.kind == kind for row in rows)


def enable_characteristic(
    rows: list[CharacteristicRowState],
    kind: CharacteristicKind,
    default_metrics_text: str,
) -> list[CharacteristicRowState]:
    """Append a default row for `kind` at the end of evaluation order, unless
    a row for `kind` already exists (no-op, preserves existing metrics)."""
    if is_characteristic_enabled(rows, kind):
        return list(rows)
    return [*rows, CharacteristicRowState(kind=kind, metrics_text=default_metrics_text)]


def disable_characteristic(
    rows: list[CharacteristicRowState], kind: CharacteristicKind
) -> list[CharacteristicRowState]:
    """Remove the row for `kind`, preserving relative order of the rest."""
    return [row for row in rows if row.kind != kind]


def _parse_optional_float(raw: str) -> float | None:
    text = raw.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_optional_int(raw: str) -> int | None:
    text = raw.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


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
