---
pretty_name: DMAIC Planner
license: cc-by-sa-4.0
language:
- en
task_categories:
- text-classification
task_ids:
- multi-class-classification
size_categories:
- n<1K
---

# Dataset Card for DMAIC Planner

> **Public copy.** This document comes from the project's private course repository, which
> holds the full project history and is available to the ARI 410/510 instructor on request.
> Commands such as `python tasks.py ...`, issue and pull-request numbers, and files that are
> not in this repository refer to that private repository.

> **Content warning.** Some items describe medical errors and patient harm; three describe a
> patient's death. Others are consumer complaints about fraud, debt collection and lost money,
> written in angry language, and workplace questions about conflict with managers and
> coworkers. None of the text is graphic, but it is real (or a close summary of real events).

## Dataset Description

- **Repository:** <https://github.com/jeraddunne/dmaic-planner>
- **Point of contact:** Jerad Dunne (GitHub `jeraddunne`)
- **Course:** ARI 410/510, University of Michigan-Flint, Fall 2026

### Dataset Summary

DMAIC Planner is a small English dataset for one decision that every continuous-improvement
team makes at intake: given a description of a problem, how should it be handled? Each of the
60 items is a short narrative with one of five labels:

| Label | Meaning |
|---|---|
| `JUST_DO_IT` | Somebody just go fix it: the cause and the fix are both stated, and the fix is small. |
| `KAIZEN_EVENT` | Get the right people in a room for a few days: a flow problem whose cause is roughly understood. |
| `DMAIC` | Measure before you fix: an existing process fails and nobody knows why. |
| `DMADV` | Design something that does not exist yet: no process today, or one that could never meet the requirement. |
| `NOT_CPI` | Not a process-improvement problem: really a request for money, staff, policy or a purchase. |

