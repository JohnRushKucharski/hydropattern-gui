"""Timing characteristic card: typed field state, metrics_text
conversion, and characteristic_rows sync helpers."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from hydropattern_gui.characteristics._shared import (
    CharacteristicRowState,
    FormValidationError,
    _metrics_to_text,
)


@dataclass(frozen=True)
class TimingFields:
    """Typed field state for the Timing characteristic card.

    hydropattern's timing metrics are always [first_doy, last_doy] (both
    ints 1-366) -- no operator, no Simple/Between mode.
    """

    first_day_of_year: int | None
    last_day_of_year: int | None


_BLANK_TIMING_FIELDS = TimingFields(first_day_of_year=None, last_day_of_year=None)


def timing_fields_to_metrics(fields: TimingFields) -> str:
    """Convert typed Timing card fields into a metrics_text list literal."""
    field_errors: dict[str, str] = {}
    if fields.first_day_of_year is None:
        field_errors["first_day_of_year"] = "required"
    if fields.last_day_of_year is None:
        field_errors["last_day_of_year"] = "required"
    if field_errors:
        raise FormValidationError(field_errors)
    return _metrics_to_text([fields.first_day_of_year, fields.last_day_of_year])


def timing_metrics_from_text(metrics_text: str) -> TimingFields:
    """Parse a metrics_text list literal into typed Timing card fields."""
    try:
        parsed = ast.literal_eval(metrics_text.strip())
    except (ValueError, SyntaxError) as exc:
        raise FormValidationError(
            {"metrics": "must be valid Python/TOML-like list literal"}
        ) from exc
    if not isinstance(parsed, list) or len(parsed) != 2:
        raise FormValidationError({"metrics": "must parse to a 2 item list"})
    return TimingFields(first_day_of_year=int(parsed[0]), last_day_of_year=int(parsed[1]))


def sync_timing_row(
    rows: list[CharacteristicRowState],
    enabled: bool,
    fields: TimingFields,
    insert_at: int | None = None,
) -> list[CharacteristicRowState]:
    """Timing analogue of sync_duration_row (same insert/preserve rules)."""
    without_timing = [row for row in rows if row.kind != "timing"]
    if not enabled:
        return without_timing

    try:
        metrics_text = timing_fields_to_metrics(fields)
    except FormValidationError:
        metrics_text = ""

    new_row = CharacteristicRowState(kind="timing", metrics_text=metrics_text)
    existing_index = next(
        (index for index, row in enumerate(rows) if row.kind == "timing"), None
    )
    if existing_index is not None:
        result = list(without_timing)
        result.insert(existing_index, new_row)
        return result

    index = len(without_timing) if insert_at is None else max(
        0, min(insert_at, len(without_timing))
    )
    result = list(without_timing)
    result.insert(index, new_row)
    return result


def timing_insertion_offset(rows: list[CharacteristicRowState]) -> int:
    """Number of non-Timing rows preceding the Timing row; 0 when absent."""
    offset = 0
    for row in rows:
        if row.kind == "timing":
            return offset
        offset += 1
    return 0


def extract_timing_state(
    rows: list[CharacteristicRowState],
) -> tuple[bool, TimingFields]:
    """Inverse of sync_timing_row."""
    row = next((row for row in rows if row.kind == "timing"), None)
    if row is None:
        return False, _BLANK_TIMING_FIELDS
    try:
        return True, timing_metrics_from_text(row.metrics_text)
    except FormValidationError:
        return True, _BLANK_TIMING_FIELDS


