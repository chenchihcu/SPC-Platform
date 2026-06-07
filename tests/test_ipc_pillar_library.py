from app.analytics.ipc_pillar_library import (
    count_by_pillar,
    list_entries,
    list_validation_errors,
    load_all_entries,
)


def test_seed_entries_count_by_pillar() -> None:
    counts = count_by_pillar()
    assert counts["dfm"] == 20
    assert counts["printing_spi"] == 20
    assert counts["bga_fa"] == 20
    assert counts["jstd_material"] == 20


def test_seed_entries_have_no_validation_errors() -> None:
    errors = list_validation_errors()
    assert errors == {}


def test_list_entries_filters_by_keyword_and_status() -> None:
    reviewed_rows = list_entries(
        pillar="printing_spi",
        keyword="Area Ratio",
        review_status="reviewed",
    )
    assert reviewed_rows
    assert all(row["pillar"] == "printing_spi" for row in reviewed_rows)
    assert all(row["review_status"] == "reviewed" for row in reviewed_rows)


def test_list_entries_filters_by_risk_level() -> None:
    high_risk = list_entries(pillar="bga_fa", risk_level="H")
    assert high_risk
    assert all(row["risk_level"] == "H" for row in high_risk)


def test_load_all_entries_total_count() -> None:
    entries = load_all_entries()
    assert len(entries) == 80
