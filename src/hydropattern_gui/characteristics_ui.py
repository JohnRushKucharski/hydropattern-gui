"""Card-building, per-kind field read/write, and mode-visibility logic for
the 5 typed characteristic cards (timing, magnitude, duration, rate of
change, frequency).

Split out of ui_shell.py in Phase 5 of the TypedCard refactor (see
HANDOFF.md Task 1): that file had grown to ~1878 lines, and the bulk of
that growth was this per-kind card-construction/field-marshalling code.
Implemented as a mixin (CharacteristicsUiMixin) rather than a composed
helper object, because the widget constructors, event-handler traces, and
the generic reorder/enable-state helpers that remain in HydropatternGuiApp
all read and write the same self._X_..._var / self._cards / self._mode_*
attributes directly -- a mixin keeps that single shared `self` without
rewriting every cross-reference to `self._characteristics.X`.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field
from tkinter import ttk
from typing import cast

from hydropattern_gui.gui_form import (
    CharacteristicKind,
    DurationFields,
    DurationMode,
    FrequencyFields,
    FrequencyPatternFields,
    FrequencyPatternMode,
    MagnitudeFields,
    MagnitudeMode,
    RateOfChangeFields,
    RateOfChangeMode,
    TimingFields,
)


@dataclass
class TypedCard:
    """Container wrapping one typed characteristic card's widgets/variables
    under a single lookup, introduced additively (Phase 1 of the TypedCard
    refactor -- see HANDOFF.md Task 1) as a step toward collapsing the 5
    near-duplicated per-kind attribute families in HydropatternGuiApp.

    `mode_var` is None for kinds without a single simple/between mode
    picker (timing has no mode at all; frequency has independent
    base/nested pattern modes instead, tracked in `field_vars` under
    "base_mode"/"nested_mode"). `field_vars` maps each Fields dataclass
    attribute name (or, for frequency, "base_"/"nested_"-prefixed pattern
    attribute names) to its backing Tk variable.
    """

    enabled_var: tk.BooleanVar
    mode_var: tk.StringVar | None
    field_vars: dict[str, tk.Variable] = field(default_factory=dict)
    body: ttk.Frame | None = None
    up_button: ttk.Button | None = None
    down_button: ttk.Button | None = None


def _parse_optional_float(raw: str) -> float | None:
    text = raw.strip()
    if not text:
        return None
    return float(text)


def _parse_optional_int(raw: str) -> int | None:
    text = raw.strip()
    if not text:
        return None
    return int(text)


class CharacteristicsUiMixin:
    """Builds the 5 typed characteristic cards' widgets and provides their
    per-kind field read/write and mode-visibility logic.

    Must be mixed into a class that sets up the Tk variables this mixin
    reads (see HydropatternGuiApp.__init__) and provides the generic
    reorder/enable-state helpers this mixin calls into
    (`_move_row`, `_update_card_enabled_state`).
    """

    _cards: dict[str, TypedCard]
    _mode_vars: dict[str, tk.StringVar]
    _mode_frames: dict[str, tuple[ttk.Frame, ttk.Frame]]
    _freq_vars: dict[str, dict[str, tk.Variable]]
    _data_units_var: tk.StringVar
    _timing_enabled_var: tk.BooleanVar
    _timing_first_day_var: tk.StringVar
    _timing_last_day_var: tk.StringVar
    _magnitude_enabled_var: tk.BooleanVar
    _magnitude_mode_var: tk.StringVar
    _magnitude_operator_var: tk.StringVar
    _magnitude_threshold_var: tk.StringVar
    _magnitude_min_var: tk.StringVar
    _magnitude_max_var: tk.StringVar
    _magnitude_ma_enabled_var: tk.BooleanVar
    _magnitude_ma_periods_var: tk.StringVar
    _duration_enabled_var: tk.BooleanVar
    _duration_mode_var: tk.StringVar
    _duration_operator_var: tk.StringVar
    _duration_steps_var: tk.StringVar
    _duration_min_var: tk.StringVar
    _duration_max_var: tk.StringVar
    _roc_enabled_var: tk.BooleanVar
    _roc_mode_var: tk.StringVar
    _roc_operator_var: tk.StringVar
    _roc_threshold_var: tk.StringVar
    _roc_min_var: tk.StringVar
    _roc_max_var: tk.StringVar
    _roc_ma_enabled_var: tk.BooleanVar
    _roc_ma_periods_var: tk.StringVar
    _roc_look_back_enabled_var: tk.BooleanVar
    _roc_look_back_var: tk.StringVar
    _roc_min_enabled_var: tk.BooleanVar
    _roc_min_value_var: tk.StringVar
    _freq_enabled_var: tk.BooleanVar
    _freq_nested_enabled_var: tk.BooleanVar

    def _move_row(self, kind: CharacteristicKind, direction: int) -> None: ...

    def _update_card_enabled_state(self, kind: str) -> None: ...

    def _build_typed_cards(self) -> dict[str, TypedCard]:
        """Phase 1 (additive only) of the TypedCard refactor: wrap the
        already-built per-kind widgets/variables into one TypedCard per
        kind, without changing any existing attribute or behavior. See
        HANDOFF.md Task 1 for the full multi-phase plan; _read_X_fields/
        _write_X_fields still go through the legacy self._X_..._var
        attributes directly until Phase 2 migrates them to read through
        self._cards instead."""
        return {
            "timing": TypedCard(
                enabled_var=self._timing_enabled_var,
                mode_var=None,
                field_vars={
                    "first_day_of_year": self._timing_first_day_var,
                    "last_day_of_year": self._timing_last_day_var,
                },
                body=self._timing_body,
                up_button=self._timing_up_button,
                down_button=self._timing_down_button,
            ),
            "magnitude": TypedCard(
                enabled_var=self._magnitude_enabled_var,
                mode_var=self._magnitude_mode_var,
                field_vars={
                    "operator": self._magnitude_operator_var,
                    "threshold": self._magnitude_threshold_var,
                    "minimum": self._magnitude_min_var,
                    "maximum": self._magnitude_max_var,
                    "ma_enabled": self._magnitude_ma_enabled_var,
                    "ma_periods": self._magnitude_ma_periods_var,
                },
                body=self._magnitude_body,
                up_button=self._magnitude_up_button,
                down_button=self._magnitude_down_button,
            ),
            "duration": TypedCard(
                enabled_var=self._duration_enabled_var,
                mode_var=self._duration_mode_var,
                field_vars={
                    "operator": self._duration_operator_var,
                    "steps": self._duration_steps_var,
                    "min_steps": self._duration_min_var,
                    "max_steps": self._duration_max_var,
                },
                body=self._duration_body,
                up_button=self._duration_up_button,
                down_button=self._duration_down_button,
            ),
            "rate_of_change": TypedCard(
                enabled_var=self._roc_enabled_var,
                mode_var=self._roc_mode_var,
                field_vars={
                    "operator": self._roc_operator_var,
                    "threshold": self._roc_threshold_var,
                    "minimum": self._roc_min_var,
                    "maximum": self._roc_max_var,
                    "ma_enabled": self._roc_ma_enabled_var,
                    "ma_periods": self._roc_ma_periods_var,
                    "look_back_enabled": self._roc_look_back_enabled_var,
                    "look_back": self._roc_look_back_var,
                    "min_enabled": self._roc_min_enabled_var,
                    "min_value": self._roc_min_value_var,
                },
                body=self._roc_body,
                up_button=self._roc_up_button,
                down_button=self._roc_down_button,
            ),
            "frequency": TypedCard(
                enabled_var=self._freq_enabled_var,
                mode_var=None,
                field_vars={
                    "nested_enabled": self._freq_nested_enabled_var,
                    **{
                        f"{prefix}_{name}": var
                        for prefix in ("base", "nested")
                        for name, var in self._freq_vars[prefix].items()
                    },
                },
                body=self._freq_body,
                up_button=self._freq_up_button,
                down_button=self._freq_down_button,
            ),
        }

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
        self._timing_order_label = ttk.Label(header_row, text="")
        self._timing_order_label.pack(side=tk.LEFT, padx=(8, 0))

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
        self._magnitude_order_label = ttk.Label(header_row, text="")
        self._magnitude_order_label.pack(side=tk.LEFT, padx=(8, 0))

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
        self._mode_frames["magnitude"] = (
            self._magnitude_simple_frame,
            self._magnitude_between_frame,
        )

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
        self._update_mode_visibility("magnitude")
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
        self._duration_order_label = ttk.Label(header_row, text="")
        self._duration_order_label.pack(side=tk.LEFT, padx=(8, 0))

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
        self._mode_frames["duration"] = (
            self._duration_simple_frame,
            self._duration_between_frame,
        )

        self._update_mode_visibility("duration")
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
            header_row,
            text="\u25b2",
            width=2,
            command=lambda: self._move_row("rate_of_change", -1),
        )
        self._roc_up_button.pack(side=tk.LEFT, padx=(8, 0))
        self._roc_down_button = ttk.Button(
            header_row,
            text="\u25bc",
            width=2,
            command=lambda: self._move_row("rate_of_change", 1),
        )
        self._roc_down_button.pack(side=tk.LEFT, padx=(2, 0))
        self._roc_order_label = ttk.Label(header_row, text="")
        self._roc_order_label.pack(side=tk.LEFT, padx=(8, 0))

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
        self._mode_frames["rate_of_change"] = (self._roc_simple_frame, self._roc_between_frame)

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

        self._update_mode_visibility("rate_of_change")
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
        self._freq_order_label = ttk.Label(header_row, text="")
        self._freq_order_label.pack(side=tk.LEFT, padx=(8, 0))

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

    def _update_mode_visibility(self, kind: str) -> None:
        """Generic replacement for the near-identical
        _update_magnitude_mode_visibility / _update_duration_mode_visibility
        / _update_roc_mode_visibility methods -- all 3 share the identical
        Simple/Between mode-visibility shape (see HANDOFF.md Task 1 Phase
        3). Rate of Change's optional-param cascade (_update_roc_cascade_
        state) and Frequency's nested-pattern-editor visibility
        (_update_freq_mode_visibility / _update_freq_nested_visibility) are
        genuinely shaped differently and stay bespoke."""
        mode_var = self._mode_vars[kind]
        simple_frame, between_frame = self._mode_frames[kind]
        if mode_var.get() == "simple":
            simple_frame.grid()
            between_frame.grid_remove()
        else:
            simple_frame.grid_remove()
            between_frame.grid()

    def _update_magnitude_unit_labels(self) -> None:
        unit_text = f"({self._data_units_var.get().strip() or 'data units'})"
        self._magnitude_threshold_unit_label.configure(text=unit_text)
        self._magnitude_min_unit_label.configure(text=unit_text)
        self._magnitude_max_unit_label.configure(text=unit_text)

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
        self._update_mode_visibility("magnitude")

    def _on_magnitude_ma_enabled_changed(self, *_: object) -> None:
        state = "normal" if self._magnitude_ma_enabled_var.get() else "disabled"
        self._magnitude_ma_periods_entry.configure(state=state)
        if state == "disabled":
            self._magnitude_ma_periods_var.set("")

    def _on_data_units_changed(self, *_: object) -> None:
        self._update_magnitude_unit_labels()

    def _read_magnitude_fields(self) -> MagnitudeFields:
        card = self._cards["magnitude"]
        field_vars = card.field_vars
        mode = cast(MagnitudeMode, cast(tk.StringVar, card.mode_var).get())
        return MagnitudeFields(
            mode=mode,
            operator=field_vars["operator"].get() or None,
            threshold=_parse_optional_float(field_vars["threshold"].get()),
            minimum=_parse_optional_float(field_vars["minimum"].get()),
            maximum=_parse_optional_float(field_vars["maximum"].get()),
            ma_enabled=field_vars["ma_enabled"].get(),
            ma_periods=_parse_optional_int(field_vars["ma_periods"].get()),
        )

    def _write_magnitude_fields(self, enabled: bool, fields: MagnitudeFields) -> None:
        card = self._cards["magnitude"]
        field_vars = card.field_vars
        card.enabled_var.set(enabled)
        cast(tk.StringVar, card.mode_var).set(fields.mode)
        field_vars["operator"].set(fields.operator or ">")
        field_vars["threshold"].set("" if fields.threshold is None else str(fields.threshold))
        field_vars["minimum"].set("" if fields.minimum is None else str(fields.minimum))
        field_vars["maximum"].set("" if fields.maximum is None else str(fields.maximum))
        field_vars["ma_enabled"].set(fields.ma_enabled)
        field_vars["ma_periods"].set(
            "" if fields.ma_periods is None else str(fields.ma_periods)
        )
        self._update_card_enabled_state("magnitude")
        self._update_mode_visibility("magnitude")

    def _on_duration_mode_changed(self, *_: object) -> None:
        if self._duration_mode_var.get() == "simple":
            self._duration_min_var.set("")
            self._duration_max_var.set("")
        else:
            self._duration_operator_var.set(">")
            self._duration_steps_var.set("")
        self._update_mode_visibility("duration")

    def _read_duration_fields(self) -> DurationFields:
        card = self._cards["duration"]
        field_vars = card.field_vars
        mode = cast(DurationMode, cast(tk.StringVar, card.mode_var).get())
        return DurationFields(
            mode=mode,
            operator=field_vars["operator"].get() or None,
            steps=_parse_optional_int(field_vars["steps"].get()),
            min_steps=_parse_optional_int(field_vars["min_steps"].get()),
            max_steps=_parse_optional_int(field_vars["max_steps"].get()),
        )

    def _write_duration_fields(self, enabled: bool, fields: DurationFields) -> None:
        card = self._cards["duration"]
        field_vars = card.field_vars
        card.enabled_var.set(enabled)
        cast(tk.StringVar, card.mode_var).set(fields.mode)
        field_vars["operator"].set(fields.operator or ">")
        field_vars["steps"].set("" if fields.steps is None else str(fields.steps))
        field_vars["min_steps"].set("" if fields.min_steps is None else str(fields.min_steps))
        field_vars["max_steps"].set("" if fields.max_steps is None else str(fields.max_steps))
        self._update_card_enabled_state("duration")
        self._update_mode_visibility("duration")

    def _read_timing_fields(self) -> TimingFields:
        field_vars = self._cards["timing"].field_vars
        return TimingFields(
            first_day_of_year=_parse_optional_int(field_vars["first_day_of_year"].get()),
            last_day_of_year=_parse_optional_int(field_vars["last_day_of_year"].get()),
        )

    def _write_timing_fields(self, enabled: bool, fields: TimingFields) -> None:
        card = self._cards["timing"]
        card.enabled_var.set(enabled)
        card.field_vars["first_day_of_year"].set(
            "" if fields.first_day_of_year is None else str(fields.first_day_of_year)
        )
        card.field_vars["last_day_of_year"].set(
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
        self._update_mode_visibility("rate_of_change")

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

    def _read_roc_fields(self) -> RateOfChangeFields:
        card = self._cards["rate_of_change"]
        field_vars = card.field_vars
        mode = cast(RateOfChangeMode, cast(tk.StringVar, card.mode_var).get())
        return RateOfChangeFields(
            mode=mode,
            operator=field_vars["operator"].get() or None,
            threshold=_parse_optional_float(field_vars["threshold"].get()),
            minimum=_parse_optional_float(field_vars["minimum"].get()),
            maximum=_parse_optional_float(field_vars["maximum"].get()),
            ma_enabled=field_vars["ma_enabled"].get(),
            ma_periods=_parse_optional_int(field_vars["ma_periods"].get()),
            look_back_enabled=field_vars["look_back_enabled"].get(),
            look_back=_parse_optional_int(field_vars["look_back"].get()),
            min_enabled=field_vars["min_enabled"].get(),
            min_value=_parse_optional_float(field_vars["min_value"].get()),
        )

    def _write_roc_fields(self, enabled: bool, fields: RateOfChangeFields) -> None:
        card = self._cards["rate_of_change"]
        field_vars = card.field_vars
        card.enabled_var.set(enabled)
        cast(tk.StringVar, card.mode_var).set(fields.mode)
        field_vars["operator"].set(fields.operator or ">")
        field_vars["threshold"].set("" if fields.threshold is None else str(fields.threshold))
        field_vars["minimum"].set("" if fields.minimum is None else str(fields.minimum))
        field_vars["maximum"].set("" if fields.maximum is None else str(fields.maximum))
        field_vars["ma_enabled"].set(fields.ma_enabled)
        field_vars["ma_periods"].set(
            "" if fields.ma_periods is None else str(fields.ma_periods)
        )
        field_vars["look_back_enabled"].set(fields.look_back_enabled)
        field_vars["look_back"].set("" if fields.look_back is None else str(fields.look_back))
        field_vars["min_enabled"].set(fields.min_enabled)
        field_vars["min_value"].set(
            "" if fields.min_value is None else str(fields.min_value)
        )
        self._update_card_enabled_state("rate_of_change")
        self._update_mode_visibility("rate_of_change")
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
        field_vars = self._cards["frequency"].field_vars
        mode = cast(FrequencyPatternMode, field_vars[f"{prefix}_mode"].get())
        return FrequencyPatternFields(
            mode=mode,
            operator=field_vars[f"{prefix}_operator"].get() or None,
            count_n=_parse_optional_int(field_vars[f"{prefix}_count_n"].get()),
            probability=_parse_optional_float(field_vars[f"{prefix}_probability"].get()),
            between_min=_parse_optional_int(field_vars[f"{prefix}_between_min"].get()),
            between_max=_parse_optional_int(field_vars[f"{prefix}_between_max"].get()),
            out_of_n=_parse_optional_int(field_vars[f"{prefix}_out_of_n"].get()),
            count_by_event=bool(field_vars[f"{prefix}_count_by_event"].get()),
        )

    def _write_freq_pattern_fields(self, prefix: str, fields: FrequencyPatternFields) -> None:
        field_vars = self._cards["frequency"].field_vars
        field_vars[f"{prefix}_mode"].set(fields.mode)
        field_vars[f"{prefix}_operator"].set(fields.operator or ">")
        field_vars[f"{prefix}_count_n"].set(
            "" if fields.count_n is None else str(fields.count_n)
        )
        field_vars[f"{prefix}_probability"].set(
            "" if fields.probability is None else str(fields.probability)
        )
        field_vars[f"{prefix}_between_min"].set(
            "" if fields.between_min is None else str(fields.between_min)
        )
        field_vars[f"{prefix}_between_max"].set(
            "" if fields.between_max is None else str(fields.between_max)
        )
        field_vars[f"{prefix}_out_of_n"].set(
            "" if fields.out_of_n is None else str(fields.out_of_n)
        )
        field_vars[f"{prefix}_count_by_event"].set(fields.count_by_event)
        self._update_freq_mode_visibility(prefix)

    def _read_frequency_fields(self) -> FrequencyFields:
        return FrequencyFields(
            nested_enabled=self._cards["frequency"].field_vars["nested_enabled"].get(),
            base=self._read_freq_pattern_fields("base"),
            nested=self._read_freq_pattern_fields("nested"),
        )

    def _write_frequency_fields(self, enabled: bool, fields: FrequencyFields) -> None:
        card = self._cards["frequency"]
        card.enabled_var.set(enabled)
        card.field_vars["nested_enabled"].set(fields.nested_enabled)
        self._write_freq_pattern_fields("base", fields.base)
        self._write_freq_pattern_fields("nested", fields.nested)
        self._update_card_enabled_state("frequency")
        self._update_freq_nested_visibility()
