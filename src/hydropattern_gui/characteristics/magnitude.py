"""Magnitude characteristic card: typed field state, metrics_text
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

MagnitudeMode = Literal["simple", "between"]


@dataclass(frozen=True)
class MagnitudeFields:
    """Typed field state for the Magnitude characteristic card.

    Mirrors the two shapes accepted by hydropattern's magnitude metrics:
    [operator, threshold, (opt)ma_periods] (mode="simple") or
    [minimum, maximum, (opt)ma_periods] (mode="between").
    """

    mode: MagnitudeMode
    operator: str | None
    threshold: float | None
    minimum: float | None
    maximum: float | None
    ma_enabled: bool
    ma_periods: int | None


def magnitude_fields_to_metrics(fields: MagnitudeFields) -> str:
    """Convert typed Magnitude card fields into a metrics_text list literal."""
    field_errors: dict[str, str] = {}
    values: list[object]
    if fields.mode == "simple":
        if fields.operator is None:
            field_errors["operator"] = "required"
        if fields.threshold is None:
            field_errors["threshold"] = "required"
        values = [fields.operator, fields.threshold]
    else:
        if fields.minimum is None:
            field_errors["minimum"] = "required"
        if fields.maximum is None:
            field_errors["maximum"] = "required"
        values = [fields.minimum, fields.maximum]

    if fields.ma_enabled and fields.ma_periods is None:
        field_errors["ma_periods"] = "required when moving average is enabled"

    if field_errors:
        raise FormValidationError(field_errors)

    if fields.ma_enabled:
        values.append(fields.ma_periods)
    return _metrics_to_text(values)


def magnitude_metrics_from_text(metrics_text: str) -> MagnitudeFields:
    """Parse a metrics_text list literal into typed Magnitude card fields."""
    try:
        parsed = ast.literal_eval(metrics_text.strip())
    except (ValueError, SyntaxError) as exc:
        raise FormValidationError(
            {"metrics": "must be valid Python/TOML-like list literal"}
        ) from exc
    if not isinstance(parsed, list) or len(parsed) not in (2, 3):
        raise FormValidationError({"metrics": "must parse to a 2 or 3 item list"})

    ma_enabled = len(parsed) == 3
    ma_periods = int(parsed[2]) if ma_enabled else None

    if isinstance(parsed[0], str):
        return MagnitudeFields(
            mode="simple",
            operator=parsed[0],
            threshold=float(parsed[1]),
            minimum=None,
            maximum=None,
            ma_enabled=ma_enabled,
            ma_periods=ma_periods,
        )
    return MagnitudeFields(
        mode="between",
        operator=None,
        threshold=None,
        minimum=float(parsed[0]),
        maximum=float(parsed[1]),
        ma_enabled=ma_enabled,
        ma_periods=ma_periods,
    )


_BLANK_MAGNITUDE_FIELDS = MagnitudeFields(
    mode="simple",
    operator=None,
    threshold=None,
    minimum=None,
    maximum=None,
    ma_enabled=False,
    ma_periods=None,
)


def sync_magnitude_row(
    rows: list[CharacteristicRowState],
    enabled: bool,
    fields: MagnitudeFields,
    insert_at: int | None = None,
) -> list[CharacteristicRowState]:
    """Build the characteristic_rows list with the Magnitude row reflecting
    typed card state: absent when disabled, present with metrics_text derived
    from `fields` when enabled. Preserves the position/order of all other
    rows, and the Magnitude row's own position when it already exists.

    When Magnitude is being newly added (not already present in `rows`),
    `insert_at` picks where it lands among the other rows (clamped to the
    valid range); defaults to appending at the end.
    """
    without_magnitude = [row for row in rows if row.kind != "magnitude"]
    if not enabled:
        return without_magnitude

    try:
        metrics_text = magnitude_fields_to_metrics(fields)
    except FormValidationError:
        # Incomplete/invalid typed input while the user is still editing;
        # fall back to an empty metrics_text so downstream config validation
        # reports the standard "required" field error instead of silently
        # dropping the row.
        metrics_text = ""

    new_row = CharacteristicRowState(kind="magnitude", metrics_text=metrics_text)
    existing_index = next(
        (index for index, row in enumerate(rows) if row.kind == "magnitude"), None
    )
    if existing_index is not None:
        result = list(without_magnitude)
        result.insert(existing_index, new_row)
        return result

    index = len(without_magnitude) if insert_at is None else max(
        0, min(insert_at, len(without_magnitude))
    )
    result = list(without_magnitude)
    result.insert(index, new_row)
    return result


def magnitude_insertion_offset(rows: list[CharacteristicRowState]) -> int:
    """Number of non-Magnitude rows preceding the Magnitude row, used to
    remember Magnitude's reorder position; 0 when Magnitude is absent."""
    offset = 0
    for row in rows:
        if row.kind == "magnitude":
            return offset
        offset += 1
    return 0


def extract_magnitude_state(
    rows: list[CharacteristicRowState],
) -> tuple[bool, MagnitudeFields]:
    """Inverse of sync_magnitude_row: find the Magnitude row (if any) and
    parse it into typed card fields, defaulting to a disabled, blank Simple
    form when Magnitude is not present or its metrics_text can't be parsed
    (e.g. mid-edit)."""
    row = next((row for row in rows if row.kind == "magnitude"), None)
    if row is None:
        return False, _BLANK_MAGNITUDE_FIELDS
    try:
        return True, magnitude_metrics_from_text(row.metrics_text)
    except FormValidationError:
        return True, _BLANK_MAGNITUDE_FIELDS


