"""The one question the app asks a model: for these narratives, how likely is each
of the five routes? Everything else (names, explanations, tools) is the app's job.

Which backend runs is set by the DMAIC_MODEL environment variable, falling back to
DEFAULT_MODEL below:

  c2                    The deployed model: Phase 3 candidate C2 refit on all 60
                        labeled narratives (MiniLM embeddings + class-balanced
                        logistic regression with the route definitions, blended).
                        Loaded by phase3_models.load_deployed from models/phase3/c2/.
  placeholder           PLACEHOLDER. The project's keyword rules (rules/), not a
                        trained model. For tests, and for checking a deployment
                        without the model.
  package.module:name   Any zero-argument callable returning a model with
                        predict_proba(texts) -> one {route code: probability} per
                        text, or predict(texts) -> (labels, probability rows).

DMAIC_THREADS caps the CPU threads PyTorch uses (default: the CPUs this process may
use, at most 4). The deploy scripts set it to the Cloud Run CPU count.
"""
from __future__ import annotations

import importlib
import json
import logging
import math
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from dmaic_planner.schema import METHODOLOGIES

# The one line to change to switch models. The deploy scripts read it.
DEFAULT_MODEL = "c2"

ROOT = Path(__file__).resolve().parents[1]
C2_DIR = ROOT / "models" / "phase3" / "c2"

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Prediction:
    """One narrative's result. label is always the highest-probability route, so
    the headline and the bar chart can never disagree."""
    label: str
    probabilities: dict[str, float]  # all five routes, in METHODOLOGIES order, sum to 1

    @classmethod
    def from_scores(cls, scores: Mapping[str, float] | Sequence[float]) -> "Prediction":
        if isinstance(scores, Mapping):
            missing = [m for m in METHODOLOGIES if m not in scores]
            if missing:
                raise ValueError(f"scores are missing routes {missing}")
            values = [float(scores[m]) for m in METHODOLOGIES]
        else:
            values = [float(v) for v in scores]
            if len(values) != len(METHODOLOGIES):
                raise ValueError(f"expected {len(METHODOLOGIES)} scores, got {len(values)}")
        if any(not math.isfinite(v) or v < 0 for v in values):
            raise ValueError(f"scores must be finite and non-negative, got {values}")
        total = sum(values)
        if total <= 0:
            raise ValueError("scores sum to zero")
        probs = {m: v / total for m, v in zip(METHODOLOGIES, values)}
        return cls(label=max(probs, key=probs.get), probabilities=probs)

    def top_two(self) -> list[tuple[str, float]]:
        return sorted(self.probabilities.items(), key=lambda kv: -kv[1])[:2]


@dataclass(frozen=True)
class Tier:
    name: str                     # e.g. "leaning", "toss_up"
    text: str                     # template; {route} = the top route's name
    min_margin: float             # applies when top-1 minus top-2 probability is at least this
    oof_accuracy: float | None    # how often the top route was right in this tier, out of fold


class ConfidenceTiers:
    """Plain-language labels for the gap between the top two probabilities, with the
    thresholds the model was shipped with (model.json "confidence_tiers"). The app
    never invents thresholds: no tiers in the file means no label."""

    def __init__(self, tiers: Sequence[Tier], top2_oof_accuracy: float | None = None):
        if not tiers:
            raise ValueError("no tiers")
        self.tiers = sorted(tiers, key=lambda t: -t.min_margin)
        self.top2_oof_accuracy = top2_oof_accuracy  # how often the right route was in the top two

    @classmethod
    def from_spec(cls, spec: Mapping[str, Any]) -> "ConfidenceTiers | None":
        block = spec.get("confidence_tiers")
        if not isinstance(block, Mapping) or not block.get("tiers"):
            return None
        top2 = block.get("top2_oof_accuracy")
        return cls([Tier(name=str(t["name"]), text=str(t["text"]), min_margin=float(t["min_margin"]),
                         oof_accuracy=None if t.get("oof_accuracy") is None else float(t["oof_accuracy"]))
                    for t in block["tiers"]], top2_oof_accuracy=None if top2 is None else float(top2))

    def tier_for(self, prediction: "Prediction") -> Tier | None:
        (_, p1), (_, p2) = prediction.top_two()
        return next((t for t in self.tiers if p1 - p2 >= t.min_margin), None)


class Predictor(ABC):
    name: str = "predictor"
    version: str = "unknown"
    is_placeholder: bool = False
    tiers: ConfidenceTiers | None = None

    @abstractmethod
    def predict(self, texts: Sequence[str]) -> list[Prediction]:
        """One Prediction per text, in order."""


