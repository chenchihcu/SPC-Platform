from app.services import chart_render
from app.services.chart_render import _RENDERERS


def test_renderers_include_3f_parallel_charts() -> None:
    required = {"imr_3f", "run_chart_3f", "ewma_3f", "cusum_3f", "boxplot_3f"}
    assert required.issubset(set(_RENDERERS.keys()))


def test_render_chart_uses_shared_resolver_and_feature_context(monkeypatch) -> None:
    called = {}

    def _fake_resolver(payload, chart_id, features=None, normalized=False, context="report"):
        called["chart_id"] = chart_id
        called["features"] = features
        called["context"] = context
        return {"metadata": {"is_valid": True}, "data": {}, "statistics": {}, "analysis_context": {}, "chart_type": chart_id}

    def _fake_renderer(slice_data):
        assert slice_data["metadata"]["is_valid"] is True
        return b"ok"

    monkeypatch.setattr(chart_render, "resolve_chart_payload", _fake_resolver)
    monkeypatch.setitem(chart_render._RENDERERS, "run_chart_3f", _fake_renderer)

    out = chart_render.render_chart_to_png_bytes(
        "run_chart_3f",
        {"selected_features": ["Volume"]},
        features=["Volume", "Area", "Height"],
        context="report",
    )
    assert out == b"ok"
    assert called["chart_id"] == "run_chart_3f"
    assert called["features"] == ["Volume", "Area", "Height"]
    assert called["context"] == "report"


class _DummyCanvas:
    def __init__(self, hidden: bool) -> None:
        self._hidden = hidden

    def isHidden(self) -> bool:
        return self._hidden


class _DummyFigure:
    def __init__(self) -> None:
        self.savefig_called = False

    def savefig(self, buf, format="png", dpi=100, bbox_inches="tight") -> None:
        self.savefig_called = True
        try:
            from PIL import Image, ImageDraw  # type: ignore[import-untyped]

            img = Image.new("RGB", (32, 24), (255, 255, 255))
            draw = ImageDraw.Draw(img)
            draw.line([(2, 2), (30, 20)], fill=(10, 10, 10), width=2)
            img.save(buf, format="PNG")
        except Exception:
            buf.write(b"png")


def test_canvas_has_drawn_content_for_base_chart_like_widget() -> None:
    w = type("W", (), {})()
    w.canvas = _DummyCanvas(hidden=False)
    assert chart_render._canvas_has_drawn_content(w) is True
    w.canvas = _DummyCanvas(hidden=True)
    assert chart_render._canvas_has_drawn_content(w) is False


def test_canvas_has_drawn_content_for_tab_chart_view_widget() -> None:
    chart_view = type("CV", (), {})()
    chart_view.canvas = _DummyCanvas(hidden=True)
    w = type("W", (), {})()
    w.chart_view = chart_view
    assert chart_render._canvas_has_drawn_content(w) is False

    chart_view.canvas = _DummyCanvas(hidden=False)
    assert chart_render._canvas_has_drawn_content(w) is True


def test_render_single_chart_returns_none_when_canvas_hidden() -> None:
    class _HiddenChart:
        def __init__(self, parent=None) -> None:
            self.canvas = _DummyCanvas(hidden=True)
            self.figure = _DummyFigure()

        def draw_chart(self, payload) -> None:
            return None

    out = chart_render._render_single_chart(
        _HiddenChart,
        {"metadata": {"is_valid": True}, "data": {}},
    )
    assert out is None


def test_render_single_chart_renders_when_canvas_visible() -> None:
    class _VisibleChart:
        def __init__(self, parent=None) -> None:
            self.canvas = _DummyCanvas(hidden=False)
            self.figure = _DummyFigure()

        def draw_chart(self, payload) -> None:
            return None

    out = chart_render._render_single_chart(
        _VisibleChart,
        {"metadata": {"is_valid": True}, "data": {}},
    )
    assert out is not None
    assert out.startswith(b"\x89PNG\r\n\x1a\n")


def test_png_has_visual_content_detects_blank_and_non_blank_images() -> None:
    try:
        from PIL import Image, ImageDraw  # type: ignore[import-untyped]
    except Exception:
        # Environment without Pillow: function intentionally degrades to permissive True.
        assert chart_render._png_has_visual_content(b"fake-bytes") is True
        return

    from io import BytesIO

    white = Image.new("RGB", (100, 80), (255, 255, 255))
    white_buf = BytesIO()
    white.save(white_buf, format="PNG")
    assert chart_render._png_has_visual_content(white_buf.getvalue()) is False

    non_blank = Image.new("RGB", (100, 80), (255, 255, 255))
    draw = ImageDraw.Draw(non_blank)
    draw.line([(5, 5), (95, 70)], fill=(20, 20, 20), width=3)
    non_blank_buf = BytesIO()
    non_blank.save(non_blank_buf, format="PNG")
    assert chart_render._png_has_visual_content(non_blank_buf.getvalue()) is True
