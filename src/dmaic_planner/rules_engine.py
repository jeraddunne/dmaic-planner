"""
Rules engine: applies the waste lexicon and the methodology routing rules.

Two jobs:
  1. Produce a transparent rule-based decision with an explanation (which rules fired).
  2. Produce numeric features (lexicon scores, rule votes) that the learned model
     consumes. This is the Ch. 4 pattern: hand-built lexicon counts become x_i,
     and logistic regression learns how much to trust each one.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from .schema import Intake, METHODOLOGIES, WASTES

RULES_DIR = Path(__file__).resolve().parents[2] / "rules"


@dataclass
class WasteEvidence:
    scores: Dict[str, float]            # weighted evidence per waste
    counts: Dict[str, int]              # number of pattern hits per waste
    fired: List[Tuple[str, str, str]]   # (rule_id, label, matched_text)

    def top(self, threshold: float = 3.0) -> List[str]:
        return [w for w, s in sorted(self.scores.items(), key=lambda kv: -kv[1]) if s >= threshold]


@dataclass
class MethodologyDecision:
    label: str
    confidence: float
    rule_id: str
    rationale: str
    votes: Dict[str, float]             # summed confidence per label across all fired rules
    fired: List[str] = field(default_factory=list)
    needs_review: bool = False


class RulesEngine:
    def __init__(self, rules_dir: Path = RULES_DIR):
        self.rules_dir = Path(rules_dir)
        self.waste_cfg = yaml.safe_load((self.rules_dir / "waste_lexicon.yaml").read_text(encoding="utf-8"))
        self.method_cfg = yaml.safe_load((self.rules_dir / "methodology_rules.yaml").read_text(encoding="utf-8"))
        self.tool_map = yaml.safe_load((self.rules_dir / "tool_map.yaml").read_text(encoding="utf-8"))

        self.waste_rules = []
        for r in self.waste_cfg["rules"]:
            if r.get("status", "active") != "active":
                continue
            compiled = [re.compile(p, re.IGNORECASE) for p in r["patterns"]]
            self.waste_rules.append((r["id"], r["label"], float(r.get("weight", 1)), compiled))

        self.method_rules = sorted(
            [r for r in self.method_cfg["rules"] if r.get("status", "active") == "active"],
            key=lambda r: r["priority"],
        )
        for r in self.method_rules:
            for clause in r.get("when", []):
                if "text" in clause:
                    clause["_re"] = re.compile(clause["text"], re.IGNORECASE)

    # ---------------- waste lexicon ----------------
    def waste_evidence(self, text: str) -> WasteEvidence:
        scores = {w: 0.0 for w in WASTES}
        counts = {w: 0 for w in WASTES}
        fired = []
        for rule_id, label, weight, patterns in self.waste_rules:
            for pat in patterns:
                for m in pat.finditer(text):
                    scores[label] += weight
                    counts[label] += 1
                    fired.append((rule_id, label, m.group(0)))
        return WasteEvidence(scores=scores, counts=counts, fired=fired)

    # ---------------- methodology routing ----------------
    def _clause_holds(self, clause: dict, text: str, intake: Intake, evidence: WasteEvidence) -> bool:
        if "field" in clause:
            value = getattr(intake, clause["field"], "unsure")
            allowed = ["yes" if v is True else "no" if v is False else str(v) for v in clause["in"]]
            return value in allowed
        if "text" in clause:
            return clause["_re"].search(text) is not None
        if "waste_any" in clause:
            return any(evidence.scores[w] >= clause.get("min_score", 1) for w in clause["waste_any"])
        raise ValueError(f"unknown clause {clause}")

    def route(self, text: str, intake: Optional[Intake] = None,
              evidence: Optional[WasteEvidence] = None) -> MethodologyDecision:
        intake = intake or Intake()
        evidence = evidence or self.waste_evidence(text)
        votes = {m: 0.0 for m in METHODOLOGIES}
        fired: List[dict] = []
        for rule in self.method_rules:
            clauses = rule.get("when", [])
            if clauses and not all(self._clause_holds(c, text, intake, evidence) for c in clauses):
                continue
            if not clauses and fired:          # fallback only applies when nothing else fired
                continue
            fired.append(rule)
            votes[rule["label"]] += float(rule["confidence"])
        best = fired[0]                          # lowest priority number wins
        return MethodologyDecision(
            label=best["label"],
            confidence=float(best["confidence"]),
            rule_id=best["id"],
            rationale=best["rationale"],
            votes=votes,
            fired=[r["id"] for r in fired],
            needs_review=best["priority"] >= 90 or float(best["confidence"]) < 0.6,
        )

    # ---------------- tools ----------------
    def tools_for(self, methodology: str, wastes: List[str]) -> Dict[str, List[str]]:
        phases = {k: list(v) for k, v in self.tool_map["by_methodology"].get(methodology, {}).items()}
        waste_tools = []
        for w in wastes:
            waste_tools += self.tool_map["by_waste"].get(w, [])
        if waste_tools:
            phases["Waste-specific"] = sorted(set(waste_tools))
        return phases

    # ---------------- explanation ----------------
    def explain(self, text: str, intake: Optional[Intake] = None) -> str:
        ev = self.waste_evidence(text)
        dec = self.route(text, intake, ev)
        lines = [f"Methodology (rules): {dec.label}  confidence={dec.confidence:.2f}  via {dec.rule_id}",
                 f"  {dec.rationale}",
                 f"  all fired: {', '.join(dec.fired)}",
                 f"  votes: " + ", ".join(f"{k}={v:.2f}" for k, v in dec.votes.items() if v > 0),
                 "Waste evidence:"]
        for w, s in sorted(ev.scores.items(), key=lambda kv: -kv[1]):
            if s > 0:
                hits = [f"{rid}:'{m}'" for rid, lab, m in ev.fired if lab == w]
                lines.append(f"  {w:<20} score={s:>4.0f}  {', '.join(hits[:6])}")
        return "\n".join(lines)


if __name__ == "__main__":
    import sys
    eng = RulesEngine()
    sample = " ".join(sys.argv[1:]) or (
        "Travel vouchers sit in the approving official's inbox for two to three weeks. "
        "About a third are sent back for missing receipts and the traveler has to rework them. "
        "We don't really know why some approvers are so much slower than others."
    )
    print(eng.explain(sample, Intake(process_exists="yes", cause_known="no", data_available="partial",
                                     scope="cross_functional", problem_type="delay_flow", effort_estimate="weeks")))