class PlaceholderPredictor(Predictor):
    """PLACEHOLDER: the rules engine's routing decision dressed as probabilities.

    Not a trained model and not a candidate. The rule decision gets a fixed bonus
    so it is always the top route; other routes share what is left in proportion
    to the votes their rules cast, plus a small floor so no route shows 0%.
    """

    name = "placeholder"
    version = "placeholder-rules-v1 (keyword rules in rules/; NOT the trained model)"
    is_placeholder = True

    def __init__(self, engine=None):
        from dmaic_planner.rules_engine import RulesEngine
        self.engine = engine or RulesEngine()

    def predict(self, texts: Sequence[str]) -> list[Prediction]:
        out = []
        for text in texts:
            decision = self.engine.route(text)
            scores = {m: 0.1 + decision.votes.get(m, 0.0) for m in METHODOLOGIES}
            scores[decision.label] += 1.0
            out.append(Prediction.from_scores(scores))
        return out


class ModelAdapter(Predictor):
    """Wraps a model object. Uses predict_proba(texts) -> one {code: p} (or one row in
    METHODOLOGIES order) per text if the model has it, else predict(texts) ->
    (labels, rows). Rows are renormalised; the label shown is their argmax."""

    def __init__(self, model: Any, name: str | None = None, version: str | None = None,
                 tiers: ConfidenceTiers | None = None):
        if not any(callable(getattr(model, m, None)) for m in ("predict_proba", "predict")):
            raise TypeError(f"{type(model).__name__} has neither predict_proba(texts) nor predict(texts)")
        self.model = model
        self.name = name or getattr(model, "name", type(model).__name__)
        self.version = version or getattr(model, "version", None) or self.name
        self.tiers = tiers

    def predict(self, texts: Sequence[str]) -> list[Prediction]:
        texts = list(texts)
        if callable(getattr(self.model, "predict_proba", None)):
            rows = self.model.predict_proba(texts)
        else:
            result = self.model.predict(texts)
            rows = result[1] if isinstance(result, tuple) and len(result) == 2 else result
        rows = rows.tolist() if hasattr(rows, "tolist") else list(rows)
        if len(rows) != len(texts):
            raise ValueError(f"model returned {len(rows)} rows for {len(texts)} texts")
        return [Prediction.from_scores(r) for r in rows]


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #

def cpu_threads(cap: int = 4) -> int:
    configured = os.environ.get("DMAIC_THREADS", "").strip()
    if configured:
        return max(1, int(configured))
    try:
        available = len(os.sched_getaffinity(0))
    except AttributeError:  # Windows and macOS
        available = os.cpu_count() or 1
    return max(1, min(cap, available))


def _load_c2() -> Predictor:
    from dmaic_planner import phase3_models as p3
    spec_path = C2_DIR / "model.json"
    if not spec_path.is_file():
        raise FileNotFoundError(f"{spec_path} is missing; the c2 model cannot load.")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    model = p3.load_deployed(str(C2_DIR), threads=cpu_threads())
    return ModelAdapter(model, name="c2", tiers=ConfidenceTiers.from_spec(spec))


BUILTIN: dict[str, Callable[[], Predictor]] = {
    "c2": _load_c2,
    "placeholder": PlaceholderPredictor,
}


def _load_factory(spec: str) -> Predictor:
    module_name, _, attr = spec.partition(":")
    try:
        factory = getattr(importlib.import_module(module_name), attr)
    except (ImportError, AttributeError) as e:
        raise ValueError(f"DMAIC_MODEL={spec!r}: cannot import {attr!r} from {module_name!r} ({e})") from e
    model = factory()
    return model if isinstance(model, Predictor) else ModelAdapter(model, name=spec)


def model_spec() -> str:
    return (os.environ.get("DMAIC_MODEL") or DEFAULT_MODEL).strip()


def load_predictor(spec: str | None = None) -> Predictor:
    spec = (spec or model_spec()).strip()
    if spec in BUILTIN:
        predictor = BUILTIN[spec]()
    elif ":" in spec:
        predictor = _load_factory(spec)
    else:
        raise ValueError(
            f"Unknown DMAIC_MODEL {spec!r}. Use one of {sorted(BUILTIN)} "
            "or 'package.module:factory'.")
    log.info("loaded model %s: %s", spec, predictor.version)
    return predictor
