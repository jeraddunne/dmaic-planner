"""The web app's input checks, predictor contract and result shape (app/).

Runs without Gradio. The UI and the live API are tested in app/tests/ with the app's
own environment (app/requirements.txt).
"""
from __future__ import annotations

import csv
import math
import re
import sys
import types
from pathlib import Path

import pytest

from app.examples import EXAMPLES
from app.labels import CONFIDENCE_NOTE, DISCLAIMER, DISPLAY_NAMES, EXPLANATIONS, TAGLINES
from app.predictor import (
    DEFAULT_MODEL, ConfidenceTiers, ModelAdapter, PlaceholderPredictor, Prediction, Predictor, load_predictor,
)
from app.service import PlannerService
from app.validation import MAX_CHARS, MIN_WORDS, REJECT_CHARS, check_narrative, count_words
from dmaic_planner.schema import METHODOLOGIES

ROOT = Path(__file__).resolve().parents[1]
GOOD = ("Invoices wait two weeks in the approval queue and about a quarter come back for "
        "missing receipts, and nobody knows why some approvers are much slower than others.")


@pytest.fixture(scope="module")
def service() -> PlannerService:
    return PlannerService(PlaceholderPredictor())


# --------------------------------------------------------------------------- #
# input checks
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("value", [None, "", "   ", "\n\t \n"])
def test_empty_input_is_refused_with_a_message(value):
    checked = check_narrative(value)
    assert not checked.ok and checked.message


@pytest.mark.parametrize("value", [42, 3.5, True, {"text": GOOD}, b"bytes", [1, 2], ["a", "b"], object()])
def test_wrong_type_is_refused_and_names_the_type(value):
    checked = check_narrative(value)
    assert not checked.ok
    assert "text" in checked.message and type(value).__name__ in checked.message


def test_a_one_item_list_of_text_is_accepted():
    assert check_narrative([GOOD]).text == GOOD


def test_minimum_length_is_counted_in_words_with_letters():
    assert count_words("1 2 3 -- ... abc d4") == 2
    assert not check_narrative(" ".join(["word"] * (MIN_WORDS - 1))).ok
    assert check_narrative(" ".join(["word"] * MIN_WORDS)).ok
    assert not check_narrative(" ".join(["123"] * 40)).ok


def test_too_short_message_says_how_many_words():
    checked = check_narrative("The form is broken.")
    assert not checked.ok and "4 words" in checked.message and str(MIN_WORDS) in checked.message


def test_control_characters_are_removed():
    checked = check_narrative(GOOD.replace(" ", "\x00 ", 3))
    assert checked.ok and "\x00" not in checked.text


