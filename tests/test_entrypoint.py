from hydropattern_gui import main


def test_main_headless_mode(capsys, monkeypatch) -> None:
    monkeypatch.setenv("HYDROPATTERN_GUI_HEADLESS", "1")
    main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "hydropattern-gui headless mode"
