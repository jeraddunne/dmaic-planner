"""
Build the public release of the 60 labeled items, with personal names scrubbed.

    python -m dmaic_planner.release                    # build the staging folder
    python -m dmaic_planner.release --check            # re-scan the staged files; exit 1 if a flagged pattern remains
    python -m dmaic_planner.release --check --strict   # also exit 1 while a NEEDS REVIEW span has no decision
    python -m dmaic_planner.release --no-se-authors    # build without Stack Exchange usernames in attribution

(Run with PYTHONPATH=src, as tasks.py does.)

Reads the competition text exactly as Kaggle participants saw it (kaggle/public/train.csv and
test.csv), the split and answer key (kaggle/private/id_map.csv), the gold rows
(data/annotated/gold_r1.jsonl) for how many people labeled each item, and, for each item's
source, link and license, the unlabeled pool and the raw collection (data/raw/all_records.csv).
Writes into the gitignored staging folder kaggle/private/phase3/release_staging/:

  train.csv         40 rows: id, text, label, decided_by, n_labels, source, source_url,
                    attribution, license, storage_mode
  test.csv          20 rows: the same columns plus Usage (Public or Private on the Kaggle leaderboard)
  scrub_report.csv  every replacement and every NEEDS REVIEW span, with about 60 characters of
                    context. It holds the ORIGINAL names, so it is never published.
  scrub_summary.md  counts by rule, the NEEDS REVIEW list, the issue #16 check, split and label tables

Nothing is published from here. Jerad reviews the staging folder and publishes it himself.
Each file is written to a .tmp file and renamed into place, so a reader (another process
training from train.csv, say) sees the old file or the new one, never half of one.

Attribution: each Stack Exchange item's `attribution` carries the author's public username and
profile link, which CC BY-SA attribution on Stack Exchange asks for (`--no-se-authors` leaves
them out). Those names never enter `text`, and the other issue #16 names (the PSNet case
commentators) appear in no column. `--check` enforces both.

Scrub rules
-----------
Scrubbed: private individuals named in the narrative text (patients, consumers, employees,
ticket senders, coworkers, Stack Exchange users). A name becomes "[person]".

Kept: organizations and agencies, in every source. Company names in CFPB complaints are part
of the record the CFPB itself publishes, and "Freddie Mac" is a company, not a person. A person
named in a public government report (GAO) is taken to be an official acting in that role: the
span is kept and listed as NEEDS REVIEW instead of being replaced. Every other source gets the
replacement.

Replaced automatically (the rule names used in scrub_report.csv):
  email, phone, ssn-like, card-16,     the validate_raw PII-1 patterns, so the release is held to
  long-account-number                  the same scan that cleared the raw collection
  handle            @name (an @ directly followed by a letter; "@ 11 am" is a time, not a handle)
  issue16-author    any of the author= names behind issue #16, anywhere in the text
  title-name        "Dr. X", "Mrs. X Y": the name goes, the title stays ("Dr. [person]")
  relation-name     "my manager X", "coworker (X)": X in parentheses, or X a common given name
  signature         a common given name alone on the line after "Regards," / "Thanks," / ...
  full-name         a common given name followed by a capitalized surname
  repeat            a later mention of a name already replaced in the same item

Listed as NEEDS REVIEW and left unchanged:
  relation-name, signature, title-name   when the capitalized word is not a known given name
  given-name        a common given name on its own
  case-citation     "X v. Y": party names in a published court case
  surname-firm      "X, Y & Z": an organization named after people
  any person rule   on a GAO report (see above)

To settle a NEEDS REVIEW span, add it to REVIEW_DECISIONS below ("keep", or the replacement
text) and rebuild. The rules are deliberately conservative: a false alarm costs a minute of
review, a missed name costs a privacy leak.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import os
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass, replace as dc_replace
from pathlib import Path

from dmaic_planner.schema import METHODOLOGIES
from dmaic_planner.validate_raw import PII_PATTERNS

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "kaggle" / "public"
ID_MAP = ROOT / "kaggle" / "private" / "id_map.csv"
GOLD = ROOT / "data" / "annotated" / "gold_r1.jsonl"
POOL = ROOT / "data" / "annotated" / "inbox_unlabeled.jsonl"
RAW = ROOT / "data" / "raw" / "all_records.csv"
OUT = ROOT / "kaggle" / "private" / "phase3" / "release_staging"

PERSON = "[person]"
COLUMNS = ["id", "text", "label", "decided_by", "n_labels", "source", "source_url",
           "attribution", "license", "storage_mode"]
TEST_COLUMNS = COLUMNS[:3] + ["Usage"] + COLUMNS[3:]

# Settled NEEDS REVIEW spans: (item id, exact span) -> "keep" or the replacement text.
# One entry covers every mention of that span in the item. Decided by Jerad, 2026-11-26.
REVIEW_DECISIONS: dict[tuple[str, str], str] = {
    ("dmaic_014", "Love, Beal & Nixon"): "keep",       # a debt-collection law firm: an organization
    ("dmaic_030", "U.S. vs. Throckmorton"): "keep",    # published case law quoted by the consumer
    ("dmaic_030", "Whipp v. Iverson"): "keep",         # published case law quoted by the consumer
}

# --------------------------------------------------------------------------- #
# word lists
# --------------------------------------------------------------------------- #

# Common given names. Words that are also ordinary English or place names (Will, May, Mark,
# Bill, Grant, Chase, Rose, Virginia, Julia the language, ...) are left out on purpose: they
# would flag half the GAO reports. A name missing here is still caught by the parenthesis,
# title and #16 rules, and lands in NEEDS REVIEW after a relation word.
GIVEN_NAMES = frozenset("""
Aaron Abigail Adam Ahmed Alan Albert Alex Alexander Alexandra Alexis Alice Alicia Allison Amanda
Amit Amy Ana Andre Andrea Andrew Andy Angela Anita Ann Anna Anne Anthony Antonio Arthur Ashley
Barbara Becky Benjamin Ben Beth Betty Beverly Bob Bobby Brad Bradley Brandon Brenda Brian Bruce
Bryan Caitlin Carl Carlos Carol Caroline Catherine Cathy Charles Charlie Cheryl Chris Christian
Christina Christine Christopher Cindy Claire Craig Cynthia Dan Daniel Danielle Danny Dave David
Debbie Deborah Debra Denise Dennis Derek Diana Diane Dmitri Donald Donna Dorothy Doug Douglas
Dylan Eddie Edward Elena Elizabeth Ellen Emily Emma Eric Erica Erin Ethan Eugene Evelyn Fred
Gary George Gerald Giulia Glenn Gloria Greg Gregory Hannah Hans Harold Harry Heather Helen Henry
Howard Igor Isabella Ivan Jacob Jacqueline Jake James Jamie Jane Janet Janice Jason Jean Jeff
Jeffrey Jen Jennifer Jenny Jeremy Jerry Jesse Jessica Jim Jimmy Joan Joe Joel John Johnny
Jonathan Jose Joseph Josh Joshua Joyce Juan Judith Judy Julie Justin Karen Kate Katherine Kathleen
Kathryn Kathy Katie Keith Kelly Ken Kenneth Kevin Kimberly Kyle Larry Lars Laura Lauren Lawrence
Leah Linda Lisa Liz Logan Louis Luca Luis Marco Margaret Maria Marie Marilyn Martha Martin Mary
Matt Matthew Megan Melissa Michael Michelle Miguel Mike Mohammad Mohammed Molly Muhammad Nancy
Natalie Nathan Nicholas Nick Nicole Noah Olga Olivia Pamela Paolo Patricia Patrick Paul Pedro
Peter Phil Philip Pierre Priya Rachel Rahul Raj Ralph Randy Ravi Raymond Rebecca Richard Rick
Robert Roger Ron Ronald Roy Russell Ryan Sally Sam Samantha Samuel Sandra Sara Sarah Scott Sean
Sharon Shirley Sofia Sophia Stephanie Stephen Steve Steven Susan Sven Ted Teresa Terry Theresa
Thomas Tim Timothy Tom Tommy Tony Tyler Vincent Walter Wayne Wei William Zach Zachary
""".split())

# Capitalized words that are never the name in "my manager X" or "Regards, X".
STOP = frozenset("""
I A An The This That These Those It He She They We You My Our Your Their His Her Its And But Or
So If When Then Also Now Here There What Who How Why Please Thanks Thank Regards Dear Dears
Greetings Hello Hi Hey Team All Everyone Sir Madam Monday Tuesday Wednesday Thursday Friday
Saturday Sunday January February March April May June July August September October November
December Mr Mrs Ms Dr Scrum Kanban Agile Sprint Jira Product Owner Manager Master Lead Director
Sales Support Helpdesk Help Desk Customer Service Department Office Bank Inc Company Corporation
Is Was Are Were Has Had Did Does Do Will Would Should Could Can Not No Yes Ok Okay
""".split())

# Organizations whose names look like a person's. Never flagged.
ORG_ALLOWLIST = ("Freddie Mac", "Fannie Mae", "Sallie Mae", "Ginnie Mae", "Charles Schwab",
                 "Edward Jones", "Wells Fargo", "Mary Kay", "John Deere", "Johnson & Johnson")

# --------------------------------------------------------------------------- #
# patterns
# --------------------------------------------------------------------------- #

NAME = r"[A-Z][a-z]+(?:[-'’][A-Z]?[a-z]+)?"   # Titlecase word: Smith, O'Neil, Adler-Milstein
NAMES = rf"{NAME}(?:[ \t]+{NAME})?"                 # one or two of them

PII_REPLACEMENT = {"SSN-like": "[number]", "email": "[email]", "phone": "[phone]",
                   "card-16": "[number]", "long-account-number": "[number]"}
PII = [(name.lower(), re.compile(pat), PII_REPLACEMENT[name]) for name, pat in PII_PATTERNS.items()]

HANDLE_RE = re.compile(r"(?<![\w.@])@[A-Za-z_][A-Za-z0-9_.-]{1,38}")

STRONG_TITLES = {"Mr", "Mrs", "Ms", "Mx", "Miss", "Dr", "Prof", "Professor"}
TITLE_RE = re.compile(
    r"\b(?P<title>Mr|Mrs|Ms|Mx|Miss|Dr|Prof|Professor|Sir|Madam|Dame|Judge|Justice|Senator|Sen|Rep"
    r"|Representative|Officer|Sgt|Sergeant|Capt|Captain|Lt|Lieutenant|Det|Detective|Nurse|Pastor"
    rf"|Rev|Reverend)\.?[ \t]+(?P<name>{NAMES})")

RELATION_WORDS = (
    "manager", "boss", "supervisor", "co-?worker", "colleague", "teammate", "lead", "director",
    "friend", "husband", "wife", "son", "daughter", "mother", "father", "mom", "dad", "brother",
    "sister", "partner", "fianc[eé]e?", "agent", "representative", "rep", "nurse", "doctor",
    "physician", "surgeon", "pharmacist", "resident", "intern", "patient", "customer", "client",
    "employee", "engineer", "developer", "tester", "analyst", "administrator", "recruiter",
    "neighbou?r", "landlord", "tenant", "attorney", "lawyer", "named", "called")
RELATION_RE = re.compile(
    r"\b(?i:(?P<rel>" + "|".join(RELATION_WORDS) + r"))\b"
    rf"(?P<sep>[ \t]*\([ \t]*|[ \t]*,[ \t]*|[ \t]+)(?P<name>{NAMES})")

SIGNATURE_RE = re.compile(
    r"\b(?i:sincerely|best regards|kind regards|warm regards|regards|best wishes|many thanks"
    r"|thank you|thanks|cheers|respectfully|yours truly|best|br)[ \t]*,?[ \t]*(?:\r?\n[ \t]*)?"
    rf"(?P<name>{NAME}(?:[ \t]+{NAME}){{0,2}})[ \t]*(?=\r?\n|$)")

GIVEN_RE = re.compile(r"\b(?:" + "|".join(sorted(GIVEN_NAMES)) + r")\b")
SURNAME_AFTER_RE = re.compile(rf"[ \t]+(?:[A-Z]\.[ \t]+)?(?P<last>{NAME})\b")

CASE_CITATION_RE = re.compile(rf"\b[A-Z][\w.']*[ \t]+(?:v|vs)\.?[ \t]+{NAMES}")
SURNAME_FIRM_RE = re.compile(rf"\b{NAME},[ \t]+{NAME}[ \t]+&[ \t]+{NAME}\b")

AUTHOR_RE = re.compile(r"(?:^|;\s*)author=([^;]*)")      # the PII-2 field in validate_raw
RECORD_RE = re.compile(r"\[([A-Z]+-\d+)\]")                # record id inside source_note

# --------------------------------------------------------------------------- #
# the scrubber
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Finding:
    start: int
    end: int
    original: str
    rule: str
    action: str             # "replaced", "needs_review", or "kept" (a review decision said keep)
    replacement: str = ""
    note: str = ""


@dataclass(frozen=True)
class Scrubbed:
    text: str
    findings: tuple[Finding, ...]

    @property
    def replaced(self) -> list[Finding]:
        return [f for f in self.findings if f.action == "replaced"]

    @property
    def needs_review(self) -> list[Finding]:
        return [f for f in self.findings if f.action == "needs_review"]


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _trim(name: str) -> str:
    """Drop trailing stop words: 'Alice Monday' -> 'Alice'. Empty if the first word is one."""
    words = name.split()
    if not words or words[0] in STOP:
        return ""
    while words and words[-1] in STOP:
        words.pop()
    return " ".join(words)


def _person(text: str, start: int, end: int, rule: str, sure: bool, government: bool) -> Finding:
    """A person-name candidate: replaced when sure and not in a government report, else reviewed."""
    if government:
        return Finding(start, end, text[start:end], rule, "needs_review",
                       note="government report: an official named in their role is kept unless reviewed")
    if sure:
        return Finding(start, end, text[start:end], rule, "replaced", PERSON)
    return Finding(start, end, text[start:end], rule, "needs_review",
                   note="capitalized word in a name position, but not a known given name")


def _candidates(text: str, government: bool, known_names: tuple[str, ...]) -> list[tuple[int, Finding]]:
    """Every rule's hits, as (priority, finding). Lower priority wins an overlap."""
    out: list[tuple[int, Finding]] = []
    for rule, rx, repl in PII:
        out += [(0, Finding(m.start(), m.end(), m.group(), rule, "replaced", repl)) for m in rx.finditer(text)]
    out += [(0, Finding(m.start(), m.end(), m.group(), "handle", "replaced", "[handle]"))
            for m in HANDLE_RE.finditer(text)]
    for name in known_names:
        for m in re.finditer(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.I):
            out.append((1, Finding(m.start(), m.end(), m.group(), "issue16-author", "replaced", PERSON)))
    out += [(2, Finding(m.start(), m.end(), m.group(), "case-citation", "needs_review",
                        note="party names in a published court case"))
            for m in CASE_CITATION_RE.finditer(text)]
    out += [(2, Finding(m.start(), m.end(), m.group(), "surname-firm", "needs_review",
                        note="looks like an organization named after people (a law firm?)"))
            for m in SURNAME_FIRM_RE.finditer(text)]

    for m in TITLE_RE.finditer(text):
        name = _trim(m.group("name"))
        if name:
            first = name.split()[0]
            sure = m.group("title") in STRONG_TITLES or first in GIVEN_NAMES
            out.append((3, _person(text, m.start("name"), m.start("name") + len(name), "title-name", sure, government)))
    for m in RELATION_RE.finditer(text):
        name = _trim(m.group("name"))
        if not name:
            continue
        first = name.split()[0]
        sep = m.group("sep")
        in_parens = "(" in sep
        if "," in sep and first not in GIVEN_NAMES:
            continue                       # "Sales Manager, Estimators": a list, not a name
        if m.group("rel")[0].isupper() and not in_parens and first not in GIVEN_NAMES:
            continue                       # "Patient Safety Authority", "Attorney General": a proper noun
        sure = in_parens or first in GIVEN_NAMES
        out.append((4, _person(text, m.start("name"), m.start("name") + len(name), "relation-name", sure, government)))
    for m in SIGNATURE_RE.finditer(text):
        name = _trim(m.group("name"))
        if name:
            sure = name.split()[0] in GIVEN_NAMES
            out.append((4, _person(text, m.start("name"), m.start("name") + len(name), "signature", sure, government)))
    for m in GIVEN_RE.finditer(text):
        after = SURNAME_AFTER_RE.match(text, m.end())
        if after and after.group("last") not in STOP:
            out.append((5, _person(text, m.start(), after.end(), "full-name", True, government)))
    return out


