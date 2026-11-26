"""From raw input to the result the UI and the API both return. No Gradio here,
so it can be tested on its own.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from dmaic_planner.rules_engine import RulesEngine

from app.labels import DISPLAY_NAMES, EXPLANATIONS, NO_TIERS_NOTE, TAGLINES
from app.predictor import Prediction, Predictor, load_predictor
from app.validation import check_narrative

log = logging.getLogger(__name__)


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


class PlannerService:
    def __init__(self, predictor: Predictor | None = None, engine: RulesEngine | None = None):
        self.engine = engine or RulesEngine()
        self.predictor = predictor or load_predictor()

    @property
    def model_version(self) -> str:
        return self.predictor.version

    def warm_up(self) -> None:
        """One throwaway prediction at startup, so the first visitor does not pay
        for lazy initialisation inside the model."""
        self.predictor.predict(["Requests wait in a shared inbox for days before anyone "
                                "picks them up, and nobody is sure why some take weeks."])

    def tier(self, prediction: Prediction) -> dict[str, Any] | None:
        """A plain-language label for how far apart the top two routes are, from the
        model's own cross-validated thresholds; None when the model ships none."""
        tier = self.predictor.tiers.tier_for(prediction) if self.predictor.tiers else None
        if tier is None:
            return None
        (top, _), (second, _) = prediction.top_two()
        names = {"route": DISPLAY_NAMES[top], "second": DISPLAY_NAMES[second]}
        try:
            text = tier.text.format(**names)
        except (KeyError, IndexError, ValueError):
            text = tier.text
        if names["route"] not in text:  # e.g. "Low confidence: compare the top two routes"
            text += f" ({names['route']} and {names['second']})"
        return {"name": tier.name, "text": text, "oof_accuracy": tier.oof_accuracy,
                "top2_oof_accuracy": self.predictor.tiers.top2_oof_accuracy}

    def tools(self, code: str, text: str) -> dict[str, list[str]]:
        # Waste-specific tools only for improvement routes; a Not-CPI request gets
        # a decision memo, not a fishbone diagram.
        wastes = [] if code == "NOT_CPI" else self.engine.waste_evidence(text).top()
        return self.engine.tools_for(code, wastes)

    def classify(self, value: Any) -> dict[str, Any]:
        """Always returns a dict; ok=False carries a message instead of a result."""
        started = time.perf_counter()
        checked = check_narrative(value)
        if not checked.ok:
            return self._error(checked.message, started)
        try:
            t0 = time.perf_counter()
            prediction = self.predictor.predict([checked.text])[0]
            model_ms = (time.perf_counter() - t0) * 1000
            code = prediction.label
            second, second_p = prediction.top_two()[1]
            tier = self.tier(prediction)
            result = {
                "ok": True,
                "route": DISPLAY_NAMES[code],
                "route_code": code,
                "confidence": round(prediction.probabilities[code], 4),
                "confidences": {DISPLAY_NAMES[m]: round(p, 4) for m, p in prediction.probabilities.items()},
                "tier": tier["text"] if tier else None,
                "tier_name": tier["name"] if tier else None,
                "tier_oof_accuracy": _round(tier and tier["oof_accuracy"]),
                "top2_oof_accuracy": _round(tier and tier["top2_oof_accuracy"]),
                "tier_note": "" if tier else NO_TIERS_NOTE,
                "tagline": TAGLINES[code],
                "explanation": EXPLANATIONS[code],
                "runner_up": {
                    "route": DISPLAY_NAMES[second],
                    "route_code": second,
                    "confidence": round(second_p, 4),
                    "tagline": TAGLINES[second],
                    "explanation": EXPLANATIONS[second],
                },
                "tools": self.tools(code, checked.text),
                "note": checked.message,
                "truncated": checked.truncated,
                "model_version": self.model_version,
                "placeholder": self.predictor.is_placeholder,
                "model_ms": round(model_ms, 1),
            }
        except Exception:  # never show a stack trace to a user
            log.exception("prediction failed")
            return self._error("Something went wrong on our side while scoring this narrative. "
                               "Please try again; if it keeps happening, try a shorter version.", started)
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
        return result

    def _error(self, message: str, started: float) -> dict[str, Any]:
        return {
            "ok": False,
            "error": message,
            "model_version": self.model_version,
            "placeholder": self.predictor.is_placeholder,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        }
