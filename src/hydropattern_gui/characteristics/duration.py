"""Duration characteristic card: typed field state, metrics_text
conversion, and characteristic_rows sync helpers."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Literal

from hydropattern_gui.characteristics._shared import (
    CharacteristicRowState,
    FormValidationError,
    _metrics_to_text,
)

DurationMode = Literal["simple", "between"]


@dataclass(frozen=True)
class DurationFields:
    """Typed field state for the Duration characteristic card.

    Mirrors the two shapes accepted by hydropattern's duration metrics:
    [operator, steps] (mode="simple") or [min_steps, max_steps]
    (mode="between"); both integers >= 1, no optional moving average.
    """

    mode: DurationMode
    operator: str | None
    steps: int | None
    min_steps: int | None
    max_steps: int | None


_BLANK_DURATION_FIELDS = DurationFields(
    mode="simple", operator=None, steps=None, min_steps=None, max_steps=None
)


def duration_fields_to_metrics(fields: DurationFields) -> str:
    """Convert typed Duration card fields into a metrics_text list literal."""
    field_errors: dict[str, str] = {}
    values: list[object]
    if fields.mode == "simple":
        if fields.operator is None:
            field_errors["operator"] = "required"
        if fields.steps is None:
            field_errors["steps"] = "required"
        values = [fields.operator, fields.steps]
    else:
        if fields.min_steps is None:
            field_errors["min_steps"] = "required"
        if fields.max_steps is None:
            field_errors["max_steps"] = "required"
        values = [fields.min_steps, fields.max_steps]

    if field_errors:
        raise FormValidationError(field_errors)
    return _metrics_to_text(values)


def duration_metrics_from_text(metrics_text: str) -> DurationFields:
    """Parse a metrics_text list literal into typed Duration card fields."""
    try:
        parsed = ast.literal_eval(metrics_text.strip())
    except (ValueError, SyntaxError) as exc:
        raise FormValidationError(
            {"metrics": "must be valid Python/TOML-like list literal"}
        ) from exc
    if not isinstance(parsed, list) or len(parsed) != 2:
        raise FormValidationError({"metrics": "must parse to a 2 item list"})

    if isinstance(parsed[0], str):
        return DurationFields(
            mode="simple",
            operator=parsed[0],
            steps=int(parsed[1]),
            min_steps=None,
            max_steps=None,
        )
    return DurationFields(
        mode="between",
        operator=None,
        steps=None,
        min_steps=int(parsed[0]),
        max_steps=int(parsed[1]),
    )


def sync_duration_row(
    rows: list[CharacteristicRowState],
    enabled: bool,
    fields: DurationFields,
    insert_at: int | None = None,
) -> list[CharacteristicRowState]:
    """Duration analogue of sync_magnitude_row (same insert/preserve rules)."""
    without_duration = [row for row in rows if row.kind != "duration"]
    if not enabled:
        return without_duration

    try:
        metrics_text = duration_fields_to_metrics(fields)
    except FormValidationError:
        metrics_text = ""

    new_row = CharacteristicRowState(kind="duration", metrics_text=metrics_text)
    existing_index = next(
        (index for index, row in enumerate(rows) if row.kind == "duration"), None
    )
    if existing_index is not None:
        result = list(without_duration)
        result.insert(existing_index, new_row)
        return result

    index = len(without_duration) if insert_at is None else max(
        0, min(insert_at, len(without_duration))
    )
    result = list(without_duration)
    result.insert(index, new_row)
    return result


def duration_insertion_offset(rows: list[CharacteristicRowState]) -> int:
    """Number of non-Duration rows preceding the Duration row; 0 when absent."""
    offset = 0
    for row in rows:
        if row.kind == "duration":
            return offset
        offset += 1
    return 0


def extract_duration_state(
    rows: list[CharacteristicRowState],
) -> tuple[bool, DurationFields]:
    """Inverse of sync_duration_row."""
    row = next((row for row in rows if row.kind == "duration"), None)
    if row is None:
        return False, _BLANK_DURATION_FIELDS
    try:
        return True, duration_metrics_from_text(row.metrics_text)
    except FormValidationError:
        return True, _BLANK_DURATION_FIELDS