The narratives come from eight public sources: CFPB consumer complaints, GAO audit findings,
help-desk ticket threads, workplace and project-management questions from Stack Exchange, and
team-written summaries of patient-safety cases and Baldrige award applications. Students in
ARI 410/510 labeled them in the project's first annotation round, and the 60 labeled items
became the training and test data of the course's Kaggle competition. Now that the competition
is over, this release contains both splits with their labels. Personal names were removed from
the text first (see [Personal and Sensitive Information](#personal-and-sensitive-information)).

Read the labels with care. The annotators agreed only slightly more often than chance
(Fleiss' kappa 0.08 on the shared items, against a target of 0.70), and 45 of the 60 labels
rest on a single annotator. Each label is one trained reader's judgment under written
guidelines, not a settled fact about the problem.

### Supported Tasks and Leaderboards

**Text classification** (`multi-class-classification`, 5 labels). Input: `text`. Target:
`label`. The metric is **macro-averaged F1**: the F1 score of each label, averaged with equal
weight. The labels are uneven (`DMADV` has 3 items in total), and accuracy would reward a model
that never predicts the rare ones.

The test set was split in half for the Kaggle competition: 10 items scored the public
leaderboard during the competition and 10 scored the private leaderboard that gave the final
ranking. Every label appears in both halves. The `Usage` column in `test.csv` records which
half each item was in.

#### Leaderboard

Every run in the competition, plus the team's baselines and LLM baselines, re-scored with
macro-F1 on the full 20-item test set (public and private halves together). The table is the
Step 0 leaderboard from [`docs/model_choice.md`](model_choice.md)
(`python tasks.py leaderboard`). Participant files are the host's download from Kaggle on
2026-11-26, and each approach is as the participant described it on the Phase 2b form. The
re-scored public and private scores match Kaggle's own scores to 1e-6.

| # | Participant | Run ID | Kaggle submission | Approach | Full macro-F1 | 95% CI | Public | Private |
|---|---|---|---|---|---|---|---|---|
| 1 | Host (Phase 2a LLM baseline) | llm_gpt_5_5 | host file | gpt-5.5 zero-shot, guidelines prompt, U-M gateway, temperature 1.0 | 0.31909 | 0.11-0.50 | 0.21333 | 0.38095 |
| 2 | Host (Phase 2a baseline) | random | host file | Uniform random label, one seeded draw | 0.26333 | 0.06-0.43 | 0.30000 | 0.16667 |
| 3 | Host (Phase 3 candidate) | C2 | not submitted | MiniLM embeddings + logistic regression + the five route definitions | 0.22020 | 0.08-0.34 | 0.23333 | 0.19429 |
| 4 | Host (Phase 2a LLM run) | llm_gpt_6_astra | host file | gpt-6-astra zero-shot, same prompt and settings | 0.20303 | 0.06-0.33 | 0.06667 | 0.29333 |
| 5 | Hina Kramer | dmaic_minilm_v1 | 58283948 | MiniLM embedding of the narrative vs. the five route definitions, nearest definition; no training labels | 0.18667 | 0.08-0.27 | 0.20000 | 0.16667 |
| 6 | Host (Phase 3 candidate) | C1 | not submitted | The team's reproduction of Hina Kramer's run | 0.17714 | 0.06-0.26 | 0.20000 | 0.11429 |
| 7 | Belhassen Khefacha | run1 | 58451301 | BERT [CLS] embeddings + Lab 3 MLP (hidden 64, 23 epochs) | 0.17167 | 0.02-0.30 | 0.18000 | 0.13000 |
| 8 | Belhassen Khefacha | run2 (selected on Kaggle) | 58451852 | all-mpnet-base-v2 embeddings + Lab 3 MLP with class weights (hidden 256, 8 epochs) | 0.16457 | 0.03-0.29 | 0.28000 | 0.05714 |
| 9 | Aymen Masmoudi | run1 | 58313799 | MiniLM embeddings + MLP (32 units, alpha 0.1), chosen by leave-one-out CV | 0.15043 | 0.03-0.27 | 0.19429 | 0.06667 |
| 10 | Host (Phase 2a baseline) | majority | host file | Always the most common training label | 0.09231 | 0.04-0.13 | 0.09231 | 0.09231 |
| 11 | Abdulhakim YM Abayu | run1 | 58847443 | Linear SVM (C=1) on word + character TF-IDF plus route keyword cues | 0.08970 | 0.00-0.17 | 0.05714 | 0.10000 |
| 12 | ShaunWS (no form response) | none | 57959591 | Not described: submitted with no form response | 0.08333 | 0.02-0.13 | 0.09231 | 0.07273 |
| 13 | Host (Phase 2a baseline) | tfidf_svm | host file | TF-IDF (1-2 grams) + class-balanced linear SVM | 0.08333 | 0.00-0.16 | 0.12000 | 0.06667 |
| 14 | Abdulhakim YM Abayu | not in form | 58848065 | Second submission, not described in the form | 0.02857 | 0.00-0.07 | 0.00000 | 0.05714 |

Ranks follow full macro-F1, then accuracy (rows 12 and 13 tie on macro-F1). The 95% interval
is a 2,000-draw bootstrap over the 20 test items. "Host file" is one of the team's own Kaggle
submissions; C1 and C2 were scored offline and never submitted. ShaunWS is the Kaggle username
on one submission made on 2026-11-03, before the Phase 2b window; it has no form response, so
the run has no description and no confirmed owner.

With 20 test items, one item is 5 percentage points of accuracy, and the 2 `DMADV` test items
carry one fifth of the macro-F1 weight between them. Small differences between runs are noise:
a single seeded random guess (row 2) beat every participant run, and the intervals of the top
runs overlap widely.

**Deployed model.** The system built in Phase 3 runs C2, refit on all 60 labeled items (train
and test together). C2 builds on Hina Kramer's definitions-only approach. Its training and
limitations are covered by the project's model card, not here.

### Languages

English (`en`). The writers are U.S. consumers (CFPB), GAO analysts, Stack Exchange users,
help-desk staff and customers, and, for the paraphrased sources, the project team. The
help-desk tickets use non-standard English (for example "Dears" as a greeting and "chick" for
"check").

## Dataset Structure

### Data Instances

One row of `train.csv`:

```json
{
  "id": "dmaic_003",
  "text": "A health system found that its event reporting policies and practices were inefficient, leaving safety event responses incomplete because issues were not reliably escalated or followed up.",
  "label": "KAIZEN_EVENT",
  "decided_by": "single annotator",
  "n_labels": "1",
  "source": "PA Patient Safety Authority: Lessons from Event Reports",
  "source_url": "https://patientsafety.pa.gov/EventReporting/Pages/Improving-Reporting-Tiered-Huddles-Story.aspx?ctg=Communication",
  "attribution": "Team paraphrase of a PA Patient Safety Authority event-report story",
  "license": "CC BY-SA 4.0 (team-written paraphrase; the source text is not included)",
  "storage_mode": "paraphrase"
}
```

`test.csv` rows have the same fields plus `Usage`.

### Data Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Item id, `dmaic_001` to `dmaic_060`. The same ids the Kaggle files used. |
| `text` | string | The narrative as annotators read it, after the name scrub. Can contain line breaks. |
| `label` | string | `JUST_DO_IT`, `KAIZEN_EVENT`, `DMAIC`, `DMADV` or `NOT_CPI`. |
| `Usage` | string (test only) | `Public` or `Private`: the Kaggle leaderboard the item counted toward. |
| `decided_by` | string | How the label was reached: `single annotator`, `majority` or `adjudicated` (see [Annotations](#annotations)). |
| `n_labels` | integer | How many annotators labeled the item: 9 for the shared items, 1 for the rest. |
| `source` | string | The source collection. |
| `source_url` | string | The source document. CFPB items link to the complaint; help-desk tickets link to the dataset page, since tickets have no page of their own. |
| `attribution` | string | The credit line for this item. For Stack Exchange items it names the author's username and links to their profile. |
| `license` | string | The terms that apply to this item's text (see [Licensing Information](#licensing-information)). |
| `storage_mode` | string | `verbatim` (source text) or `paraphrase` (a summary written by the team). |

The files are UTF-8 CSV with a header row. `text` often spans several lines inside quotes, so
read the files with a CSV parser (`pandas.read_csv`, Python's `csv` module), not line by line.

### Data Splits

| Split | Items |
|---|---|
| train | 40 |
| test | 20 (10 public, 10 private) |

Label distribution:

| Label | train | test | test, public | test, private | all |
|---|---|---|---|---|---|
| `JUST_DO_IT` | 10 | 5 | 3 | 2 | 15 |
| `KAIZEN_EVENT` | 7 | 3 | 1 | 2 | 10 |
| `DMAIC` | 12 | 6 | 3 | 3 | 18 |
| `DMADV` | 1 | 2 | 1 | 1 | 3 |
| `NOT_CPI` | 10 | 4 | 2 | 2 | 14 |
| **total** | 40 | 20 | 10 | 10 | 60 |

Items by source:

| Source | train | test | all | Stored as |
|---|---|---|---|---|
| AHRQ PSNet WebM&M | 7 | 4 | 11 | paraphrase |
| GAO Reports | 6 | 4 | 10 | verbatim |
| CFPB Consumer Complaint Database | 7 | 2 | 9 | verbatim |
| Stack Exchange: workplace.stackexchange.com | 5 | 3 | 8 | verbatim |
| Stack Exchange: pm.stackexchange.com | 5 | 2 | 7 | verbatim |
| Mendeley Help Desk Tickets | 5 | 2 | 7 | verbatim |
| PA Patient Safety Authority: Lessons from Event Reports | 3 | 3 | 6 | paraphrase |
| NIST Baldrige Application Summaries | 2 | 0 | 2 | paraphrase |

How each label was reached:

| Decided by | train | test | all |
|---|---|---|---|
| single annotator | 29 | 16 | 45 |
| majority | 1 | 1 | 2 |
| adjudicated | 10 | 3 | 13 |

Length, in whitespace-separated words: median 230.5 over all items (train 207.5, test 249),
ranging from 27 to 650.

**How the split was made.** `python tasks.py kaggle` (`src/dmaic_planner/competition.py`)
split the 60 labeled items by label with seed 20261105: 20 items to test, at least 2 of every
label, the rest to train. Within each label the test items alternate between the public and
private halves, so every label appears on both leaderboards. There is no separate validation
split; with 40 training items, use cross-validation inside `train.csv`. No item is synthetic.
No source document appears twice in the release, and no near-duplicate group (TF-IDF cosine
0.85 or higher, `dupe_groups.csv`) spans train and test. Four of the 20 test items
are shared items with 9 labels each; the other 16 have one label each.

## Dataset Creation

### Curation Rationale

When a problem reaches a continuous-improvement team, the first decision is how to attack it,
and a wrong call is expensive either way: a small fix run as a months-long DMAIC project ties
up a team, and a variation problem run as a short workshop fails in public. That judgment
usually sits with a few trained practitioners, and they apply it inconsistently. The project
proposal (`PROPOSAL.md`) set out to capture it as labeled data, using real narratives instead
of textbook cases, because real problem reports hedge, mix several problems and leave the
deciding facts implicit. The proposal reports that no public dataset labels problem
narratives with an improvement route.

### Source Data

#### Initial Data Collection and Normalization

The team collected 373 narratives from eight public sources on 2026-09-11
(`docs/collection_report.md`), each sampled by a written procedure:

| Source | Collected | How it was sampled |
|---|---|---|
| CFPB Consumer Complaint Database | 138 | Seeded reservoir sample of the bulk export: narrative present, 500+ characters, 2019 or later, 5 product categories |
| GAO Reports | 80 | Report pages sampled across 2019 to 2026; kept where "What GAO Found" is 300+ characters and a recommendation exists |
| Stack Exchange (pm and workplace) | 70 | API search on process and workflow tags, accepted answer, top by score, question body over 300 characters |
| AHRQ PSNet WebM&M | 26 | Case pages enumerated by number; process-problem cases selected across the range |
| Mendeley Help Desk Tickets | 25 | Scored sample of the 360 tickets that have reporter messages |
| PA Patient Safety Authority | 24 | All unique stories across 6 categories |
| NIST Baldrige Application Summaries | 10 | Application summaries with a usable challenge narrative |

The 60 items in this release are the first annotation round's draw from that pool
(`annotation/build_batches.py`, seed 20260920): 15 shared items that every annotator labeled,
and 45 further items, 5 per annotator. Both draws were stratified across the eight sources.

`text` is the narrative exactly as annotators saw it. Two sources were lightly cleaned for
reading: CFPB complaints show the CFPB's own redaction marks as `[redacted]` and `[date]`, and
help-desk tickets are whole email threads with one paragraph per message and the publisher's
anonymization shown as `[user]`, `[system]`, `[name]` and similar. Several sources also publish
how the problem was fixed; that text was never shown to annotators and is not in this release.
For GAO reports, `text` is the "What GAO Found" section.

Three sources (AHRQ PSNet, PA Patient Safety Authority, NIST Baldrige) do not allow their text
to be redistributed. For those 19 items, `text` is a summary of two to six sentences written by
the team, and `source_url` points to the original.

#### Who are the source language producers?

CFPB items were written by U.S. consumers filing complaints. GAO items were written by GAO
analysts. Stack Exchange items were written by the users who asked the questions. Help-desk
items are messages between an IT service desk and its customers, published as a research
dataset on Mendeley Data. The paraphrased items were written by the project team from the
source documents. No demographic information about any writer is available or recorded.

### Annotations

#### Annotation process

Annotators followed [`docs/annotation_guidelines.md`](annotation_guidelines.md), written for
readers with no Lean Six Sigma background: a plain-language definition of each label, one
worked example per label, a tie-breaker order for close calls, and a table of hard cases
decided in advance. Every returned label is stamped guidelines version 1.0; the changelog
records that the v1.1 draft's clarifications (chiefly how to tell `DMAIC` from `DMADV`) were
also in the annotation tool's help text.

Each annotator received one self-contained HTML file and worked offline in a browser. For each
item they chose the label first, then answered questions about Lean wastes and seven intake
questions, then gave a confidence (high, medium or low) and an optional note. Only the label is
in this release. The rules were to work independently, not to look up the source, and not to
ask an AI model to choose a label.

The round produced 180 labels, made between 2026-09-24 and 2026-10-26. The tool recorded
active time per item: a median of 125 seconds per label.

#### Who are the annotators?

Nine annotators, each of whom labeled 20 items (the 15 shared items and 5 of their own):

- **Team members (4):** Reshu Jain, Shaun Sarcona, Bradley Moore and Turrell Taylor. Turrell
  Taylor's labels come from his pilot batch, labeled on 2026-09-24, weeks before the other
  eight files.
- **ARI 410/510 classmates (5):** assigned by the course and credited only by anonymous ID,
  `ext01` to `ext05`, as the guidelines promised them.

No Lean Six Sigma training was required, and no demographic information was collected. Jerad
Dunne, the team's annotation lead, wrote the guidelines and did not label, so that he could
adjudicate. The guidelines planned for 12 external annotators; round 1 had five. Per-annotator
labels are not part of this release; only the final label is.

#### Agreement

Agreement is Fleiss' kappa on the label, computed over the 15 shared items that all nine
annotators labeled (`src/dmaic_planner/round_review.py`):

| Group | Annotators | Fleiss' kappa |
|---|---|---|
| All | 9 | 0.08 |
| Team members only | 4 | 0.05 |
| Classmates only | 5 | 0.07 |
| Target | | 0.70 |

Across all nine annotators, two labels on the same item matched 30 percent of the time, against
24 percent expected by chance. For comparison, the four team annotators reached 0.49 on an
earlier practice round of 8 synthetic items. Only 2 of the 15 shared items reached a majority
(7 of 9 each). `NOT_CPI` was the most common answer on the shared items, 49 of the 135 labels,
even though every narrative was collected as a process problem.

The low score has two likely causes, and the data cannot separate them: the guidelines did not
make the boundaries between labels clear enough, and the task asks for a judgment that
practitioners also disagree on.

#### How the ground truth was decided

The rules were agreed in issue #27 and applied by `python tasks.py review`:

1. An item with one label (the 45 non-shared items) takes that label.
2. A shared item takes the majority label when at least 60 percent of its labels agree (6 of
   9), unless at least half of those votes were low-confidence.
3. Otherwise (a tie for first place or a weaker majority) a confidence-weighted vote picks the label (high 1.0, medium 0.67, low 0.33, exact
   ties broken by the guidelines' tie-breaker order), and the label stays provisional until an
   adjudicator confirms or overrides it.

Result: 45 labels from a single annotator, 2 by majority, and 13 by the weighted vote. The
adjudicator, Jerad Dunne, accepted the confidence-weighted tie-breaker's pick on all 13
tie-break items and overrode none.

### Personal and Sensitive Information

**Protection at the source.** The CFPB removes personal information from complaint narratives
before publishing them, and its redaction marks appear as `[redacted]` and `[date]`. The
help-desk dataset's publisher replaced names and systems with placeholders. The patient-safety
and Baldrige items are team-written summaries that name no patient, staff member or reporter.

**The release scrub.** `src/dmaic_planner/release.py` builds this release from the competition
files and removes names of private individuals from `text`: patients, consumers, employees,
ticket senders, coworkers and Stack Exchange users. A name becomes `[person]`. It looks for
email addresses, phone numbers and long numbers (the same patterns the project's raw-data check
uses), @handles, a name after a title ("Dr. X"), a name after a relationship word ("my manager
X", "coworker (X)"), a name under a sign-off ("Regards, X"), common first names followed by a
surname, and any later mention of a name it has already replaced. Organization and agency names
are kept. A person named in a GAO report is taken to be an official acting in that role and is
left for human review rather than replaced. Spans the rules are unsure about (a capitalized word
that is not a known first name, a court-case citation, a firm named after people) are listed
for review and never changed silently. The script is deterministic, and
`python -m dmaic_planner.release --check` fails if any pattern it would replace is still present.

Results on these 60 items: one item changed, a Stack Exchange question in which the writer
names a coworker (two mentions, both replaced). Six spans in two items were flagged for
review, and the team reviewed them and kept all six: four mentions of a debt-collection law
firm whose name is made of surnames (an organization, kept under the rule above), and two
court-case citations that a consumer quoted in a complaint (published case law). The decisions
are recorded in `REVIEW_DECISIONS` in `release.py`. No email address, phone number, handle or
long number was found.

**Issue #16.** The raw collection stores the author's name with 96 records (40 from
pm.stackexchange.com, 30 from workplace.stackexchange.com, 26 from AHRQ PSNet, where the name is
the published case commentator). These are attribution metadata, not narrative text. 26 of the
60 released items come from those records (15 Stack Exchange, 11 PSNet; 24 distinct names). The
release checks the text of every item against all of the stored names: none appears in `text`,
before or after the scrub.

**Stack Exchange usernames in `attribution`.** Each of the 15 Stack Exchange items carries its
author's Stack Exchange username and a link to the author's profile in the `attribution` column
(13 distinct usernames; one author has no profile link on record). They are there because the
posts are licensed CC BY-SA, and Stack Exchange's attribution requirements ask anyone who
reuses a post to name its author and link to the author's profile. These are the public names
the authors chose to post under. They appear only in `attribution`, never in `text`, and the
other issue #16 names (the 11 PSNet case commentators) appear in no column at all.
`python -m dmaic_planner.release --check` fails if any of these names turns up anywhere else, and
`--no-se-authors` builds the release without the usernames.

**Other sensitive content.** Patient-safety items describe medical errors and their outcomes.
Complaint items describe fraud, debts and disputes with named companies. The data has no
demographic fields, and no label is about a person.

## Considerations for Using the Data

### Social Impact of Dataset

The intended use is teaching and research on routing improvement work, and a first-pass triage
aid whose output a person reviews before anything is chartered. Do not use the data, or a model
trained on it, to approve or reject projects automatically, to judge employees or the people
who wrote the narratives, to decide how a consumer complaint is handled, or to make any
clinical decision. A wrong `NOT_CPI` call in particular can send a real problem back unfixed.

### Discussion of Biases

- **Source and label travel together.** Both Baldrige items are `NOT_CPI`; the 3 `DMADV` items
  come only from GAO (2) and PSNet (1); no help-desk or PA Patient Safety item is `NOT_CPI`;
  no CFPB item is `KAIZEN_EVENT`. A model can score points by recognizing the source's style
  instead of the problem.
- **Paraphrase style.** All 19 healthcare items are summaries written by the team in one
  plain style, so writing style and sector are confounded.
- **Who labeled.** The annotators are students, not practicing improvement specialists. Their
  calls reflect the guidelines and their own reading, and may differ from what an experienced
  practitioner would choose.
- **Coverage.** The text is English and the sources are mostly U.S. (federal audits, U.S.
  consumer complaints, a Pennsylvania patient-safety agency). Sectors are uneven: healthcare
  19 items, federal administration 10, financial services 9, workplace operations 8, project
  management 7, IT services 7, and no manufacturing item.

### Other Known Limitations

- **Labels are unreliable.** Fleiss' kappa 0.08 on the shared items is near chance, and 45 of
  the 60 labels (16 of the 20 test items) come from a single annotator, with no second label to
  check them against. A model's errors on this test set may be label errors.
- **The dataset is tiny.** 60 items, 3 of them `DMADV`, and only 1 `DMADV` item in train.
  Per-label scores for `DMADV` rest on 2 test items.
- **`NOT_CPI` has no examples collected as such** (issue #18). Every narrative was collected
  because it described a process problem; the 14 `NOT_CPI` labels are annotators deciding that a
  collected problem is really a request for money, staff or policy. A model may not recognize a
  plain resource request, which is what a `NOT_CPI` item looks like in practice.
- **GAO findings can contain their own fix** (issue #23). In 14 raw GAO records more than 30
  percent of the recommendation's wording also appears in the narrative. None of the 10 GAO
  items in this release is one of those 14 (all 10 have zero overlap), but GAO findings still
  tend to say in general terms what would help (for example, `dmaic_051` says that additional
  outreach could help charter schools), which hints at the label.
- **A large source was left out** (issue #19). Oversight.gov holds over 12,000 open
  inspector-general recommendations, but its `robots.txt` carries an `ai-train=no` signal, and
  the team collected nothing from it while that question is open. Federal oversight findings are
  represented by GAO alone.
- **Text varies a lot.** Items run from 27 to 650 words. Help-desk threads repeat messages and
  are full of placeholders; GAO findings are long and formal.
- **Not included.** The annotation round also collected Lean waste tags and seven intake
  answers per item. They are not part of this release.

## Additional Information

### Dataset Curators

The DMAIC Planner team, ARI 410/510, University of Michigan-Flint, Fall 2026: Jerad Dunne,
Reshu Jain, Shaun Sarcona, Bradley Moore and Turrell Taylor.

### Licensing Information

The dataset (text and labels) is released under the **Creative Commons
Attribution-ShareAlike 4.0 International** license (CC BY-SA 4.0,
<https://creativecommons.org/licenses/by-sa/4.0/>); the full text is in `LICENSE-DATA.txt`. The
share-alike terms come from the Stack Exchange items, and CC BY-SA 4.0 can carry the more
permissive sources along with them. [`LICENSE.md`](../LICENSE.md) explains the reasoning. The
code that builds the release is MIT licensed.

Each item's `license` column gives the terms for its text:

| Items | `license` |
|---|---|
| 19 | CC BY-SA 4.0, team-written paraphrase (PSNet 11, PA Patient Safety 6, Baldrige 2). The source documents are not included and remain with their owners. Keep the `storage_mode` marking if you redistribute, and do not replace a paraphrase with source text. |
| 10 | Public domain, U.S. Government work (GAO) |
| 9 | Public domain, CC0 / U.S. Government work (CFPB) |
| 15 | CC BY-SA, version by the question's posting date (Stack Exchange): 2.5 for 1 item, 3.0 for 8, 4.0 for 6 |
| 7 | CC BY 4.0 (Mendeley Help Desk Tickets, doi:10.17632/btm76zndnt.3) |

Stack Exchange licenses each post by the date it was contributed, according to its licensing
page: CC BY-SA 2.5 before 2011-04-08, CC BY-SA 3.0 from 2011-04-08, and CC BY-SA 4.0 from
2018-05-02. The `license` column gives each Stack Exchange item's version by its question date.
Attribution follows Stack Exchange's requirements: `attribution` names the author's username
and links to their profile, and `source_url` links to the question itself.

The `attribution` column carries the credit line for each item: the GAO report title and
number, the CFPB complaint number, the Stack Exchange question number, date, author username
and profile link, the Mendeley dataset citation, and for paraphrases the source title.

During the Kaggle competition, participants were asked to keep the data inside the course.
That restriction ended with the competition; this release is public.

### Citation Information

> DMAIC Planner dataset. Dunne, J., Jain, R., Sarcona, S., Moore, B., & Taylor, T. (2026).
> ARI 410/510, University of Michigan-Flint. Licensed CC BY-SA 4.0.

```bibtex
@misc{dmaic_planner_2026,
  title        = {{DMAIC Planner} dataset},
  author       = {Dunne, Jerad and Jain, Reshu and Sarcona, Shaun and Moore, Bradley and Taylor, Turrell},
  year         = {2026},
  howpublished = {ARI 410/510, University of Michigan-Flint},
  url          = {https://github.com/jeraddunne/dmaic-planner},
  note         = {Licensed CC BY-SA 4.0}
}
```

### Contributions

Planned team roles are in the team contract (`PROPOSAL.md` section 1), and
what each member did is in the Contributions section of the repository
[`README.md`](../README.md#contributions). Jerad Dunne wrote the annotation guidelines and
adjudicated the 13 tie-breaks. Reshu Jain, Shaun Sarcona, Bradley Moore and
Turrell Taylor labeled items together with five ARI 410/510 classmates (`ext01` to `ext05`).
The competition participants who built the runs on the leaderboard are credited there by name.
The source texts belong to the CFPB, GAO, the Stack Exchange authors (named per item in
`attribution`), and the creator of the Mendeley Help Desk Tickets dataset; the patient-safety and
Baldrige summaries draw on documents published by AHRQ PSNet, the Pennsylvania Patient Safety
Authority and NIST.
