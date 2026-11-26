"""Phase 3 candidates: CV keeps DMADV in training, log loss respects label order,
and C1 / C2 return one label and five probabilities per narrative."""
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from dmaic_planner import phase3_models as pm
from dmaic_planner.schema import METHODOLOGIES

ROOT = Path(__file__).resolve().parents[1]


def labels_40():
    """The training set's shape: 10 / 7 / 12 / 1 / 10."""
    counts = {"JUST_DO_IT": 10, "KAIZEN_EVENT": 7, "DMAIC": 12, "DMADV": 1, "NOT_CPI": 10}
    return np.array([m for m, k in counts.items() for _ in range(k)])


def test_cv_keeps_the_single_dmadv_item_in_training_and_holds_out_the_rest_once_per_seed():
    y = labels_40()
    dmadv = int(np.flatnonzero(y == "DMADV")[0])
    held = Counter()
    for seed, tr, te in pm.cv_splits(y):
        assert dmadv in tr and dmadv not in te
        assert not set(tr) & set(te)
        held.update((seed, int(i)) for i in te)
    assert set(held.values()) == {1}
    assert len(held) == len(pm.CV_SEEDS) * (len(y) - 1)


def test_log_loss_reads_columns_in_methodologies_order():
    y = ["DMADV", "JUST_DO_IT"]
    p = np.full((2, 5), 1e-9)
    p[0, METHODOLOGIES.index("DMADV")] = 1.0
    p[1, METHODOLOGIES.index("JUST_DO_IT")] = 1.0
    assert pm.log_loss(y, p) == pytest.approx(0.0, abs=1e-6)
    assert pm.log_loss(y, np.full((2, 5), 0.2)) == pytest.approx(np.log(5))


def test_softmax_rows_sum_to_one():
    p = pm.softmax(np.array([[0.1, 0.2, 0.3, 0.4, 0.5], [5, 5, 5, 5, 5.0]]) / 0.05)
    assert np.allclose(p.sum(1), 1) and p[0].argmax() == 4


@pytest.fixture(scope="module")
def encoder():
    pytest.importorskip("sentence_transformers")
    try:
        return pm.MiniLMEncoder()
    except OSError as e:  # no network and no cached model
        pytest.skip(f"MiniLM not available: {e}")


TEXTS = ["The printer jams every morning; the fix is to replace the worn roller, which takes ten minutes.",
         "Handoffs between intake and scheduling stall for days and the team roughly knows why.",
         "Claim error rates rose last year and nobody knows the cause. " * 80]  # long: several chunks


def check_output(labels, proba, n):
    assert len(labels) == n and all(l in METHODOLOGIES for l in labels)
    assert proba.shape == (n, len(METHODOLOGIES))
    assert np.allclose(proba.sum(1), 1)
    assert [METHODOLOGIES[i] for i in proba.argmax(1)] == list(labels)


def test_long_narratives_are_chunked_and_vectors_have_unit_length(encoder):
    assert len(encoder.chunks(TEXTS[2])) > 1
    e = encoder.encode(TEXTS)
    assert e.shape == (3, 384) and np.allclose(np.linalg.norm(e, axis=1), 1)


def test_c1_predicts_a_label_and_five_probabilities(encoder):
    check_output(*pm.DefinitionsOnly(encoder, temperature=0.2).predict(TEXTS), 3)


def test_c2_fits_and_predicts_a_label_and_five_probabilities(encoder):
    train = [f"{pm.ROUTE_DEFINITIONS[m]} Example {k}." for m in METHODOLOGIES for k in range(2)]
    y = [m for m in METHODOLOGIES for _ in range(2)]
    model = pm.DefinitionsLogReg(encoder, C=0.1, def_weight=5.0, blend=0.25).fit(train, y)
    check_output(*model.predict(TEXTS), 3)


# --------------------------------------------------------------------------- #
# the deployed model (models/phase3/c2)
# --------------------------------------------------------------------------- #

DEPLOYED = ROOT / "models" / "phase3" / "c2"


def spec():
    import json
    return json.loads((DEPLOYED / "model.json").read_text(encoding="utf-8"))


def test_the_artifact_is_plain_json_with_everything_the_loader_needs():
    assert sorted(p.name for p in DEPLOYED.iterdir()) == ["README.md", "model.json"]  # no pickle
    s = spec()
    assert s["classes"] == METHODOLOGIES
    assert np.asarray(s["logistic_regression"]["coef"]).shape == (5, 384)
    assert len(s["logistic_regression"]["intercept"]) == 5
    assert s["base_model"]["id"] == pm.MODEL_NAME and s["base_model"]["revision"] == pm.MODEL_REVISION
    assert s["route_definitions"] == pm.ROUTE_DEFINITIONS
    assert s["training_data"]["rows"] == 60
    assert "not a held-out test score" in s["evaluation"]["cv_estimate_60"]["note"]
    margins = [t["min_margin"] for t in s["confidence_tiers"]["tiers"]]
    assert margins == sorted(margins, reverse=True) and margins[-1] == 0.0


def test_the_artifact_was_trained_on_the_released_data():
    hashes = spec()["training_data"]["sha256"]
    assert sorted(hashes) == ["test.csv", "train.csv"]
    for name, digest in hashes.items():
        assert pm.sha256(ROOT / "data" / name) == digest, f"data/{name} is not the file the model was trained on"


def test_tiers_keep_a_boundary_only_where_accuracy_rises():
    sure = {"proba": np.array([0.6, 0.1, 0.1, 0.1, 0.1]), "gold": "JUST_DO_IT"}      # right, wide gap
    unsure = {"proba": np.array([0.22, 0.2, 0.2, 0.19, 0.19]), "gold": "KAIZEN_EVENT"}  # wrong, narrow gap
    informative = pm.confidence_tiers([sure] * 30 + [unsure] * 30)
    assert [t["name"] for t in informative["tiers"]] == ["leaning", "toss_up"]
    assert informative["tiers"][0]["oof_accuracy"] == 1.0
    wrong_sure = {**sure, "gold": "DMAIC"}
    right_unsure = {**unsure, "gold": "JUST_DO_IT"}
    flat = pm.confidence_tiers([sure, wrong_sure] * 15 + [unsure, right_unsure] * 15)
    assert [t["name"] for t in flat["tiers"]] == ["low"]


@pytest.fixture(scope="module")
def deployed():
    pytest.importorskip("sentence_transformers")
    try:
        return pm.load_deployed()
    except OSError as e:
        pytest.skip(f"MiniLM not available: {e}")


def test_load_deployed_gives_five_probabilities_that_sum_to_one(deployed):
    assert deployed.version.startswith("c2-all60-")
    out = deployed.predict_proba(TEXTS)
    assert len(out) == 3
    for row in out:
        assert list(row) == METHODOLOGIES
        assert all(0 <= v <= 1 for v in row.values()) and sum(row.values()) == pytest.approx(1, abs=1e-9)
    labels, proba = deployed.predict(TEXTS)
    check_output(labels, proba, 3)
    assert labels == [max(r, key=r.get) for r in out]
    c = deployed.confidence(out[0])
    assert c["tier"] in {t["name"] for t in deployed.tiers} and c["text"]
    assert deployed.predict_proba([]) == []
    with pytest.raises(TypeError):
        deployed.predict_proba([1])
