import os

from app.bootstrap.dpi import setup_high_dpi


def test_setup_high_dpi_sets_default_environment(monkeypatch) -> None:
    monkeypatch.delenv("QT_ENABLE_HIGHDPI_SCALING", raising=False)
    monkeypatch.delenv("QT_AUTO_SCREEN_SCALE_FACTOR", raising=False)
    monkeypatch.delenv("QT_SCALE_FACTOR_ROUNDING_POLICY", raising=False)

    setup_high_dpi()

    assert os.environ["QT_ENABLE_HIGHDPI_SCALING"] == "1"
    assert os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] == "1"
    assert os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] == "RoundPreferFloor"


def test_setup_high_dpi_preserves_existing_environment(monkeypatch) -> None:
    monkeypatch.setenv("QT_ENABLE_HIGHDPI_SCALING", "0")
    monkeypatch.setenv("QT_AUTO_SCREEN_SCALE_FACTOR", "0")
    monkeypatch.setenv("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

    setup_high_dpi()

    assert os.environ["QT_ENABLE_HIGHDPI_SCALING"] == "0"
    assert os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] == "0"
    assert os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] == "PassThrough"
