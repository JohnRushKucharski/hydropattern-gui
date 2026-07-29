from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from hydropattern_gui.runner_service import HydropatternRunner, RunOptions


class _FakePopen:
    def __init__(self, command: list[str], **_: object) -> None:
        self.command = command
        self.pid = 4242
        self._return_code = 0
        self._cancelled = False
        self.stdout = StringIO("out-1\nout-2\n")
        self.stderr = StringIO("err-1\n")

    def poll(self) -> int | None:
        return None if self._cancelled else 0

    def wait(self) -> int:
        return 130 if self._cancelled else self._return_code


def test_build_command_deterministic_order() -> None:
    runner = HydropatternRunner(executable="hydropattern")
    command = runner.build_command(
        "cfg.toml",
        RunOptions(
            output_directory="out",
            plot=False,
            excel=True,
            overwrite=False,
            interp=True,
            show=False,
            threshold=0.25,
            color_map="RdBu",
            color_map_ticks=[-2.0, 0.0, 2.0],
        ),
    )
    assert command == [
        "hydropattern",
        "run",
        "cfg.toml",
        "--output-dir",
        "out",
        "--no-plot",
        "--excel",
        "--no-overwrite",
        "--interp",
        "--no-show",
        "--threshold",
        "0.25",
        "--color-map",
        "RdBu",
        "--color-map-ticks",
        "-2.0",
        "--color-map-ticks",
        "0.0",
        "--color-map-ticks",
        "2.0",
    ]


def test_run_streams_logs_and_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, str]] = []

    def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
        command = args[0]
        assert isinstance(command, list)
        return _FakePopen(command=command, **kwargs)

    monkeypatch.setattr("hydropattern_gui.runner_service.subprocess.Popen", fake_popen)
    runner = HydropatternRunner(executable="hydropattern")
    result = runner.run(
        "cfg.toml",
        options=RunOptions(plot=False, excel=False),
        on_output=lambda channel, line: seen.append((channel, line)),
        cwd=".",
    )

    assert result.exit_code == 0
    assert result.cancelled is False
    assert result.stdout == "out-1\nout-2\n"
    assert result.stderr == "err-1\n"
    assert seen == [("stdout", "out-1\n"), ("stdout", "out-2\n"), ("stderr", "err-1\n")]


def test_cancel_terminates_process_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    terminated: list[int] = []

    def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
        command = args[0]
        assert isinstance(command, list)
        process = _FakePopen(command=command, **kwargs)
        process._cancelled = True
        return process

    def fake_terminate(pid: int) -> None:
        terminated.append(pid)

    monkeypatch.setattr("hydropattern_gui.runner_service.subprocess.Popen", fake_popen)
    monkeypatch.setattr("hydropattern_gui.runner_service._terminate_process_tree", fake_terminate)

    runner = HydropatternRunner()
    running = runner.start("cfg.toml")
    running.cancel()
    result = running.wait()

    assert terminated == [4242]
    assert result.cancelled is True
    assert result.exit_code == 130


def test_build_command_includes_fillin_flag() -> None:
    runner = HydropatternRunner(executable="hydropattern")
    command = runner.build_command(
        "cfg.toml",
        RunOptions(fillin=True),
    )
    assert command == ["hydropattern", "run", "cfg.toml", "--fillin"]


def test_build_command_includes_no_fillin_flag() -> None:
    runner = HydropatternRunner(executable="hydropattern")
    command = runner.build_command(
        "cfg.toml",
        RunOptions(fillin=False),
    )
    assert command == ["hydropattern", "run", "cfg.toml", "--no-fillin"]


def test_run_toml_options_conflict_raises() -> None:
    runner = HydropatternRunner()
    with pytest.raises(ValueError):
        runner.build_command(
            "cfg.toml",
            RunOptions(run_toml_options=True, output_directory="out"),
        )


def test_run_toml_options_conflicts_with_fillin() -> None:
    runner = HydropatternRunner()
    with pytest.raises(ValueError):
        runner.build_command(
            "cfg.toml",
            RunOptions(run_toml_options=True, fillin=True),
        )


def test_integration_smoke_run_fixture_toml_success(tmp_path: Path) -> None:
    timeseries_csv = tmp_path / "input.csv"
    timeseries_csv.write_text(
        "time,scenario_a\n"
        "2000-01-01,0.5\n"
        "2000-01-02,2.0\n"
        "2000-01-03,3.0\n",
        encoding="utf-8",
    )
    config_toml = tmp_path / "fixture.toml"
    config_toml.write_text(
        "[timeseries]\n"
        "path = \"input.csv\"\n"
        "date_format = \"%Y-%m-%d\"\n"
        "\n"
        "[components.simple_component]\n"
        "magnitude = [\">\", 1.0]\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"

    runner = HydropatternRunner()
    result = runner.run(
        config_toml.name,
        options=RunOptions(
            output_directory=output_dir.name,
            plot=False,
            excel=False,
            overwrite=True,
        ),
        cwd=tmp_path,
    )

    assert result.exit_code == 0
    assert result.cancelled is False
    assert result.command == [
        "hydropattern",
        "run",
        "fixture.toml",
        "--output-dir",
        "out",
        "--no-plot",
        "--no-excel",
        "--overwrite",
    ]
    assert output_dir.exists()
    assert "Output written to:" in result.stdout
