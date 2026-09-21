"""Shared types/helpers used by every per-characteristic-kind module in
this package (magnitude/duration/timing/rate_of_change/frequency). Split out
of the former single 996+-line gui_form.py during the
thermo-nuclear-code-review-pre-phase1 refactor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CharacteristicKind = Literal["timing", "magnitude", "duration", "rate_of_change", "frequency"]
_CHARACTERISTIC_KINDS: tuple[CharacteristicKind, ...] = (
    "timing",
    "magnitude",
    "rate_of_change",
    "duration",
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


def _metrics_to_text(metrics: list[object]) -> str:
    rendered_parts: list[str] = []
    for item in metrics:
        if isinstance(item, str):
            rendered_parts.append(f'"{item}"')
        elif isinstance(item, list):
            rendered_parts.append(_metrics_to_text(item))
        else:
            rendered_parts.append(str(item))
    return f"[{', '.join(rendered_parts)}]"
