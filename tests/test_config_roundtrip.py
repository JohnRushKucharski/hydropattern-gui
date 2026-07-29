from hydropattern_gui.config_model import (
    ClimateCanvasPlotOptions,
    ComponentConfig,
    HydropatternConfig,
    MetricOptions,
    OutputOptions,
    PlotOptions,
    TimeseriesConfig,
    dumps_config_toml,
    loads_config_toml,
)


def _sample_config() -> HydropatternConfig:
    return HydropatternConfig(
        timeseries=TimeseriesConfig(
            path="examples/single_timeseries.csv",
            date_format="%Y-%m-%d",
            first_day_of_water_year=1,
            sheet_name=0,
        ),
        components={
            "november_pulse_flow": ComponentConfig(
                timing=[305, 335],
                magnitude=[">", 1.0],
                rate_of_change=[">", 2.0, 1],
                verbose=False,
                success_pattern=True,
            ),
            "dry_season_baseflow": ComponentConfig(
                timing=[152, 305],
                magnitude=["<", 1.0],
                duration=[">", 7],
                success_pattern=False,
            ),
        },
        output=OutputOptions(
            directory="examples/output",
            overwrite=True,
            excel=True,
            metric=MetricOptions(mode="portion"),
            plot=PlotOptions(
                enabled=True,
                climate_canvas=ClimateCanvasPlotOptions(
                    interpolate=True,
                    show=False,
                    title="Response Surface",
                    xlabel="Precipitation Delta (%)",
                    ylabel="Temperature Delta (C)",
                    zlabel="portion",
                    threshold=0.5,
                    color_map="RdBu",
                    color_map_ticks=[-2.0, 0.0, 2.0],
                    fillin=True,
                ),
            ),
        ),
    )


def test_complete_mode_round_trip_stable_and_ordered() -> None:
    config = _sample_config()
    toml_text_a = dumps_config_toml(config, mode="complete")
    toml_text_b = dumps_config_toml(config, mode="complete")

    assert toml_text_a == toml_text_b

    assert toml_text_a.find("[timeseries]") < toml_text_a.find("[components.november_pulse_flow]")
    assert (
        toml_text_a.find("[components.november_pulse_flow]")
        < toml_text_a.find("[components.dry_season_baseflow]")
        < toml_text_a.find("[output]")
        < toml_text_a.find("[output.metric]")
        < toml_text_a.find("[output.plot]")
        < toml_text_a.find("[output.plot.climate-canvas]")
    )

    loaded = loads_config_toml(toml_text_a)
    assert loaded == config


def test_minimal_mode_omits_defaults() -> None:
    config = HydropatternConfig(
        timeseries=TimeseriesConfig(path="examples/single_timeseries.csv"),
        components={
            "single_characteristic": ComponentConfig(
                magnitude=[">", 1.0],
            ),
        },
    )
    toml_text = dumps_config_toml(config, mode="minimal")

    assert "date_format" not in toml_text
    assert "first_day_of_water_year" not in toml_text
    assert "sheet_name" not in toml_text
    assert "verbose" not in toml_text
    assert "success_pattern" not in toml_text
    assert "[output]" not in toml_text

    loaded = loads_config_toml(toml_text)
    assert loaded == config
