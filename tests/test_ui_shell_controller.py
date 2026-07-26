from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from hydropattern_gui.runner_service import LogCallback, RunOptions, RunResult
from hydropattern_gui.ui_shell import (
    CharacteristicRowState,
    FormValidationError,
    GuiController,
    GuiFormState,
)


class _FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, Path, object]] = []

    def run(
        self,
        config_path: str | Path,
        options: RunOptions | None = None,
        on_output: LogCallback | None = None,
        cwd: str | Path | None = None,
    ) -> RunResult:
        config_path_str = str(config_path)
        run_cwd = Path(cwd).resolve() if cwd is not None else Path.cwd()
        self.calls.append((config_path_str, options, run_cwd, on_output))
        if on_output is not None:
            on_output("stdout", "line-1\n")
            on_output("stderr", "line-2\n")
        return RunResult(
            command=["hydropattern", "run", config_path_str],
            cwd=run_cwd,
            exit_code=0,
            cancelled=False,
            stdout="line-1\n",
            stderr="line-2\n",
        )


def _state() -> GuiFormState:
    return GuiFormState(
        timeseries_path="input.csv",
        date_format="%Y-%m-%d",
        first_day_of_water_year="1",
        sheet_name="0",
        output_directory="out",
        excel=False,
        overwrite=True,
        metric_mode="portion",
        component_name="simple_component",
        component_verbose=True,
        component_success_pattern=False,
        characteristic_rows=[
            CharacteristicRowState(kind="timing", metrics_text="[305, 335]"),
            CharacteristicRowState(kind="magnitude", metrics_text='[">", 1.5]'),
            CharacteristicRowState(kind="duration", metrics_text='[">", 7]'),
        ],
        plot_enabled=True,
        climate_interpolate=True,
        climate_show=False,
        climate_title="Response Surface",
        climate_xlabel="Precipitation Delta (%)",
        climate_ylabel="Temperature Delta (C)",
        climate_zlabel="portion",
        climate_threshold="0.0",
        climate_color_map="RdBu",
        climate_color_map_ticks="-2.0,0.0,2.0",
    )


def test_open_existing_toml_hydrates_form_state(tmp_path: Path) -> None:
    config_path = tmp_path / "cfg.toml"
    config_path.write_text(
        "[timeseries]\n"
        'path = "in.csv"\n'
        'date_format = "%Y-%m-%d"\n'
        "first_day_of_water_year = 5\n"
        "\n"
        "[components.baseflow]\n"
        'timing = [152, 305]\n'
        'magnitude = [">", 2.5]\n'
        'duration = [">", 7]\n'
        "verbose = true\n"
        "success_pattern = false\n"
        "\n"
        "[output]\n"
        'directory = "o"\n'
        "excel = false\n"
        "overwrite = false\n"
        "\n"
        "[output.metric]\n"
        'mode = "percentage"\n'
        "\n"
        "[output.plot]\n"
        "enabled = true\n"
        "\n"
        "[output.plot.climate-canvas]\n"
        "interpolate = false\n"
        "show = true\n"
        'title = "T"\n'
        'xlabel = "X"\n'
        'ylabel = "Y"\n'
        'zlabel = "Z"\n'
        "threshold = 0.2\n"
        'color_map = "RdYlBu"\n'
        "color_map_ticks = [-1.0, 0.0, 1.0]\n",
        encoding="utf-8",
    )
    controller = GuiController(runner=_FakeRunner())
    state = controller.load_form_state(config_path)

    assert state.timeseries_path == "in.csv"
    assert state.first_day_of_water_year == "5"
    assert state.component_name == "baseflow"
    assert [row.kind for row in state.characteristic_rows] == ["timing", "magnitude", "duration"]
    assert state.characteristic_rows[1].metrics_text == '[">", 2.5]'
    assert state.component_verbose is True
    assert state.component_success_pattern is False
    assert state.output_directory == "o"
    assert state.metric_mode == "percentage"
    assert state.excel is False
    assert state.overwrite is False
    assert state.plot_enabled is True
    assert state.climate_interpolate is False
    assert state.climate_show is True
    assert state.climate_title == "T"
    assert state.climate_xlabel == "X"
    assert state.climate_ylabel == "Y"
    assert state.climate_zlabel == "Z"
    assert state.climate_threshold == "0.2"
    assert state.climate_color_map == "RdYlBu"
    assert state.climate_color_map_ticks == "-1.0,0.0,1.0"


def test_preview_reflects_current_form_state() -> None:
    controller = GuiController(runner=_FakeRunner())
    preview = controller.preview_toml(_state(), mode="minimal")
    data = tomllib.loads(preview)
    assert data["timeseries"]["path"] == "input.csv"
    assert list(data["components"]["simple_component"])[:3] == ["timing", "magnitude", "duration"]
    assert data["components"]["simple_component"]["magnitude"] == [">", 1.5]
    assert data["components"]["simple_component"]["verbose"] is True
    assert data["components"]["simple_component"]["success_pattern"] is False
    assert data["output"]["directory"] == "out"
    assert data["output"]["excel"] is False
    assert data["output"]["plot"]["enabled"] is True
    assert data["output"]["plot"]["climate-canvas"]["title"] == "Response Surface"
    assert data["output"]["plot"]["climate-canvas"]["color_map_ticks"] == [-2.0, 0.0, 2.0]


def test_run_wires_runner_and_streams_logs(tmp_path: Path) -> None:
    data_path = tmp_path / "input.csv"
    data_path.write_text("time,s1\n2000-01-01,1\n", encoding="utf-8")
    state = _state()
    state.timeseries_path = str(data_path)
    state.output_directory = "out"

    runner = _FakeRunner()
    logs: list[tuple[str, str]] = []
    controller = GuiController(runner=runner)
    result = controller.run(
        state,
        on_log=lambda ch, line: logs.append((ch, line)),
        working_dir=tmp_path,
    )

    assert result.exit_code == 0
    assert logs == [("stdout", "line-1\n"), ("stderr", "line-2\n")]
    assert len(runner.calls) == 1
    called_config, _opts, called_cwd, _cb = runner.calls[0]
    assert called_config.endswith(".toml")
    assert called_cwd == tmp_path


def test_validation_errors_map_to_fields_before_run(tmp_path: Path) -> None:
    bad_state = _state()
    bad_state.first_day_of_water_year = "bad-int"
    bad_state.characteristic_rows[0] = CharacteristicRowState(
        kind="timing", metrics_text="[1]"
    )

    controller = GuiController(runner=_FakeRunner())
    with pytest.raises(FormValidationError) as exc:
        controller.run(bad_state, working_dir=tmp_path)

    assert "timeseries.first_day_of_water_year" in exc.value.field_errors
    assert "components.simple_component.rows[0].metrics" in exc.value.field_errors
