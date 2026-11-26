"""
Dataset and outcome record schemas.

Two tables:
  1. Case records      (data/annotated/*.jsonl)  one process-problem narrative with labels
  2. Outcome records   (data/outcomes/*.jsonl)   what happened after a recommendation was made

Both are plain JSON lines so they diff cleanly in git and load with pandas.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import json
import re

METHODOLOGIES = ["JUST_DO_IT", "KAIZEN_EVENT", "DMAIC", "DMADV", "NOT_CPI"]

# One sentence per route: the annotation guidelines' plain-English column. The Kaggle
# Overview page shows it (competition.PLAIN) and the Phase 3 models embed it, word for
# word. It lives here, with no imports, so the app and the models can use it without
# loading the competition and annotation tooling.
ROUTE_DEFINITIONS: Dict[str, str] = {
    "JUST_DO_IT": "Somebody just go fix it: the cause and the fix are both stated, and the fix is small.",
    "KAIZEN_EVENT": "Get the right people in a room for a few days: a flow problem whose cause is roughly understood.",
    "DMAIC": "Measure before you fix: an existing process fails and nobody knows why.",
    "DMADV": "Design something that does not exist yet: no process today, or one that could never meet the requirement.",
    "NOT_CPI": "Not a process-improvement problem: really a request for money, staff, policy or a purchase.",
}

WASTES = ["DEFECTS", "OVERPRODUCTION", "WAITING", "NON_UTILIZED_TALENT",
          "TRANSPORTATION", "INVENTORY", "MOTION", "EXTRA_PROCESSING"]

INTAKE_FIELDS: Dict[str, List[str]] = {
    "process_exists":  ["yes", "no", "unsure"],
    "cause_known":     ["yes", "no", "unsure"],
    "solution_known":  ["yes", "no", "unsure"],
    "data_available":  ["yes", "partial", "no", "unsure"],
    "scope":           ["single_step", "single_process", "cross_functional", "enterprise", "unsure"],
    "problem_type":    ["defects_variation", "delay_flow", "cost", "safety", "customer_requirement",
                        "new_capability", "resourcing_policy", "unsure"],
    "effort_estimate": ["hours", "days", "weeks", "months", "unsure"],
}
SOURCE_TYPES = ["gov_public_domain", "academic", "industry_cc", "industry_paraphrased", "synthetic", "user_submitted"]
SPLITS = ["train", "dev", "test", "unassigned"]


@dataclass
class Intake:
    process_exists: str = "unsure"
    cause_known: str = "unsure"
    solution_known: str = "unsure"
    data_available: str = "unsure"
    scope: str = "unsure"
    problem_type: str = "unsure"
    effort_estimate: str = "unsure"

    def validate(self) -> List[str]:
        errors = []
        for name, allowed in INTAKE_FIELDS.items():
            if getattr(self, name) not in allowed:
                errors.append(f"intake.{name}={getattr(self, name)!r} not in {allowed}")
        return errors


@dataclass
class CaseRecord:
    id: str                                  # e.g. "CASE-000123"
    narrative: str                           # the process-problem description, free text
    intake: Intake = field(default_factory=Intake)
    methodology: Optional[str] = None        # gold label, one of METHODOLOGIES
    wastes: List[str] = field(default_factory=list)   # gold labels, subset of WASTES
    source_type: str = "synthetic"
    source_url: Optional[str] = None
    source_note: Optional[str] = None        # e.g. "paraphrased from section 3 of the report"
    sector: Optional[str] = None             # e.g. "federal_admin", "manufacturing", "healthcare", "it"
    annotator: Optional[str] = None
    annotation_confidence: Optional[str] = None   # "high" | "medium" | "low"
    split: str = "unassigned"
    created: Optional[str] = None            # ISO date

    def validate(self) -> List[str]:
        errors = []
        if not re.match(r"^CASE-\d{6}$", self.id):
            errors.append(f"id {self.id!r} must look like CASE-000123")
        if len(self.narrative.split()) < 15:
            errors.append(f"{self.id}: narrative shorter than 15 words")
        if self.methodology is not None and self.methodology not in METHODOLOGIES:
            errors.append(f"{self.id}: methodology {self.methodology!r} not in {METHODOLOGIES}")
        bad = [w for w in self.wastes if w not in WASTES]
        if bad:
            errors.append(f"{self.id}: unknown wastes {bad}")
        if self.source_type not in SOURCE_TYPES:
            errors.append(f"{self.id}: source_type {self.source_type!r} not in {SOURCE_TYPES}")
        if self.split not in SPLITS:
            errors.append(f"{self.id}: split {self.split!r} not in {SPLITS}")
        errors += [f"{self.id}: {e}" for e in self.intake.validate()]
        return errors

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CaseRecord":
        d = dict(d)
        d["intake"] = Intake(**d.get("intake", {}))
        return CaseRecord(**d)


@dataclass
class OutcomeRecord:
    """Logged after a recommendation is issued, then updated as the project moves.

    This is the table the outcome model learns from over time.
    """
    recommendation_id: str                   # e.g. "REC-2026-09-10-0001"
    case_id: Optional[str]                   # links to a CaseRecord if the narrative was saved
    issued: str                              # ISO datetime the recommendation was produced
    model_version: str
    methodology_recommended: str
    methodology_probability: float
    wastes_recommended: List[str] = field(default_factory=list)
    methodology_chosen: Optional[str] = None       # what the team actually did
    followed_recommendation: Optional[bool] = None
    decision_date: Optional[str] = None            # when the team chose a methodology
    status: str = "open"                           # open | in_progress | completed | abandoned
    resolved: Optional[bool] = None                # did the problem actually go away
    days_to_decision: Optional[int] = None
    days_to_complete: Optional[int] = None
    benefit_metric: Optional[str] = None           # e.g. "cycle time 21d -> 6d"
    sponsor_level: Optional[str] = None            # "team_lead" | "branch" | "division" | "executive"
    team_size: Optional[int] = None
    closed: Optional[str] = None                   # ISO date
    notes: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def load_jsonl(path: str) -> List[CaseRecord]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(CaseRecord.from_dict(json.loads(line)))
    return records


def validate_file(path: str) -> List[str]:
    """Return a list of validation errors for a JSONL file (empty list means clean)."""
    errors = []
    seen = set()
    for r in load_jsonl(path):
        if r.id in seen:
            errors.append(f"duplicate id {r.id}")
        seen.add(r.id)
        errors += r.validate()
    return errors


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/annotated/seed_cases.jsonl"
    errs = validate_file(path)
    print(f"{path}: {'OK' if not errs else str(len(errs)) + ' errors'}")
    for e in errs:
        print("  -", e)
