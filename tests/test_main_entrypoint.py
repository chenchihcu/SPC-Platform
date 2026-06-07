import main


def test_main_returns_error_when_required_module_missing(monkeypatch, capsys) -> None:
    monkeypatch.setattr(main, "_missing_required_modules", lambda: ["app.ui.pages.diagnostic_page"])

    code = main.main()

    captured = capsys.readouterr()
    assert code == 1
    assert "Startup preflight failed" in captured.err
    assert "missing_module=app.ui.pages.diagnostic_page" in captured.err


def test_main_returns_error_when_import_raises_module_not_found(monkeypatch, capsys) -> None:
    monkeypatch.setattr(main, "_missing_required_modules", list)

    def _raise() -> None:
        raise ModuleNotFoundError("app.ui.pages.diagnostic_page")

    monkeypatch.setattr(main, "_load_run_app", _raise)

    code = main.main()

    captured = capsys.readouterr()
    assert code == 1
    assert "Startup import failed (ModuleNotFoundError)." in captured.err


def test_main_runs_app_when_preflight_and_import_are_ok(monkeypatch) -> None:
    monkeypatch.setattr(main, "_missing_required_modules", list)
    called = {"value": False}

    def _run_app() -> None:
        called["value"] = True

    monkeypatch.setattr(main, "_load_run_app", lambda: _run_app)

    code = main.main()

    assert code == 0
    assert called["value"] is True
