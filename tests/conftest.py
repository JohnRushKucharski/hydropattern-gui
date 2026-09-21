"""Shared Tk root fixture for headless ui_shell widget tests.

Session-scoped (not per-module) because this environment's Tk install is
unreliable: repeated `tk.Tk()` instantiation within the same Python process
intermittently raises `_tkinter.TclError` (missing tcl8.6/ttk/cursors.tcl).
With one `tk.Tk()` per test *module* (the previous pattern, duplicated
across every `test_ui_shell_*_card.py` file), a full test run creates 7+
separate roots and occasionally hits that flakiness. A single session-wide
root eliminates the repeated instantiation entirely, since ttk widgets are
cleared out (not destroyed) between tests in each file's own `app` fixture.
"""

from __future__ import annotations

import tkinter as tk

import pytest


@pytest.fixture(scope="session")
def root() -> tk.Tk:
    try:
        tk_root = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - no display/broken Tk install
        pytest.skip(f"Tk display unavailable: {exc}")
    tk_root.withdraw()
    yield tk_root
    tk_root.destroy()
