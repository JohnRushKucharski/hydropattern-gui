"""Frequency characteristic card: typed field state, metrics_text
conversion, and characteristic_rows sync helpers."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Literal, cast

from hydropattern_gui.characteristics._shared import (
    CharacteristicRowState,
    FormValidationError,
    _metrics_to_text,
)

FrequencyPatternMode = Literal["count", "between", "probability"]


@dataclass(frozen=True)
class FrequencyPatternFields:
    """Typed field state for one frequency pattern (the base pattern of an
    un-nested frequency, or either half of a nested frequency).

    Mirrors hydropattern's un-nested forms:
        [operator, n, N, (event_bool)]        -> COUNT
        [min_n, max_n, N, (event_bool)]       -> BETWEEN
        [operator, probability, (event_bool)] -> PROBABILITY (base-only; see
                                                  frequency_fields_to_metrics)
    count_by_event is always emitted explicitly (never omitted for its
    hydropattern default of True), per locked design decision.
    """

    mode: FrequencyPatternMode
    operator: str | None
    count_n: int | None
    probability: float | None
    between_min: int | None
    between_max: int | None
    out_of_n: int | None
    count_by_event: bool


_BLANK_FREQUENCY_PATTERN_FIELDS = FrequencyPatternFields(
    mode="count",
    operator=None,
    count_n=None,
    probability=None,
    between_min=None,
    between_max=None,
    out_of_n=None,
    count_by_event=True,
)


@dataclass(frozen=True)
class FrequencyFields:
    """Typed field state for the Frequency characteristic card.

    nested_enabled toggles whether a second, dependent frequency pattern
    (`nested`) is appended alongside `base`, producing hydropattern's
    [base_list, nested_list] nested-frequency shape. PROBABILITY mode is
    only valid for `base` when nested_enabled is True (hydropattern rejects
    a standalone/un-nested probability form); `nested` may only be COUNT or
    BETWEEN.
    """

    nested_enabled: bool
    base: FrequencyPatternFields
    nested: FrequencyPatternFields


_BLANK_FREQUENCY_FIELDS = FrequencyFields(
    nested_enabled=False,
    base=_BLANK_FREQUENCY_PATTERN_FIELDS,
    nested=_BLANK_FREQUENCY_PATTERN_FIELDS,
)


def _frequency_pattern_values(
    fields: FrequencyPatternFields,
    allow_probability: bool,
    prefix: str,
    field_errors: dict[str, str],
) -> list[object]:
    """Build one pattern's metrics list (sans trailing count_by_event),
    recording any field_errors under f"{prefix}_{field}" keys."""
    if fields.mode == "probability":
        if not allow_probability:
            field_errors[f"{prefix}_mode"] = (
                "probability is only valid for the base pattern of a nested frequency"
            )
            return []
        if fields.operator is None:
            field_errors[f"{prefix}_operator"] = "required"
        if fields.probability is None:
            field_errors[f"{prefix}_probability"] = "required"
        return [fields.operator, fields.probability]
    if fields.mode == "count":
        if fields.operator is None:
            field_errors[f"{prefix}_operator"] = "required"
        if fields.count_n is None:
            field_errors[f"{prefix}_count_n"] = "required"
        if fields.out_of_n is None:
            field_errors[f"{prefix}_out_of_n"] = "required"
        return [fields.operator, fields.count_n, fields.out_of_n]
    # between
    if fields.between_min is None:
        field_errors[f"{prefix}_between_min"] = "required"
    if fields.between_max is None:
        field_errors[f"{prefix}_between_max"] = "required"
    if fields.out_of_n is None:
        field_errors[f"{prefix}_out_of_n"] = "required"
    return [fields.between_min, fields.between_max, fields.out_of_n]


def frequency_fields_to_metrics(fields: FrequencyFields) -> str:
    """Convert typed Frequency card fields into a metrics_text list literal
    (un-nested, or nested [base_list, nested_list] when nested_enabled)."""
    field_errors: dict[str, str] = {}
    base_values = _frequency_pattern_values(
        fields.base,
        allow_probability=fields.nested_enabled,
        prefix="base",
        field_errors=field_errors,
    )
    if fields.nested_enabled:
        nested_values = _frequency_pattern_values(
            fields.nested, allow_probability=False, prefix="nested", field_errors=field_errors
        )
        if field_errors:
            raise FormValidationError(field_errors)
        base_values.append(fields.base.count_by_event)
        nested_values.append(fields.nested.count_by_event)
        return _metrics_to_text([base_values, nested_values])
    if field_errors:
        raise FormValidationError(field_errors)
    base_values.append(fields.base.count_by_event)
    return _metrics_to_text(base_values)


def _frequency_pattern_from_values(values: list[object]) -> FrequencyPatternFields:
    """Inverse of _frequency_pattern_values (including the trailing
    count_by_event, which is optional in hydropattern's own format -
    defaults to True when absent - even though this GUI always writes it
    explicitly)."""
    values = list(values)
    count_by_event = True
    if values and isinstance(values[-1], bool):
        count_by_event = values[-1]
        values = values[:-1]
    if isinstance(values[0], str):
        if len(values) == 2:
            return FrequencyPatternFields(
                mode="probability",
                operator=cast(str, values[0]),
                count_n=None,
                probability=float(cast(float, values[1])),
                between_min=None,
                between_max=None,
                out_of_n=None,
                count_by_event=count_by_event,
            )
        return FrequencyPatternFields(
            mode="count",
            operator=cast(str, values[0]),
            count_n=int(cast(float, values[1])),
            probability=None,
            between_min=None,
            between_max=None,
            out_of_n=int(cast(float, values[2])),
            count_by_event=count_by_event,
        )
    return FrequencyPatternFields(
        mode="between",
        operator=None,
        count_n=None,
        probability=None,
        between_min=int(cast(float, values[0])),
        between_max=int(cast(float, values[1])),
        out_of_n=int(cast(float, values[2])),
        count_by_event=count_by_event,
    )


def frequency_metrics_from_text(metrics_text: str) -> FrequencyFields:
    """Parse a metrics_text list literal into typed Frequency card fields."""
    try:
        parsed = ast.literal_eval(metrics_text.strip())
    except (ValueError, SyntaxError) as exc:
        raise FormValidationError(
            {"metrics": "must be valid Python/TOML-like list literal"}
        ) from exc
    if not isinstance(parsed, list) or not parsed:
        raise FormValidationError({"metrics": "must parse to a non-empty list"})
    if isinstance(parsed[0], list):
        if len(parsed) != 2 or not isinstance(parsed[1], list):
            raise FormValidationError(
                {"metrics": "nested frequency must be [base_list, nested_list]"}
            )
        return FrequencyFields(
            nested_enabled=True,
            base=_frequency_pattern_from_values(parsed[0]),
            nested=_frequency_pattern_from_values(parsed[1]),
        )
    return FrequencyFields(
        nested_enabled=False,
        base=_frequency_pattern_from_values(parsed),
        nested=_BLANK_FREQUENCY_PATTERN_FIELDS,
    )


def sync_frequency_row(
    rows: list[CharacteristicRowState],
    enabled: bool,
    fields: FrequencyFields,
    insert_at: int | None = None,
) -> list[CharacteristicRowState]:
    """Frequency analogue of sync_duration_row (same insert/preserve
    rules)."""
    without_frequency = [row for row in rows if row.kind != "frequency"]
    if not enabled:
        return without_frequency

    try:
        metrics_text = frequency_fields_to_metrics(fields)
    except FormValidationError:
        metrics_text = ""

    new_row = CharacteristicRowState(kind="frequency", metrics_text=metrics_text)
    existing_index = next(
        (index for index, row in enumerate(rows) if row.kind == "frequency"), None
    )
    if existing_index is not None:
        result = list(without_frequency)
        result.insert(existing_index, new_row)
        return result

    index = len(without_frequency) if insert_at is None else max(
        0, min(insert_at, len(without_frequency))
    )
    result = list(without_frequency)
    result.insert(index, new_row)
    return result


def frequency_insertion_offset(rows: list[CharacteristicRowState]) -> int:
    """Number of non-Frequency rows preceding it; 0 when absent."""
    offset = 0
    for row in rows:
        if row.kind == "frequency":
            return offset
        offset += 1
    return 0


def extract_frequency_state(
    rows: list[CharacteristicRowState],
) -> tuple[bool, FrequencyFields]:
    """Inverse of sync_frequency_row."""
    row = next((row for row in rows if row.kind == "frequency"), None)
    if row is None:
        return False, _BLANK_FREQUENCY_FIELDS
    try:
        return True, frequency_metrics_from_text(row.metrics_text)
    except FormValidationError:
        return True, _BLANK_FREQUENCY_FIELDS


