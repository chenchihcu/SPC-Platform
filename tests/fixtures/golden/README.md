# Golden fixtures (deprecated location)

System baseline data lives at the repository root: **`golden_dataset/`**.

Pytest `golden_root` is resolved from [`tests/release_validation/conftest.py`](../../release_validation/conftest.py) to `golden_dataset/`. Do not add new scenarios under `tests/fixtures/golden/`.
