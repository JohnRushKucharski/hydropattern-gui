from pathlib import Path

from hydropattern_gui.runner_service import InProcessHydropatternRunner, RunOptions


def test_inprocess_runner_runs_fixture_and_streams_logs(tmp_path: Path) -> None:
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
    seen: list[tuple[str, str]] = []

    runner = InProcessHydropatternRunner()
    result = runner.run(
        config_toml.name,
        options=RunOptions(
            output_directory=output_dir.name,
            plot=False,
            excel=False,
            overwrite=True,
        ),
        on_output=lambda channel, line: seen.append((channel, line)),
        cwd=tmp_path,
    )

    assert result.exit_code == 0
    assert output_dir.exists()
    assert "Output written to:" in result.stdout
    assert any(channel == "stdout" for channel, _ in seen)
