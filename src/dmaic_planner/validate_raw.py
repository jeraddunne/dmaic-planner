"""
Phase-2 gate checks on the raw collection (data/raw/all_records.csv).

This runs *before* annotation. It does not look at labels; it checks that the
collected narratives are internally consistent, that they obey the storage rules
in docs/data_statement.md, and that they can actually be carried into the
CaseRecord schema in schema.py without silent breakage.

    python -m dmaic_planner.validate_raw            # or: make validate-raw

Exit status is 1 if any BLOCKER fires, so this can gate a merge.
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import List, Tuple

from .schema import SOURCE_TYPES

RAW = Path("data/raw/all_records.csv")
SOURCES = Path("data/raw/sources.csv")

EXPECTED_COLUMNS = [
    "record_id", "source_name", "source_doc_id", "url",
    "source_type", "content_shape", "sector",
    "problem_text", "fix_text", "result_text", "outcome_code",
    "narrative_predates_fix", "license", "storage_mode", "fetched_date", "notes",
]

# Content-shape vocabulary the collector actually used in the source_type column.
CONTENT_SHAPES = {"problem only", "problem+fix", "problem+fix+result"}

# Strings that are a disposition/status code rather than a described fix or outcome.
CANNED_FIX = [
    "chooses not to provide a public response",
    "Company believes it acted appropriately",
]
CANNED_RESULT = re.compile(r"^(Closed with .*|status=\w+; resolution=\w+)$")

# Minimum narrative length enforced by CaseRecord.validate().
MIN_NARRATIVE_WORDS = 15

PII_PATTERNS = {
    "SSN-like": r"\b\d{3}-\d{2}-\d{4}\b",
    "email": r"[\w\.-]+@[\w\.-]+\.\w{2,}",
    "phone": r"\b\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b",
    "card-16": r"\b\d{16}\b",
    "long-account-number": r"\b\d{9,}\b",
}


class Report:
    def __init__(self) -> None:
        self.findings: List[Tuple[str, str, str]] = []

    def add(self, severity: str, code: str, message: str) -> None:
        self.findings.append((severity, code, message))

    def ok(self, code: str, message: str) -> None:
        self.add("PASS", code, message)

    @property
    def blockers(self) -> int:
        return sum(1 for s, _, _ in self.findings if s == "BLOCKER")

    def render(self) -> str:
        order = {"BLOCKER": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "PASS": 4}
        lines = []
        for sev, code, msg in sorted(self.findings, key=lambda f: (order[f[0]], f[1])):
            lines.append(f"[{sev:7s}] {code:10s} {msg}")
        return "\n".join(lines)


def load(path: Path) -> List[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check(rows: List[dict], sources: List[dict], rep: Report) -> None:
    n = len(rows)

    # --- structure -------------------------------------------------------
    cols = list(rows[0].keys()) if rows else []
    if cols != EXPECTED_COLUMNS:
        rep.add("BLOCKER", "STRUCT-1",
                f"column mismatch.\n  expected {EXPECTED_COLUMNS}\n  found    {cols}")
    else:
        rep.ok("STRUCT-1", f"{len(EXPECTED_COLUMNS)} columns as documented; {n} records parsed")

    ids = [r["record_id"] for r in rows]
    dupe_ids = [i for i, c in Counter(ids).items() if c > 1]
    if dupe_ids:
        rep.add("BLOCKER", "STRUCT-2", f"duplicate record_id: {dupe_ids[:10]}")
    else:
        rep.ok("STRUCT-2", "record_id unique")

    # --- schema compatibility with schema.py ------------------------------
    tiers = {r["source_type"] for r in rows}
    if tiers <= CONTENT_SHAPES:
        rep.add("BLOCKER", "SCHEMA-1",
                "`source_type` holds content shape "
                f"({sorted(tiers)}) but schema.py/data_statement.md define "
                f"source_type as a licensing tier ({SOURCE_TYPES}). "
                "Rename this column to `content_shape` and add a real "
                "`source_type` tier column before ingest.")
    else:
        bad = tiers - set(SOURCE_TYPES)
        if bad:
            rep.add("BLOCKER", "SCHEMA-1",
                    f"source_type values outside the data_statement tiers: {sorted(bad)}")
        else:
            rep.ok("SCHEMA-1", f"source_type uses data_statement tiers {sorted(tiers)}")

    shapes = {r["content_shape"] for r in rows}
    bad_shape = shapes - CONTENT_SHAPES
    if bad_shape:
        rep.add("HIGH", "SCHEMA-4", f"content_shape values outside the vocabulary: {sorted(bad_shape)}")
    else:
        rep.ok("SCHEMA-4", f"content_shape uses {sorted(shapes)}")

    bad_id = [r["record_id"] for r in rows if not re.match(r"^CASE-\d{6}$", r["record_id"])]
    if bad_id:
        rep.add("MEDIUM", "SCHEMA-2",
                f"{len(bad_id)} record_ids are source-prefixed (e.g. {bad_id[0]}), not "
                "CASE-nnnnnn. The ingest script must mint CASE ids and keep the "
                "collector id as provenance.")

    short = [r["record_id"] for r in rows
             if len(r["problem_text"].split()) < MIN_NARRATIVE_WORDS]
    if short:
        rep.add("HIGH", "SCHEMA-3",
                f"{len(short)} narratives under {MIN_NARRATIVE_WORDS} words; "
                f"CaseRecord.validate() will reject: {short[:5]}")
    else:
        rep.ok("SCHEMA-3", f"all narratives >= {MIN_NARRATIVE_WORDS} words")

    # --- declared type vs actual content ---------------------------------
    def actual_shape(r: dict) -> str:
        has_fix = bool(r["fix_text"].strip())
        has_res = bool(r["result_text"].strip())
        if has_fix and has_res:
            return "problem+fix+result"
        if has_fix:
            return "problem+fix"
        return "problem only"

    mism = [r for r in rows if r["content_shape"] != actual_shape(r)]
    if mism:
        by = Counter((r["source_name"], r["content_shape"], actual_shape(r)) for r in mism)
        detail = "; ".join(f"{s} declared {d!r} but is {a!r} x{c}" for (s, d, a), c in by.items())
        rep.add("MEDIUM", "SHAPE-1", f"{len(mism)} records mis-typed: {detail}")
    else:
        rep.ok("SHAPE-1", "declared content_shape matches field content")

    # --- is the "fix" actually a fix? ------------------------------------
    canned = [r["record_id"] for r in rows
              if r["fix_text"].strip()
              and any(c in r["fix_text"] for c in CANNED_FIX)]
    if canned:
        rep.add("BLOCKER", "FIX-1",
                f"{len(canned)} records carry a disposition code in fix_text "
                "(e.g. 'Company has responded ... chooses not to provide a public "
                "response'). That is not a process fix; these are problem-only "
                f"records. Affected: {canned[:3]} ...")
    else:
        rep.ok("FIX-1", "no canned disposition strings in fix_text")

    # --- is the "result" an outcome or a status code? ---------------------
    leaked = [r for r in rows
              if r["result_text"].strip() and CANNED_RESULT.match(r["result_text"].strip())]
    prose = [r for r in rows if r["result_text"].strip()]
    coded = [r for r in rows if r["outcome_code"].strip()]
    if leaked:
        by = Counter(r["source_name"] for r in leaked)
        rep.add("HIGH", "RESULT-1",
                f"{len(leaked)} status codes are still in result_text rather than "
                f"outcome_code ({dict(by)}). Run dmaic_planner.migrate_raw.")
    else:
        rep.ok("RESULT-1",
               f"result_text holds {len(prose)} prose outcomes; "
               f"outcome_code holds {len(coded)} status codes; no mixing")

    # --- does the narrative leak its own fix? (V-11) -----------------------
    from .ingest import LEAK_THRESHOLD, fix_leak_fraction
    leaky = [(r["record_id"], fix_leak_fraction(r)) for r in rows]
    leaky = [(rid, f) for rid, f in leaky if f > LEAK_THRESHOLD]
    if leaky:
        by = Counter(r["source_name"] for r in rows
                     if fix_leak_fraction(r) > LEAK_THRESHOLD)
        full = sum(1 for _, f in leaky if f >= 0.99)
        rep.add("HIGH", "LEAK-1",
                f"{len(leaky)} records have >{LEAK_THRESHOLD:.0%} of their fix text "
                f"already inside the narrative ({dict(by)}); {full} are a complete "
                "overlap. The narrative then contains its own remedy, which makes "
                "intake.solution_known trivially inferable and weakens the routing "
                "task. Re-extract the problem-as-stated for these.")
    else:
        rep.ok("LEAK-1", "no narrative contains its own recorded fix")

    # --- storage rule compliance -----------------------------------------
    rule_by_source = {s["source_name"]: s["storage_rule"] for s in sources}
    violations = []
    for r in rows:
        rule = rule_by_source.get(r["source_name"], "")
        if rule.startswith("paraphrase") and r["storage_mode"] != "paraphrase":
            violations.append(r["record_id"])
    if violations:
        rep.add("BLOCKER", "LICENSE-1",
                f"{len(violations)} records from paraphrase-only sources stored as "
                f"verbatim: {violations[:5]}")
    else:
        rep.ok("LICENSE-1", "every paraphrase-only source is stored as paraphrase")

    # --- PII ---------------------------------------------------------------
    for name, pat in PII_PATTERNS.items():
        hits = [r["record_id"] for r in rows
                if re.search(pat, r["problem_text"]) or re.search(pat, r["fix_text"])]
        if hits:
            rep.add("HIGH", "PII-1", f"{name} pattern in {len(hits)} records: {hits[:5]}")
    if not any(code == "PII-1" for _, code, _ in rep.findings):
        rep.ok("PII-1", "no SSN/email/phone/card/account patterns in narrative text")

    # data_statement.md: "No personal names, no identifiable individuals"
    named = [r["record_id"] for r in rows if re.search(r"(?:^|;\s*)author=", r["notes"])]
    if named:
        by = Counter(r["source_name"] for r in rows if re.search(r"(?:^|;\s*)author=", r["notes"]))
        rep.add("HIGH", "PII-2",
                f"{len(named)} records store a named individual in notes (author=...) "
                f"{dict(by)}. data_statement.md bans personal names, but CC BY-SA "
                "requires attribution. Team must resolve which governs.")

    # --- grouped-split feasibility ----------------------------------------
    by_doc = Counter(r["source_doc_id"] for r in rows)
    biggest = by_doc.most_common(1)[0]
    oversized = [(d, c) for d, c in by_doc.items() if c / n > 0.10]
    if oversized:
        detail = "; ".join(f"{c} records ({100*c/n:.0f}%) share {d}"
                           for d, c in sorted(oversized, key=lambda x: -x[1]))
        rep.add("HIGH", "SPLIT-1",
                "data_statement.md requires a grouped split on the source document and "
                f"at most one case per document in test. {detail}. Those groups cannot "
                "be divided, so a grouped split would dump them whole into one fold.")
    else:
        rep.ok("SPLIT-1",
               f"{len(by_doc)} distinct source_doc_id groups across {n} records; "
               f"largest is {biggest[1]} — grouped split is feasible")

    # --- registry reconciliation -------------------------------------------
    collected = {s["source_name"] for s in sources if s["status"].startswith("collected")}
    present = {r["source_name"] for r in rows}
    if collected - present:
        rep.add("MEDIUM", "REG-1", f"registry says collected but no records: {sorted(collected - present)}")
    if present - collected:
        rep.add("MEDIUM", "REG-2", f"records present but not marked collected: {sorted(present - collected)}")
    if collected == present:
        rep.ok("REG-1", f"all {len(present)} collected sources reconcile with the registry")

    # --- Phase-2 tollgate numbers ------------------------------------------
    if n >= 300:
        rep.ok("GATE-1", f"{n} narratives >= 300 target")
    else:
        rep.add("BLOCKER", "GATE-1", f"only {n} narratives, target is 300")

    sectors = {r["sector"] for r in rows}
    if len(sectors) >= 4:
        rep.ok("GATE-2", f"{len(sectors)} sector tags >= 4 target")
    else:
        rep.add("HIGH", "GATE-2", f"only {len(sectors)} sectors, target is 4")

    # class-coverage proxy: how much of the set can support a fix-bearing label
    real_fix = sum(1 for r in rows
                   if r["fix_text"].strip()
                   and not any(c in r["fix_text"] for c in CANNED_FIX))
    rep.add("LOW", "GATE-3",
            f"{real_fix} records ({100*real_fix/n:.0f}%) carry a genuinely described fix "
            f"after discounting disposition codes")


def main() -> int:
    if not RAW.exists():
        print(f"missing {RAW}", file=sys.stderr)
        return 2
    rows, sources = load(RAW), load(SOURCES)
    rep = Report()
    check(rows, sources, rep)
    print(f"\nPhase-2 raw validation — {RAW} ({len(rows)} records)\n")
    print(rep.render())
    print(f"\n{rep.blockers} blocker(s).\n")
    return 1 if rep.blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