def _allowed_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for org in ORG_ALLOWLIST for m in re.finditer(re.escape(org), text)]


def scrub(text: str, *, government: bool = False, known_names: tuple[str, ...] = (),
          decisions: dict[str, str] | None = None) -> Scrubbed:
    """Scrub one narrative. Deterministic: same input, same output and findings, in order."""
    decisions = decisions or {}
    allowed = _allowed_spans(text)
    cands = sorted(_candidates(text, government, tuple(sorted(set(known_names), key=lambda n: (-len(n), n)))),
                   key=lambda pf: (pf[0], pf[1].start, -(pf[1].end - pf[1].start), pf[1].rule))
    accepted: list[Finding] = []
    for prio, f in cands:
        span = (f.start, f.end)
        if prio >= 1 and any(_overlaps(span, a) for a in allowed):
            continue
        if any(_overlaps(span, (a.start, a.end)) for a in accepted):
            continue
        accepted.append(f)

    # A name replaced once is replaced everywhere in the item: "coworker (X)" ... "met with X".
    names = {f.original for f in accepted if f.action == "replaced" and f.replacement == PERSON}
    names |= {w for n in names for w in n.split() if len(w) >= 3 and w not in STOP and w[0].isupper()}
    for name in sorted(names, key=lambda n: (-len(n), n)):
        for m in re.finditer(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text):
            span = (m.start(), m.end())
            if any(_overlaps(span, (a.start, a.end)) for a in accepted):
                continue
            accepted.append(Finding(m.start(), m.end(), m.group(), "repeat", "replaced", PERSON))

    # A common given name on its own: worth a look, not worth a silent change.
    for m in GIVEN_RE.finditer(text):
        span = (m.start(), m.end())
        if any(_overlaps(span, a) for a in allowed) or any(_overlaps(span, (a.start, a.end)) for a in accepted):
            continue
        note = ("government report: an official named in their role is kept unless reviewed" if government
                else "a common given name on its own")
        accepted.append(Finding(m.start(), m.end(), m.group(), "given-name", "needs_review", note=note))

    settled = []
    for f in accepted:
        if f.action == "needs_review" and f.original in decisions:
            d = decisions[f.original]
            f = (dc_replace(f, action="kept", note="reviewed: keep") if d == "keep"
                 else dc_replace(f, action="replaced", replacement=d, note="reviewed: replace"))
        settled.append(f)
    settled.sort(key=lambda f: (f.start, f.end, f.rule))

    out = text
    for f in sorted(settled, key=lambda f: f.start, reverse=True):
        if f.action == "replaced":
            out = out[:f.start] + f.replacement + out[f.end:]
    return Scrubbed(out, tuple(settled))