def test_text_at_the_limit_is_used_whole():
    text = ("abcd " * (MAX_CHARS // 5))[:MAX_CHARS]
    checked = check_narrative(text)
    assert checked.ok and not checked.truncated and not checked.message


def test_long_text_is_cut_on_a_word_boundary_with_a_note():
    text = "alpha beta gamma " * 600  # about 10,200 characters
    checked = check_narrative(text)
    assert checked.ok and checked.truncated
    assert len(checked.text) <= MAX_CHARS
    assert checked.text.split()[-1] in {"alpha", "beta", "gamma"}
    assert f"{len(text.strip()):,}" in checked.message


def test_a_whole_document_is_refused():
    checked = check_narrative("word " * (REJECT_CHARS // 5 + 10))
    assert not checked.ok and "document" in checked.message


# --------------------------------------------------------------------------- #
# predictor contract
# --------------------------------------------------------------------------- #

def test_prediction_label_is_always_the_top_route():
    p = Prediction.from_scores([1, 5, 2, 0, 2])
    assert p.label == "KAIZEN_EVENT"
    assert list(p.probabilities) == METHODOLOGIES
    assert math.isclose(sum(p.probabilities.values()), 1.0)
    assert Prediction.from_scores({m: i + 1 for i, m in enumerate(METHODOLOGIES)}).label == "NOT_CPI"


@pytest.mark.parametrize("scores", [[1, 2, 3], [0, 0, 0, 0, 0], [1, -1, 1, 1, 1],
                                    [1, float("nan"), 1, 1, 1], {"DMAIC": 1.0}])
def test_prediction_rejects_malformed_scores(scores):
    with pytest.raises(ValueError):
        Prediction.from_scores(scores)


def test_placeholder_predictor_contract():
    predictor = PlaceholderPredictor()
    assert isinstance(predictor, Predictor) and predictor.is_placeholder
    assert "placeholder" in predictor.version.lower()
    texts = [text for _, text in EXAMPLES]
    preds = predictor.predict(texts)
    assert len(preds) == len(texts)
    for p in preds:
        assert p.label in METHODOLOGIES
        assert list(p.probabilities) == METHODOLOGIES
        assert math.isclose(sum(p.probabilities.values()), 1.0)
        assert all(v > 0 for v in p.probabilities.values())
        assert p.label == max(p.probabilities, key=p.probabilities.get)


class FakePhase3Model:
    """The phase3_models shape: predict(texts) -> (labels, rows in METHODOLOGIES order)."""
    name = "fake_phase3"

    def predict(self, texts):
        rows = [[0.1, 0.2, 0.4, 0.1, 0.2] for _ in texts]
        return ["DMAIC"] * len(texts), rows


def test_adapter_wraps_the_phase3_shape():
    preds = ModelAdapter(FakePhase3Model()).predict(["one", "two"])
    assert [p.label for p in preds] == ["DMAIC", "DMAIC"]
    assert math.isclose(preds[0].probabilities["DMAIC"], 0.4)


class FakeDeployedModel:
    """The load_deployed shape: .version and predict_proba(texts) -> [{code: p}, ...]."""
    version = "fake-c2"

    def __init__(self, path=None, threads=None):
        self.path, self.threads = path, threads

    def predict_proba(self, texts):
        return [{"JUST_DO_IT": 0.05, "KAIZEN_EVENT": 0.35, "DMAIC": 0.45, "DMADV": 0.05, "NOT_CPI": 0.10}
                for _ in texts]


def test_adapter_prefers_predict_proba_dicts():
    adapter = ModelAdapter(FakeDeployedModel())
    p = adapter.predict(["one"])[0]
    assert adapter.version == "fake-c2" and p.label == "DMAIC"
    assert p.top_two() == [("DMAIC", pytest.approx(0.45)), ("KAIZEN_EVENT", pytest.approx(0.35))]


def test_adapter_refuses_a_row_count_mismatch():
    class Broken(FakePhase3Model):
        def predict(self, texts):
            return ["DMAIC"], [[0.2] * 5]
    with pytest.raises(ValueError):
        ModelAdapter(Broken()).predict(["one", "two"])


def test_c2_loads_through_load_deployed(monkeypatch, tmp_path):
    import app.predictor as predictor_module
    import dmaic_planner
    (tmp_path / "model.json").write_text("{}", encoding="utf-8")
    fake = types.SimpleNamespace(load_deployed=FakeDeployedModel)
    monkeypatch.setitem(sys.modules, "dmaic_planner.phase3_models", fake)
    monkeypatch.setattr(dmaic_planner, "phase3_models", fake, raising=False)
    monkeypatch.setattr(predictor_module, "C2_DIR", tmp_path)
    predictor = load_predictor("c2")
    assert predictor.version == "fake-c2" and not predictor.is_placeholder
    assert predictor.model.path == str(tmp_path)
    assert predictor.predict([GOOD])[0].label == "DMAIC"


def test_c2_without_its_file_says_what_is_missing(monkeypatch, tmp_path):
    import app.predictor as predictor_module
    monkeypatch.setattr(predictor_module, "C2_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="model.json"):
        load_predictor("c2")


# --------------------------------------------------------------------------- #
# confidence tiers (thresholds come from model.json, never from the app)
# --------------------------------------------------------------------------- #

TIER_SPEC = {"confidence_tiers": {"tiers": [
    {"name": "toss_up", "text": "Toss-up: compare the top two", "min_margin": 0.0, "oof_accuracy": 0.36},
    {"name": "leaning", "text": "Leaning {route}", "min_margin": 0.0625, "oof_accuracy": 0.33},
], "top2_oof_accuracy": 0.63}}


@pytest.mark.parametrize("spec", [{}, {"confidence_tiers": {}}, {"confidence_tiers": {"tiers": []}}])
def test_no_tiers_in_the_file_means_no_tier(spec):
    assert ConfidenceTiers.from_spec(spec) is None


def test_tier_is_chosen_by_the_gap_between_the_top_two():
    tiers = ConfidenceTiers.from_spec(TIER_SPEC)
    lean = Prediction.from_scores([0.10, 0.20, 0.40, 0.10, 0.20])   # gap 0.20
    toss = Prediction.from_scores([0.10, 0.29, 0.31, 0.10, 0.20])   # gap 0.02
    edge = Prediction.from_scores([0.125, 0.25, 0.3125, 0.0625, 0.25])  # gap exactly 1/16 (exact in binary)
    assert tiers.tier_for(lean).name == "leaning"
    assert tiers.tier_for(toss).name == "toss_up"
    assert tiers.tier_for(edge).name == "leaning"


def _tiered_service(spec=TIER_SPEC) -> PlannerService:
    return PlannerService(ModelAdapter(FakeDeployedModel(), name="c2", tiers=ConfidenceTiers.from_spec(spec)))


def test_tier_text_uses_route_names_and_names_both_routes_in_a_toss_up():
    service = _tiered_service()
    r = service.classify(GOOD)  # fake model: DMAIC 0.45, Kaizen Event 0.35, gap 0.10
    assert r["tier"] == "Leaning DMAIC" and r["tier_name"] == "leaning"
    assert r["tier_oof_accuracy"] == 0.33 and r["top2_oof_accuracy"] == 0.63 and r["tier_note"] == ""
    toss_spec = {"confidence_tiers": {"tiers": [dict(TIER_SPEC["confidence_tiers"]["tiers"][0])]}}
    r = _tiered_service(toss_spec).classify(GOOD)
    assert r["tier"] == "Toss-up: compare the top two (DMAIC and Kaizen Event)"
    assert r["top2_oof_accuracy"] is None


def test_percentages_are_shown_exactly_as_the_model_gives_them():
    r = _tiered_service().classify(GOOD)
    assert r["confidences"] == {"Just Do It": 0.05, "Kaizen Event": 0.35, "DMAIC": 0.45, "DMADV": 0.05,
                                "Not a CPI project": 0.1}


C2_JSON = ROOT / "models" / "phase3" / "c2" / "model.json"


@pytest.mark.skipif(not C2_JSON.exists(), reason="models/phase3/c2/model.json not built yet")
def test_app_tiers_match_the_shipped_model():
    """The app picks the same tier as DeployedModel.confidence for the real thresholds."""
    import json
    from dmaic_planner import phase3_models as p3
    spec = json.loads(C2_JSON.read_text(encoding="utf-8"))
    tiers = ConfidenceTiers.from_spec(spec)
    assert tiers is not None
    shipped = object.__new__(p3.DeployedModel)  # only .tiers is needed; skips the encoder
    shipped.tiers = spec["confidence_tiers"]["tiers"]
    for gap in (0.0, 0.005, 0.0170, 0.0171, 0.02, 0.1, 0.5):
        probs = {"JUST_DO_IT": 0.1, "KAIZEN_EVENT": 0.3 - gap / 2, "DMAIC": 0.3 + gap / 2, "DMADV": 0.1, "NOT_CPI": 0.2}
        assert tiers.tier_for(Prediction.from_scores(probs)).name == shipped.confidence(probs)["tier"]


@pytest.mark.skipif(not C2_JSON.exists(), reason="models/phase3/c2/model.json not built yet")
def test_the_training_count_in_the_text_matches_the_model():
    import json
    rows = json.loads(C2_JSON.read_text(encoding="utf-8"))["training_data"]["rows"]
    assert f"{rows} labeled public narratives" in CONFIDENCE_NOTE
    assert f"{rows} public process-problem narratives" in DISCLAIMER


def test_loader_falls_back_to_the_default_model(monkeypatch):
    import app.predictor as predictor_module
    monkeypatch.delenv("DMAIC_MODEL", raising=False)
    monkeypatch.setattr(predictor_module, "DEFAULT_MODEL", "placeholder")
    assert load_predictor().is_placeholder


def test_loader_reads_the_environment_variable(monkeypatch):
    monkeypatch.setitem(sys.modules, "fake_models", types.SimpleNamespace(make=FakePhase3Model))
    monkeypatch.setenv("DMAIC_MODEL", "fake_models:make")
    predictor = load_predictor()
    assert isinstance(predictor, ModelAdapter) and not predictor.is_placeholder
    assert predictor.predict([GOOD])[0].label == "DMAIC"


@pytest.mark.parametrize("spec", ["no-such-model", "fake_missing_module:make", "app.predictor:no_such_factory"])
def test_loader_explains_an_unknown_model(spec):
    with pytest.raises(ValueError, match="DMAIC_MODEL"):
        load_predictor(spec)


def test_deploy_scripts_can_read_the_default_model_line():
    source = (ROOT / "app" / "predictor.py").read_text(encoding="utf-8")
    assert re.findall(r'^DEFAULT_MODEL = "([^"]+)"', source, re.MULTILINE) == [DEFAULT_MODEL]


# --------------------------------------------------------------------------- #
# what the app returns
# --------------------------------------------------------------------------- #

def test_result_uses_names_not_codes_and_covers_all_routes(service):
    r = service.classify(GOOD)
    assert r["ok"] and r["route"] in DISPLAY_NAMES.values()
    assert r["route"] == DISPLAY_NAMES[r["route_code"]]
    assert set(r["confidences"]) == set(DISPLAY_NAMES.values())
    assert math.isclose(sum(r["confidences"].values()), 1.0, abs_tol=1e-3)
    assert r["confidence"] == max(r["confidences"].values())
    assert r["explanation"] == EXPLANATIONS[r["route_code"]]
    assert r["tools"] and all(isinstance(v, list) and v for v in r["tools"].values())
    assert r["placeholder"] and "placeholder" in r["model_version"].lower()
    assert r["latency_ms"] >= r["model_ms"] >= 0


def test_result_names_the_runner_up(service):
    r = service.classify(GOOD)
    runner = r["runner_up"]
    assert runner["route_code"] != r["route_code"]
    assert runner["confidence"] == sorted(r["confidences"].values())[-2]
    assert runner["explanation"] == EXPLANATIONS[runner["route_code"]]


def test_a_model_without_tiers_shows_percentages_with_a_note(service):
    r = service.classify(GOOD)
    assert r["tier"] is None and r["tier_note"]


@pytest.mark.parametrize("value", [None, "", "   ", "too short", 7, {"a": 1}, "word " * (REJECT_CHARS // 4)],
                         ids=["none", "empty", "spaces", "short", "int", "dict", "document"])
def test_bad_input_returns_a_message_not_an_exception(service, value):
    r = service.classify(value)
    assert r["ok"] is False and r["error"] and "Traceback" not in r["error"]
    assert "latency_ms" in r and "model_version" in r


def test_truncation_note_reaches_the_result(service):
    r = service.classify(GOOD + " more detail" * 600)
    assert r["ok"] and r["truncated"] and "were used" in r["note"]


def test_a_model_crash_becomes_a_friendly_message():
    class Exploding(PlaceholderPredictor):
        def predict(self, texts):
            raise RuntimeError("secret internal detail")
    r = PlannerService(Exploding()).classify(GOOD)
    assert r["ok"] is False and "secret" not in r["error"] and "try again" in r["error"]


def test_not_cpi_gets_route_tools_only(service):
    tools = service.tools("NOT_CPI", GOOD)
    assert "Waste-specific" not in tools and tools
    assert "Waste-specific" in service.tools("DMAIC", GOOD)


# --------------------------------------------------------------------------- #
# labels and examples
# --------------------------------------------------------------------------- #

def test_every_route_has_a_name_tagline_and_one_paragraph():
    assert set(DISPLAY_NAMES) == set(TAGLINES) == set(EXPLANATIONS) == set(METHODOLOGIES)
    assert DISPLAY_NAMES["NOT_CPI"] != "NOT_CPI" and DISPLAY_NAMES["JUST_DO_IT"] != "JUST_DO_IT"
    for text in EXPLANATIONS.values():
        assert "\n" not in text and 40 <= len(text.split()) <= 120


def test_examples_are_valid_inputs():
    assert len(EXAMPLES) >= 3
    for _, text in EXAMPLES:
        checked = check_narrative(text)
        assert checked.ok and not checked.truncated


def _shingles(text: str, n: int = 8) -> set:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


@pytest.mark.parametrize("split", ["train", "test"])
def test_examples_are_not_copied_from_the_dataset(split):
    path = ROOT / "data" / f"{split}.csv"
    with path.open(encoding="utf-8", newline="") as fh:
        dataset = set().union(*(_shingles(row["text"]) for row in csv.DictReader(fh)))
    for title, text in EXAMPLES:
        assert not (_shingles(text) & dataset), f"example {title!r} shares 8 words in a row with {split}.csv"
