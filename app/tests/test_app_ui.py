"""The Gradio app and its API, end to end on a local port.

Needs the app environment (pip install -r app/requirements.txt):
    python -m pytest -q app/tests
"""
from __future__ import annotations

import json
import math
import socket
from pathlib import Path

import pytest

gr = pytest.importorskip("gradio")
gradio_client = pytest.importorskip("gradio_client")

from app.examples import EXAMPLES  # noqa: E402
from app.main import build_demo, render  # noqa: E402
from app.predictor import PlaceholderPredictor  # noqa: E402
from app.service import PlannerService  # noqa: E402

GOOD = EXAMPLES[0][1]


@pytest.fixture(scope="module")
def service() -> PlannerService:
    return PlannerService(PlaceholderPredictor())


@pytest.fixture(scope="module")
def client(service):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    demo = build_demo(service)
    demo.launch(server_name="127.0.0.1", server_port=port, prevent_thread_lock=True, quiet=True)
    try:
        yield gradio_client.Client(f"http://127.0.0.1:{port}/", verbose=False)
    finally:
        demo.close()


def test_render_ok_result(service):
    headline, confidences, explanation, tools, footer = render(service.classify(GOOD))
    assert headline.startswith("### Recommended route:") and "Top two:" in headline
    assert len(confidences) == 5
    assert explanation.startswith("#### What ")
    assert "☐" in tools and "Starter tools checklist" in tools
    assert " ms" in footer and "Model version" in footer


def test_render_error_result(service):
    headline, confidences, explanation, tools, footer = render(service.classify("   "))
    assert "Please check your input" in headline
    assert confidences is None and explanation == "" and tools == ""


def test_api_exposes_one_named_endpoint(client):
    endpoints = client.view_api(print_info=False, return_format="dict")["named_endpoints"]
    assert list(endpoints) == ["/predict"]


def test_api_returns_a_result(client):
    result = client.predict(GOOD, api_name="/predict")
    assert result["ok"] is True
    assert set(result["confidences"]) == {"Just Do It", "Kaizen Event", "DMAIC", "DMADV", "Not a CPI project"}
    assert result["tools"]


@pytest.mark.parametrize("value", ["", "too short", 12345, ["not", "text"], {"text": "x"}],
                         ids=["empty", "short", "int", "list", "dict"])
def test_api_bad_input_gets_a_message(client, value):
    result = client.predict(value, api_name="/predict")
    assert result["ok"] is False and result["error"] and "Traceback" not in result["error"]


C2_JSON = Path(__file__).resolve().parents[2] / "models" / "phase3" / "c2" / "model.json"


@pytest.mark.skipif(not C2_JSON.exists(), reason="models/phase3/c2/model.json not built yet")
def test_the_deployed_model_end_to_end():
    pytest.importorskip("sentence_transformers")
    from app.predictor import load_predictor
    service = PlannerService(load_predictor("c2"))
    result = service.classify(GOOD)
    assert result["ok"] and not result["placeholder"]
    assert result["model_version"] == json.loads(C2_JSON.read_text(encoding="utf-8"))["version"]
    assert math.isclose(sum(result["confidences"].values()), 1.0, abs_tol=1e-3)
    headline = render(result)[0]
    assert result["tier"] and result["tier"] in headline and "Top two:" in headline