def context(text: str, f: Finding, width: int = 30) -> str:
    """About 60 characters around a span, the span marked with guillemets, on one line."""
    before = text[max(0, f.start - width):f.start]
    after = text[f.end:f.end + width]
    return " ".join(f"{before}«{f.original}»{after}".split())


# --------------------------------------------------------------------------- #
# per-item source, attribution and license
# --------------------------------------------------------------------------- #

def notes_dict(notes: str) -> dict[str, str]:
    out = {}
    for part in notes.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def se_license(created: str) -> str:
    """Stack Exchange's version cut-overs (stackoverflow.com/help/licensing), by post date."""
    if created < "2011-04-08":
        return "CC BY-SA 2.5"
    if created < "2018-05-02":
        return "CC BY-SA 3.0"
    return "CC BY-SA 4.0"


def provenance(rid: str, raw: dict, source_url: str, with_se_authors: bool = True) -> dict[str, str]:
    """source, attribution, license and storage_mode for one item, from the raw record."""
    kind = rid.split("-")[0]
    notes = raw["notes"]
    nd = notes_dict(notes)
    paraphrase = "CC BY-SA 4.0 (team-written paraphrase; the source text is not included)"
    if kind == "CFPB":
        src = "CFPB Consumer Complaint Database"
        attribution = f"CFPB Consumer Complaint Database, complaint {nd.get('complaint_id', '')}"
        lic = "Public domain (CC0 / U.S. Government work)"
    elif kind == "GAO":
        src = "GAO Reports"
        title, _, when = notes.partition(" | ")
        number = source_url.rstrip("/").rsplit("/", 1)[-1].upper()
        attribution = f"U.S. Government Accountability Office, \"{title.strip()}\", {number}, {when.strip()}"
        lic = "Public domain (U.S. Government work)"
    elif kind == "SE":
        # CC BY-SA attribution as Stack Exchange asks for it: the author's public username and a
        # link to their profile. Attribution column only; the name never enters `text`.
        site = re.search(r"https://([a-z]+\.stackexchange\.com)/", source_url).group(1)
        src = f"Stack Exchange: {site}"
        attribution = f"Question {nd.get('question_id', '')} on {site}, asked {nd.get('created', '')}"
        if with_se_authors:
            profile = nd.get("author_url") or "no profile link recorded"
            attribution += f", by {nd.get('author', '')} ({profile})"
        else:
            attribution += "; the author's name and profile are on the question page (source_url)"
        lic = se_license(nd.get("created", ""))
    elif kind == "PSN":
        src = "AHRQ PSNet WebM&M"
        attribution = (f"Team paraphrase of the AHRQ PSNet WebM&M case \"{nd.get('title', '')}\" "
                       f"({nd.get('date', '')})")
        lic = paraphrase
    elif kind == "PAPSA":
        src = "PA Patient Safety Authority: Lessons from Event Reports"
        attribution = "Team paraphrase of a PA Patient Safety Authority event-report story"
        lic = paraphrase
    elif kind == "BAL":
        src = "NIST Baldrige Application Summaries"
        attribution = (f"Team paraphrase of the {nd.get('org', '')} Baldrige Award application summary "
                       f"({nd.get('award_year', '')}), hosted by NIST")
        lic = paraphrase
    elif kind == "HD":
        src = "Mendeley Help Desk Tickets"
        cite = notes.split("attribution:", 1)[1].strip() if "attribution:" in notes else "Help Desk Tickets, Mendeley Data"
        attribution = f"{cite}, doi:10.17632/btm76zndnt.3; ticket {nd.get('ticket_id', '')}"
        lic = "CC BY 4.0"
    else:
        raise ValueError(f"{rid}: no attribution rule for source kind {kind!r}")
    return {"source": src, "attribution": attribution, "license": lic, "storage_mode": raw["storage_mode"]}


