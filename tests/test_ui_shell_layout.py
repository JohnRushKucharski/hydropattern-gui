"""Headless widget tests for the sidebar+stage 2-column shell layout
(HANDOFF.md Task 2 / phase1-shell-layout-restructure). No window is shown
and mainloop() is never called."""

from __future__ import annotations

import tkinter as tk

import pytest

from hydropattern_gui.runner_service import InProcessHydropatternRunner
from hydropattern_gui.ui_shell import GuiController, HydropatternGuiApp


@pytest.fixture
def app(root: tk.Tk) -> HydropatternGuiApp:
    controller = GuiController(InProcessHydropatternRunner())
    application = HydropatternGuiApp(root, controller)
    yield application
    for child in root.winfo_children():
        child.destroy()


def test_sidebar_outer_and_stage_are_gridded_in_separate_columns(
    app: HydropatternGuiApp,
) -> None:
    sidebar_info = app._sidebar_outer.grid_info()
    stage_info = app._stage_container.grid_info()
    assert int(sidebar_info["column"]) == 0
    assert int(stage_info["column"]) == 1


def test_stage_column_has_expand_weight(app: HydropatternGuiApp) -> None:
    # The stage column (1) should be the one that grows; sidebar (0) stays
    # fixed-width.
    assert int(app._root.grid_columnconfigure(1)["weight"]) == 1
    assert int(app._root.grid_columnconfigure(0)["weight"]) == 0


def test_sidebar_holds_input_sections(app: HydropatternGuiApp) -> None:
    sidebar_children = app._sidebar_container.winfo_children()
    # Timeseries, Component editor, Output/Metric, Climate, Save row, run button row.
    assert len(sidebar_children) >= 6


def test_stage_holds_preview_and_log(app: HydropatternGuiApp) -> None:
    assert app._preview_text.winfo_manager() != ""
    assert app._log_text.winfo_manager() != ""

    def _under_stage(widget: tk.Misc) -> bool:
        current: tk.Misc | None = widget
        while current is not None:
            if current is app._stage_container:
                return True
            current = current.master
        return False

    assert _under_stage(app._preview_text)
    assert _under_stage(app._log_text)


def test_run_button_lives_in_sidebar_not_stage(app: HydropatternGuiApp) -> None:
    def _under_sidebar(widget: tk.Misc) -> bool:
        current: tk.Misc | None = widget
        while current is not None:
            if current is app._sidebar_container:
                return True
            current = current.master
        return False

    assert _under_sidebar(app._run_button)


def test_clam_theme_and_custom_styles_registered(app: HydropatternGuiApp) -> None:
    style = app._style
    assert style.theme_use() == "clam"
    assert style.layout("Card.TLabelframe")
    assert style.layout("Primary.TButton")
