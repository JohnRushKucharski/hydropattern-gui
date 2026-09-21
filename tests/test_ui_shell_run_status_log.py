"""Headless widget tests for Task 4 run/status/log polish (HANDOFF.md
phase4-run-status-log-polish): stdout/stderr Text tag coloring, "Open
output folder" button enable/disable, and Cancel button wiring for
cancel-capable runners. No window is shown and mainloop() is never
called."""

from __future__ import annotations

import tkinter as tk
from unittest.mock import patch

import pytest

from hydropattern_gui.runner_service import (
    InProcessHydropatternRunner,
    RunOptions,
    RunResult,
)
from hydropattern_gui.ui_shell import GuiController, HydropatternGuiApp


@pytest.fixture
def app(root: tk.Tk) -> HydropatternGuiApp:
    controller = GuiController(InProcessHydropatternRunner())
    application = HydropatternGuiApp(root, controller)
    yield application
    for child in root.winfo_children():
        child.destroy()


class _FakeRunningRun:
    def __init__(self, result: RunResult, wait_event: object | None = None) -> None:
        self._result = result
        self._wait_event = wait_event
        self.cancel_called = False

    def wait(self) -> RunResult:
        if self._wait_event is not None:
            self._wait_event.wait(timeout=5)  # type: ignore[attr-defined]
        return self._result

    def cancel(self) -> None:
        self.cancel_called = True


class _FakeCancellableRunner:
    """Minimal stand-in for HydropatternRunner: exposes start() (and no
    blocking run()), so GuiController.supports_cancel() reports True."""

    def __init__(self, result: RunResult, wait_event: object | None = None) -> None:
        self._result = result
        self._wait_event = wait_event
        self.started_with: tuple[object, ...] | None = None

    def start(
        self,
        config_path: object,
        options: RunOptions | None = None,
        on_output: object = None,
        cwd: object = None,
    ) -> _FakeRunningRun:
        self.started_with = (config_path, options, cwd)
        return _FakeRunningRun(self._result, self._wait_event)


def test_inprocess_runner_does_not_support_cancel(app: HydropatternGuiApp) -> None:
    assert app._controller.supports_cancel() is False
    assert str(app._cancel_button.cget("state")) == "disabled"
    assert not app._cancel_button.winfo_ismapped()


def test_cancellable_runner_shows_enabled_cancel_button_after_run_starts(
    root: tk.Tk,
) -> None:
    import threading

    result = RunResult(
        command=["hydropattern", "run", "x.toml"],
        cwd=None,  # type: ignore[arg-type]
        exit_code=0,
        cancelled=False,
        stdout="",
        stderr="",
    )
    wait_event = threading.Event()
    controller = GuiController(_FakeCancellableRunner(result, wait_event))
    application = HydropatternGuiApp(root, controller)
    try:
        assert controller.supports_cancel() is True
        application._path_var.set("timeseries.csv")
        application._timing_enabled_var.set(True)
        application._timing_first_day_var.set("1")
        application._timing_last_day_var.set("120")
        application._on_run()
        for _ in range(200):
            if application._active_run is not None:
                break
            root.update()
        assert application._active_run is not None
        assert str(application._cancel_button.cget("state")) == "normal"
        application._on_cancel()
        assert application._active_run.cancel_called is True  # type: ignore[attr-defined]
        assert str(application._cancel_button.cget("state")) == "disabled"
    finally:
        wait_event.set()
        for child in root.winfo_children():
            child.destroy()


def test_log_text_applies_stderr_tag_for_stderr_lines(app: HydropatternGuiApp) -> None:
    app._set_log_placeholder()
    app._append_log("boom\n", "stderr")
    ranges = app._log_text.tag_ranges("stderr")
    assert ranges, "expected a stderr-tagged range after appending a stderr line"
    assert app._log_text.tag_cget("stderr", "foreground") == "red"
    tagged_start, tagged_end = ranges[0], ranges[1]
    assert app._log_text.get(tagged_start, tagged_end) == "boom\n"


def test_log_text_stdout_lines_are_not_tagged_stderr(app: HydropatternGuiApp) -> None:
    app._set_log_placeholder()
    before = len(app._log_text.tag_ranges("stderr"))
    app._append_log("ok\n", "stdout")
    after = len(app._log_text.tag_ranges("stderr"))
    assert before == after


def test_open_output_dir_button_disabled_until_successful_run(app: HydropatternGuiApp) -> None:
    assert str(app._open_output_dir_button.cget("state")) == "disabled"


def test_open_output_dir_button_enabled_after_success_event(app: HydropatternGuiApp) -> None:
    from pathlib import Path

    result = RunResult(
        command=["hydropattern", "run", "x.toml"],
        cwd=Path("."),
        exit_code=0,
        cancelled=False,
        stdout="",
        stderr="",
    )
    app._event_queue.put(("done", result))
    app._drain_events()
    assert str(app._open_output_dir_button.cget("state")) == "normal"


def test_open_output_dir_button_stays_disabled_after_failure_event(
    app: HydropatternGuiApp,
) -> None:
    from pathlib import Path

    result = RunResult(
        command=["hydropattern", "run", "x.toml"],
        cwd=Path("."),
        exit_code=1,
        cancelled=False,
        stdout="",
        stderr="",
    )
    app._event_queue.put(("done", result))
    app._drain_events()
    assert str(app._open_output_dir_button.cget("state")) == "disabled"


def test_on_open_output_dir_calls_os_startfile_with_output_dir(app: HydropatternGuiApp) -> None:
    app._output_dir_var.set("C:\\some\\output")
    with patch("hydropattern_gui.ui_shell.os.startfile") as mock_startfile:
        app._on_open_output_dir()
    mock_startfile.assert_called_once_with("C:\\some\\output")