# --------------------------------------------------------------------------- #
# inputs
# --------------------------------------------------------------------------- #

def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def issue16_names(raw_rows: list[dict]) -> tuple[dict[str, str], tuple[str, ...]]:
    """record_id -> author for the records issue #16 counts, and the distinct names (3+ chars)."""
    by_record = {}
    for r in raw_rows:
        m = AUTHOR_RE.search(r["notes"])
        if m and m.group(1).strip():
            by_record[r["record_id"]] = m.group(1).strip()
    names = tuple(sorted({n for n in by_record.values() if len(n) >= 3}))
    return by_record, names


def load_items(with_se_authors: bool = True) -> tuple[list[dict], dict]:
    for p in (ID_MAP, PUBLIC / "train.csv", PUBLIC / "test.csv", GOLD, POOL, RAW):
        if not p.exists():
            sys.exit(f"error: {p} not found. The release is built from the Kaggle files "
                     "(`python tasks.py kaggle`) and the round-1 annotation files.")
    id_map = read_csv(ID_MAP)
    text = {r["id"]: r["text"] for f in ("train.csv", "test.csv") for r in read_csv(PUBLIC / f)}
    gold = {g["id"]: g for g in read_jsonl(GOLD)}
    pool = {r["id"]: r for r in read_jsonl(POOL)}
    raw_rows = read_csv(RAW)
    raw = {r["record_id"]: r for r in raw_rows}
    authors, names = issue16_names(raw_rows)

    items = []
    for m in sorted(id_map, key=lambda r: r["id"]):
        rec = pool[m["case_id"]]
        rid = RECORD_RE.search(rec.get("source_note") or "").group(1)
        if m["label"] not in METHODOLOGIES:
            sys.exit(f"error: {m['id']} has label {m['label']!r}, not one of {METHODOLOGIES}")
        items.append({
            "id": m["id"], "split": m["split"], "Usage": m["Usage"], "label": m["label"],
            "decided_by": m["decided_by"], "n_labels": str(gold[m["case_id"]]["n_labels"]),
            "record_id": rid, "kind": rid.split("-")[0], "original_text": text[m["id"]],
            "source_url": rec.get("source_url") or raw[rid]["url"],
            **provenance(rid, raw[rid], rec.get("source_url") or raw[rid]["url"], with_se_authors),
        })
    meta = {"authors": authors, "names": names,
            "raw_by_source": Counter(provenance(r, raw[r], raw[r]["url"])["source"] for r in authors)}
    return items, meta


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #

