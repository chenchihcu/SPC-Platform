"""
Regression tests for:
  Bug 1 – _restore_refresh_button() gen_id guard
           (計算中… button stuck when a cancelled worker resets the flag early)

The tests run without a live Qt event loop by mocking the button widget and
exercising the pure flag/gen_id logic that lives in MainWindow.
"""


# ---------------------------------------------------------------------------
# Minimal stub that replicates only the parts of MainWindow under test
# ---------------------------------------------------------------------------

class _FakeBtn:
    """Minimal QPushButton stand-in."""
    def __init__(self) -> None:
        self.enabled = True
        self.text = "重新分析"
        self.props: dict = {}

    def setEnabled(self, v: bool) -> None:
        self.enabled = v

    def setText(self, t: str) -> None:
        self.text = t

    def setProperty(self, k: str, v) -> None:
        self.props[k] = v

    def style(self):
        return self

    def unpolish(self, _) -> None:
        pass

    def polish(self, _) -> None:
        pass


class _FakeRefreshBtnHost:
    """Exposes a control_panel.refresh_btn, like MainWindow does."""
    def __init__(self) -> None:
        self.refresh_btn = _FakeBtn()


class _MainWindowStub:
    """Carries only the attributes & methods from MainWindow that are under test."""

    def __init__(self) -> None:
        self._refresh_button_loading: bool = False
        self._refresh_button_gen: int = -1
        self._analysis_generation_id: int = 0
        self.control_panel = _FakeRefreshBtnHost()

    # --- copied verbatim from the fixed main_window.py ---

    def _restore_refresh_button(self, gen_id=None) -> None:
        """Restore the refresh button from its loading state."""
        if not getattr(self, "_refresh_button_loading", False):
            return
        if gen_id is not None and gen_id != getattr(self, "_refresh_button_gen", None):
            return
        self._refresh_button_loading = False
        btn = self.control_panel.refresh_btn
        btn.setEnabled(True)
        btn.setText("重新分析")
        btn.setProperty("state", "")

    def _simulate_refresh_analysis(self) -> None:
        """Mirrors refresh_analysis(): sets flag + btn text."""
        self._refresh_button_loading = True
        btn = self.control_panel.refresh_btn
        btn.setEnabled(False)
        btn.setText("計算中…")
        btn.setProperty("state", "loading")

    def _simulate_create_worker(self) -> int:
        """Mirrors _run_refresh_analysis() worker creation block."""
        self._analysis_generation_id += 1
        current_id = self._analysis_generation_id
        if getattr(self, "_refresh_button_loading", False):
            self._refresh_button_gen = current_id
        return current_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRestoreRefreshButtonGenIdGuard:
    """
    Scenario that triggered the original bug
    ─────────────────────────────────────────
    1. Combo-box change → Worker A created (loading flag NOT set).
    2. User clicks «重新分析» → loading flag set, btn → "計算中…".
    3. Worker A cancelled → new Worker B created; _refresh_button_gen = B's gen_id.
    4. Worker A finishes first → _restore_refresh_button(gen_A) called.
       *Old code*: flag=True → restores btn, clears flag → Worker B can't restore.
       *New code*: gen_A ≠ _refresh_button_gen → skip → btn stays "計算中…" ✓
    5. Worker B finishes → _restore_refresh_button(gen_B) called → restores ✓
    """

    def _setup_race(self):
        stub = _MainWindowStub()

        # Step 1: combo change spawns Worker A (no loading flag)
        gen_a = stub._simulate_create_worker()  # gen_id = 1, flag=False, _refresh_button_gen stays -1

        # Step 2: user clicks «重新分析»
        stub._simulate_refresh_analysis()       # flag=True, btn="計算中…"

        # Step 3: Worker B replaces Worker A
        gen_b = stub._simulate_create_worker()  # gen_id = 2, _refresh_button_gen = 2

        return stub, gen_a, gen_b

    def test_cancelled_worker_does_not_clear_loading_flag(self):
        """Worker A's finished must NOT restore the button."""
        stub, gen_a, gen_b = self._setup_race()

        # Worker A finishes (cancelled)
        stub._restore_refresh_button(gen_a)

        assert stub._refresh_button_loading is True, (
            "Cancelled worker (gen_a) must NOT clear _refresh_button_loading"
        )
        assert stub.control_panel.refresh_btn.text == "計算中…", (
            "Button must still show '計算中…' while Worker B is running"
        )

    def test_active_worker_restores_button(self):
        """Worker B's finished MUST restore the button."""
        stub, gen_a, gen_b = self._setup_race()

        # Simulate: Worker A fires (harmless), then Worker B fires
        stub._restore_refresh_button(gen_a)   # should be no-op
        stub._restore_refresh_button(gen_b)   # should restore

        assert stub._refresh_button_loading is False, (
            "Worker B must clear _refresh_button_loading"
        )
        assert stub.control_panel.refresh_btn.text == "重新分析", (
            "Button must be restored to '重新分析' after Worker B finishes"
        )
        assert stub.control_panel.refresh_btn.enabled is True

    def test_early_return_path_restores_unconditionally(self):
        """Direct _restore_refresh_button() call (no gen_id) must always restore."""
        stub = _MainWindowStub()
        stub._simulate_refresh_analysis()

        # Early-return path: no worker was created
        stub._restore_refresh_button()   # gen_id=None

        assert stub._refresh_button_loading is False
        assert stub.control_panel.refresh_btn.text == "重新分析"

    def test_no_op_when_not_loading(self):
        """If flag is False, restore must be a no-op regardless of gen_id."""
        stub = _MainWindowStub()
        stub.control_panel.refresh_btn.setText("重新分析")

        stub._restore_refresh_button(gen_id=99)
        stub._restore_refresh_button()

        assert stub.control_panel.refresh_btn.text == "重新分析"

    def test_gen_id_updated_on_subsequent_worker(self):
        """Each new worker while loading must update _refresh_button_gen."""
        stub = _MainWindowStub()
        stub._simulate_refresh_analysis()

        gen1 = stub._simulate_create_worker()
        assert stub._refresh_button_gen == gen1

        gen2 = stub._simulate_create_worker()
        assert stub._refresh_button_gen == gen2

        # Only gen2 should be able to restore
        stub._restore_refresh_button(gen1)
        assert stub._refresh_button_loading is True   # gen1 blocked

        stub._restore_refresh_button(gen2)
        assert stub._refresh_button_loading is False  # gen2 allowed
