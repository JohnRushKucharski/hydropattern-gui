"""Rate of Change characteristic card: typed field state, metrics_text
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

RateOfChangeMode = Literal["simple", "between"]


@dataclass(frozen=True)
class RateOfChangeFields:
    """Typed field state for the Rate of Change characteristic card.

    Mirrors hydropattern's [symbol, value, (opt)ma_periods, (opt)look_back,
    (opt)min] / [lower, upper, ...] shape. The three optional params are
    strictly positional/cascading in hydropattern (no null placeholder):
    look_back can't be set without ma_periods, min can't be set without
    look_back. That cascade rule is enforced here too, not just in the
    widget layer, so this stays independently testable/correct.
    """

    mode: RateOfChangeMode
    operator: str | None
    threshold: float | None
    minimum: float | None
    maximum: float | None
    ma_enabled: bool
    ma_periods: int | None
    look_back_enabled: bool
    look_back: int | None
    min_enabled: bool
    min_value: float | None


_BLANK_RATE_OF_CHANGE_FIELDS = RateOfChangeFields(
    mode="simple",
    operator=None,
    threshold=None,
    minimum=None,
    maximum=None,
    ma_enabled=False,
    ma_periods=None,
    look_back_enabled=False,
    look_back=None,
    min_enabled=False,
    min_value=None,
)


def rate_of_change_fields_to_metrics(fields: RateOfChangeFields) -> str:
    """Convert typed Rate of Change card fields into a metrics_text list
    literal, enforcing the cascade rule (look_back requires ma_enabled,
    min requires look_back_enabled)."""
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

    if fields.look_back_enabled and not fields.ma_enabled:
        field_errors["look_back"] = "requires ma_periods to be enabled first"
    if fields.min_enabled and not fields.look_back_enabled:
        field_errors["min_value"] = "requires look_back to be enabled first"

    if fields.ma_enabled:
        if fields.ma_periods is None:
            field_errors["ma_periods"] = "required"
        values.append(fields.ma_periods)
    if fields.look_back_enabled:
        if fields.look_back is None:
            field_errors["look_back"] = "required"
        values.append(fields.look_back)
    if fields.min_enabled:
        if fields.min_value is None:
            field_errors["min_value"] = "required"
        values.append(fields.min_value)

    if field_errors:
        raise FormValidationError(field_errors)
    return _metrics_to_text(values)


def rate_of_change_metrics_from_text(metrics_text: str) -> RateOfChangeFields:
    """Parse a metrics_text list literal into typed Rate of Change card
    fields."""
    try:
        parsed = ast.literal_eval(metrics_text.strip())
    except (ValueError, SyntaxError) as exc:
        raise FormValidationError(
            {"metrics": "must be valid Python/TOML-like list literal"}
        ) from exc
    if not isinstance(parsed, list) or len(parsed) not in (2, 3, 4, 5):
        raise FormValidationError({"metrics": "must parse to a 2-5 item list"})

    ma_enabled = len(parsed) > 2
    look_back_enabled = len(parsed) > 3
    min_enabled = len(parsed) > 4
    ma_periods = int(parsed[2]) if ma_enabled else None
    look_back = int(parsed[3]) if look_back_enabled else None
    min_value = float(parsed[4]) if min_enabled else None

    if isinstance(parsed[0], str):
        return RateOfChangeFields(
            mode="simple",
            operator=parsed[0],
            threshold=float(parsed[1]),
            minimum=None,
            maximum=None,
            ma_enabled=ma_enabled,
            ma_periods=ma_periods,
            look_back_enabled=look_back_enabled,
            look_back=look_back,
            min_enabled=min_enabled,
            min_value=min_value,
        )
    return RateOfChangeFields(
        mode="between",
        operator=None,
        threshold=None,
        minimum=float(parsed[0]),
        maximum=float(parsed[1]),
        ma_enabled=ma_enabled,
        ma_periods=ma_periods,
        look_back_enabled=look_back_enabled,
        look_back=look_back,
        min_enabled=min_enabled,
        min_value=min_value,
    )


def sync_rate_of_change_row(
    rows: list[CharacteristicRowState],
    enabled: bool,
    fields: RateOfChangeFields,
    insert_at: int | None = None,
) -> list[CharacteristicRowState]:
    """Rate of Change analogue of sync_duration_row (same insert/preserve
    rules)."""
    without_roc = [row for row in rows if row.kind != "rate_of_change"]
    if not enabled:
        return without_roc

    try:
        metrics_text = rate_of_change_fields_to_metrics(fields)
    except FormValidationError:
        metrics_text = ""

    new_row = CharacteristicRowState(kind="rate_of_change", metrics_text=metrics_text)
    existing_index = next(
        (index for index, row in enumerate(rows) if row.kind == "rate_of_change"), None
    )
    if existing_index is not None:
        result = list(without_roc)
        result.insert(existing_index, new_row)
        return result

    index = len(without_roc) if insert_at is None else max(
        0, min(insert_at, len(without_roc))
    )
    result = list(without_roc)
    result.insert(index, new_row)
    return result


def rate_of_change_insertion_offset(rows: list[CharacteristicRowState]) -> int:
    """Number of non-Rate-of-Change rows preceding it; 0 when absent."""
    offset = 0
    for row in rows:
        if row.kind == "rate_of_change":
            return offset
        offset += 1
    return 0


def extract_rate_of_change_state(
    rows: list[CharacteristicRowState],
) -> tuple[bool, RateOfChangeFields]:
    """Inverse of sync_rate_of_change_row."""
    row = next((row for row in rows if row.kind == "rate_of_change"), None)
    if row is None:
        return False, _BLANK_RATE_OF_CHANGE_FIELDS
    try:
        return True, rate_of_change_metrics_from_text(row.metrics_text)
    except FormValidationError:
        return True, _BLANK_RATE_OF_CHANGE_FIELDS