def item_decisions(item_id: str) -> dict[str, str]:
    return {span: d for (i, span), d in REVIEW_DECISIONS.items() if i == item_id}


def replace_atomically(tmp: Path, path: Path, attempts: int = 20) -> None:
    """Rename tmp over path, so a reader sees the old file or the new one, never half of one.
    On Windows the rename fails while another process has the file open; wait and retry."""
    for k in range(attempts):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if k == attempts - 1:
                raise
            time.sleep(0.25)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    replace_atomically(tmp, path)


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    replace_atomically(tmp, path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def names_in(text: str, names: tuple[str, ...]) -> list[str]:
    return [n for n in names if re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", text, re.I)]


def build(out: Path = OUT, with_se_authors: bool = True) -> dict:
    items, meta = load_items(with_se_authors)
    report = []
    for it in items:
        s = scrub(it["original_text"], government=it["kind"] == "GAO", known_names=meta["names"],
                  decisions=item_decisions(it["id"]))
        it["text"] = s.text
        it["findings"] = s.findings
        for f in s.findings:
            report.append({"id": it["id"], "split": it["split"], "source": it["source"], "rule": f.rule,
                           "action": f.action, "original": f.original, "replacement": f.replacement,
                           "context": context(it["original_text"], f), "note": f.note})

    train = [it for it in items if it["split"] == "train"]
    test = [it for it in items if it["split"] == "test"]
    write_csv(out / "train.csv", COLUMNS, train)
    write_csv(out / "test.csv", TEST_COLUMNS, test)
    write_csv(out / "scrub_report.csv",
              ["id", "split", "source", "rule", "action", "original", "replacement", "context", "note"], report)

    summary = {"items": items, "report": report, "meta": meta, "with_se_authors": with_se_authors,
               "files": {n: sha256(out / n) for n in ("train.csv", "test.csv")}}
    write_text(out / "scrub_summary.md", summary_md(summary))
    return summary


def _table(header: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return lines + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def summary_md(s: dict) -> str:
    items, report, meta = s["items"], s["report"], s["meta"]
    by_rule = Counter((r["rule"], r["action"]) for r in report)
    rules = sorted({r for r, _ in by_rule})
    review = [r for r in report if r["action"] == "needs_review"]
    changed = sorted({r["id"] for r in report if r["action"] == "replaced"})
    released16 = [it for it in items if it["record_id"] in meta["authors"]]
    before = sorted({(it["id"], n) for it in items for n in names_in(it["original_text"], meta["names"])})
    after = sorted({(it["id"], n) for it in items for n in names_in(it["text"], meta["names"])})
    in_attr = sorted({(it["id"], n) for it in items for n in names_in(it["attribution"], meta["names"])})
    splits = [("train", lambda it: it["split"] == "train"), ("test", lambda it: it["split"] == "test"),
              ("test, Public", lambda it: it["Usage"] == "Public"),
              ("test, Private", lambda it: it["Usage"] == "Private"), ("all", lambda it: True)]

    L = ["# Public release staging: scrub summary", "",
         "Built by `python -m dmaic_planner.release` (PYTHONPATH=src). Re-running on the same inputs "
         "gives byte-identical files; the hashes below let you confirm that. "
         "**Do not publish `scrub_report.csv`: it holds the original names.**", ""]
    L += _table(["File", "Rows", "sha256"],
                [["train.csv", sum(it["split"] == "train" for it in items), s["files"]["train.csv"]],
                 ["test.csv", sum(it["split"] == "test" for it in items), s["files"]["test.csv"]]])
    L += ["", f"Stack Exchange usernames and profile links in `attribution`: "
          f"{'yes' if s['with_se_authors'] else 'no'} (`--no-se-authors` leaves them out).", "",
          "## Scrub results", ""]
    L += _table(["Rule", "Replaced", "Needs review", "Kept after review"],
                [[r, by_rule[(r, "replaced")], by_rule[(r, "needs_review")], by_rule[(r, "kept")]] for r in rules]
                or [["(no findings)", 0, 0, 0]])
    L += ["", f"Items with at least one replacement: {len(changed)} of {len(items)}"
          + (f" ({', '.join(changed)})." if changed else "."),
          f"NEEDS REVIEW spans: {len(review)} in {len({r['id'] for r in review})} item(s).", "",
          "## NEEDS REVIEW", ""]
    if review:
        L += ["Left unchanged. To settle one, add `(\"id\", \"span\"): \"keep\"` or `: \"replacement\"` to "
              "`REVIEW_DECISIONS` in `src/dmaic_planner/release.py` and rebuild.", ""]
        L += _table(["id", "split", "rule", "span", "context", "note"],
                    [[r["id"], r["split"], r["rule"], f"`{r['original']}`", r["context"].replace("|", "\\|"), r["note"]]
                     for r in review])
    else:
        L += ["None."]
    kept = [r for r in report if r["action"] == "kept"]
    if kept:
        L += ["", "## Reviewed and kept", "", "Settled as \"keep\" in `REVIEW_DECISIONS`; the text is unchanged.", ""]
        L += _table(["id", "split", "rule", "span", "context"],
                    [[r["id"], r["split"], r["rule"], f"`{r['original']}`", r["context"].replace("|", "\\|")]
                     for r in kept])
    rep = [r for r in report if r["action"] == "replaced"]
    if rep:
        L += ["", "## Replacements", ""]
        L += _table(["id", "rule", "replacement", "context (original)"],
                    [[r["id"], r["rule"], r["replacement"], r["context"].replace("|", "\\|")] for r in rep])
    kinds = Counter(it["source"] for it in released16)
    L += ["", "## Issue #16 check", "",
          f"- Raw records with an `author=` value: {len(meta['authors'])} "
          f"({', '.join(f'{k} {v}' for k, v in sorted(meta['raw_by_source'].items()))}).",
          f"- Distinct names among them: {len(set(meta['authors'].values()))}.",
          f"- Released items whose source record is one of them: {len(released16)} "
          f"({', '.join(f'{k} {v}' for k, v in sorted(kinds.items()))}); "
          f"distinct names: {len({meta['authors'][it['record_id']] for it in released16})}.",
          f"- Those names found in the released text before the scrub: {len(before)}; after: {len(after)}.",
          f"- Those names found in the `attribution` column: {len(in_attr)} item(s), "
          f"{len({n for _, n in in_attr})} distinct name(s), on these sources: "
          f"{', '.join(sorted({it['source'] for it in items if it['id'] in {i for i, _ in in_attr}})) or 'none'}.",
          "", "## Split and labels", ""]
    L += _table(["Label"] + [n for n, _ in splits],
                [[m] + [sum(it["label"] == m for it in items if f(it)) for _, f in splits] for m in METHODOLOGIES]
                + [["total"] + [sum(1 for it in items if f(it)) for _, f in splits]])
    L += ["", "## How each label was decided", ""]
    decided = sorted({it["decided_by"] for it in items})
    L += _table(["Decided by"] + [n for n, _ in splits[:2]] + ["all"],
                [[d] + [sum(it["decided_by"] == d for it in items if f(it)) for _, f in (splits[0], splits[1], splits[4])]
                 for d in decided])
    L += ["", "## Sources", ""]
    L += _table(["Source", "train", "test", "all", "storage"],
                [[src, sum(it["source"] == src and it["split"] == "train" for it in items),
                  sum(it["source"] == src and it["split"] == "test" for it in items),
                  sum(it["source"] == src for it in items),
                  ", ".join(sorted({it["storage_mode"] for it in items if it["source"] == src}))]
                 for src in sorted({it["source"] for it in items})])
    L += ["", "## Text length (whitespace-separated words, released text)", ""]
    rows = []
    for name, f in (splits[0], splits[1], splits[4]):
        w = [len(it["text"].split()) for it in items if f(it)]
        rows.append([name, len(w), statistics.median(w), min(w), max(w)])
    L += _table(["Split", "Items", "Median", "Min", "Max"], rows)
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# check
# --------------------------------------------------------------------------- #

def check(out: Path = OUT, strict: bool = False, with_se_authors: bool = True) -> int:
    """Re-scan the staged files. 0 when clean; 1 when a flagged pattern remains or the files are off.

    An issue #16 name may appear only in the `attribution` column of a Stack Exchange item, and
    only when the release credits Stack Exchange authors (the default). Anywhere else it fails."""
    problems: list[str] = []
    if not (out / "train.csv").exists() or not (out / "test.csv").exists():
        print(f"error: {out} has no train.csv / test.csv. Build it first: python -m dmaic_planner.release")
        return 1
    _, names = issue16_names(read_csv(RAW))
    id_map = {r["id"]: r for r in read_csv(ID_MAP)}
    rows = [dict(r, split="train") for r in read_csv(out / "train.csv")] + \
           [dict(r, split="test") for r in read_csv(out / "test.csv")]

    ids = [r["id"] for r in rows]
    if sorted(ids) != sorted(id_map) or len(set(ids)) != len(ids):
        problems.append(f"ids do not match id_map.csv one to one ({len(ids)} staged, {len(id_map)} expected)")
    for r in rows:
        m = id_map.get(r["id"])
        if m and (r["label"] != m["label"] or r["split"] != m["split"]
                  or (r["split"] == "test" and r.get("Usage") != m["Usage"])):
            problems.append(f"{r['id']}: label, split or Usage differs from id_map.csv")

    review = in_text = 0
    in_attribution: set[str] = set()
    for r in rows:
        s = scrub(r["text"], government=r["source"] == "GAO Reports", known_names=names,
                  decisions=item_decisions(r["id"]))
        for f in s.replaced:
            problems.append(f"{r['id']}: {f.rule} still matches {f.original!r}")
        review += len(s.needs_review)
        in_text += len(names_in(r["text"], names))
        is_se = r["source"].startswith("Stack Exchange")
        for n in names_in(r["attribution"], names):
            in_attribution.add(n)
            if not (is_se and with_se_authors):
                problems.append(f"{r['id']}: issue #16 name {n!r} in attribution, where it is not allowed")
        for col in ("source", "source_url", "license", "storage_mode", "label", "decided_by"):
            for n in names_in(r.get(col) or "", names):
                problems.append(f"{r['id']}: issue #16 name {n!r} in {col}")
    if strict and review:
        problems.append(f"{review} NEEDS REVIEW span(s) have no decision in REVIEW_DECISIONS")

    for p in problems:
        print(f"  ! {p}")
    status = "FAILED" if problems else "passed"
    print(f"check {status}: {len(rows)} rows, {len(problems)} problem(s), "
          f"{review} NEEDS REVIEW span(s) awaiting a decision; issue #16 names: {in_text} in text, "
          f"{len(in_attribution)} distinct in attribution")
    return 1 if problems else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT, help="staging folder (default: %(default)s)")
    ap.add_argument("--check", action="store_true", help="re-scan the staged files instead of building")
    ap.add_argument("--strict", action="store_true", help="with --check: also fail on undecided NEEDS REVIEW spans")
    ap.add_argument("--no-se-authors", action="store_true",
                    help="leave Stack Exchange usernames and profile links out of the attribution column")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")   # names with non-ASCII letters on a cp1252 console
    if args.check:
        sys.exit(check(args.out, args.strict, not args.no_se_authors))
    s = build(args.out, not args.no_se_authors)
    rep = s["report"]
    print(f"wrote {args.out}: train.csv ({sum(i['split'] == 'train' for i in s['items'])}), "
          f"test.csv ({sum(i['split'] == 'test' for i in s['items'])}), scrub_report.csv, scrub_summary.md")
    print(f"  {sum(r['action'] == 'replaced' for r in rep)} replacement(s), "
          f"{sum(r['action'] == 'needs_review' for r in rep)} NEEDS REVIEW span(s). "
          "Read scrub_summary.md, then: python -m dmaic_planner.release --check")


if __name__ == "__main__":
    main()
