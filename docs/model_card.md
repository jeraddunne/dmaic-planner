---
language:
- en
license: cc-by-sa-4.0
base_model: sentence-transformers/all-MiniLM-L6-v2
pipeline_tag: text-classification
tags:
- text-classification
- sentence-transformers
- logistic-regression
- lean-six-sigma
- continuous-improvement
metrics:
- f1
---

# Model Card for the DMAIC Planner route model `c2-all60-2026-11-26`

> **Public copy.** This document comes from the project's private course repository, which
> holds the full project history and is available to the ARI 410/510 instructor on request.
> Commands such as `python tasks.py ...`, issue and pull-request numbers, and files that are
> not in this repository refer to that private repository.

> **Content note.** The model returns a route name and five probabilities. It does not write
> text. The narratives it was trained on include medical errors and patient harm, angry consumer
> complaints about money and debt, and workplace conflict (see the
> [dataset card's content warning](dataset_card.md)). Do not type names, patient details or other
> personal information into it: it does not need them, and the names of private individuals were
> removed from its training text.

**Where the numbers come from.** Every number in this card names its source file:

- `model.json`: [`models/phase3/c2/model.json`](../models/phase3/c2/model.json), the deployed artifact.
- Step 1 memo: [`docs/model_choice.md`](model_choice.md), the leaderboard and model choice.
- Mistake patterns: [`docs/mistake_patterns.md`](mistake_patterns.md).
- Dataset card: [`docs/dataset_card.md`](dataset_card.md).
- Deploy measurement: `deployed_measure.json`, written by `python tasks.py phase3-deploy`
  (a run output kept in the private course repository; it holds timings only, no labels).
- Step 1 run output: `phase3_models.json`, written by `python tasks.py phase3-models`
  (private course repository).

## Model summary

The DMAIC Planner route model reads a short English description of a problem at work and
suggests how a continuous-improvement team should handle it. It gives a probability for each of
five routes. The definitions below are the ones the model uses, word for word (`model.json`):

| Route | What it means |
|---|---|
| `JUST_DO_IT` | Somebody just go fix it: the cause and the fix are both stated, and the fix is small. |
| `KAIZEN_EVENT` | Get the right people in a room for a few days: a flow problem whose cause is roughly understood. |
| `DMAIC` | Measure before you fix: an existing process fails and nobody knows why. |
| `DMADV` | Design something that does not exist yet: no process today, or one that could never meet the requirement. |
| `NOT_CPI` | Not a process-improvement problem: really a request for money, staff, policy or a purchase. |

It is candidate C2 from Phase 3 of the ARI 410/510 project: frozen `all-MiniLM-L6-v2` sentence
embeddings, a class-balanced logistic regression trained on the labeled narratives and the five
route definitions, and a 75/25 blend with how close the narrative is to each route definition.
This version was refit on all 60 labeled narratives of the public DMAIC Planner dataset.

What to expect:

- **It is a weak model on a hard, noisily labeled task.** Fit on the 40 training narratives, the
  same recipe scored macro-F1 0.22020 on the 20-item test set (95% bootstrap interval 0.08-0.34),
  against 0.31909 for gpt-5.5 zero-shot and 0.26333 for one seeded random guess (Step 1 memo). On
  20 items, none of these gaps can be told apart from chance.
- **Read the top two routes, not just the top one.** In cross-validation on the 60 items, the
  right route was among the top two in 0.626 of predictions; the top route alone was right in
  0.345 (`model.json`).
- **Every prediction carries the same confidence label**, "Low confidence: compare the top two
  routes", because the size of the model's lead did not predict whether it was right.
- **It runs on a CPU at no per-prediction cost**: a median of 67.3 ms per narrative on a laptop
  (deploy measurement).

Use it as a second opinion that a person checks, not as the decision.

## Model details

- **Version:** `c2-all60-2026-11-26`, created 2026-11-26 (`model.json`).
- **Developed by:** the DMAIC Planner team, Group 1, ARI 410/510, University of Michigan-Flint,
  Fall 2026: Jerad Dunne, Reshu Jain, Shaun Sarcona, Bradley Moore and Turrell Taylor.
- **Builds on Hina Kramer's work.** The definitions-only idea comes from Hina Kramer's Phase 2b
  Kaggle submission `dmaic_minilm_v1`: embed the narrative and the five route definitions with
  all-MiniLM-L6-v2 and pick the most similar definition, using no training labels. Our candidate
  C1 reproduces her run (public score 0.20000, the same as hers; 17 of 20 test predictions
  identical to her submitted file; Step 1 memo). C2 uses her idea in two places: the route
  definitions are extra training points for the classifier, and the definition-similarity scores
  make up a quarter of every prediction. Her code:
  <https://colab.research.google.com/drive/1R8eSiphq_bwPXHY-pVbWY_fQEAs77c1x> (Step 1 memo).
- **Model type:** five-class text classifier. A frozen sentence encoder produces a 384-number
  vector per narrative; a multinomial logistic regression head and a nearest-definition score are
  blended into five probabilities. The encoder was not fine-tuned.
- **Base model:** [`sentence-transformers/all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
  at hub revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` (`model.json`), licensed
  Apache 2.0.
- **Language:** English.
- **License:**
  - Model weights (`model.json`): **CC BY-SA 4.0**. They are derived from the DMAIC Planner
    dataset, which is CC BY-SA 4.0, so they carry the same terms
    ([`models/phase3/c2/README.md`](../models/phase3/c2/README.md)).
  - Code (`src/dmaic_planner/phase3_models.py` and the rest of the repository's code): **MIT**,
    [`LICENSE-CODE.txt`](../LICENSE-CODE.txt).
  - Base encoder: Apache 2.0. It is not stored in the repository; it downloads from the Hugging
    Face hub at the pinned revision the first time the model loads.
- **Files:** `models/phase3/c2/model.json` (56,994 bytes, deploy measurement): plain JSON, no
  pickle. It holds the logistic-regression weights and intercepts, the blend weight and
  temperature, the five route definitions, the confidence tier, SHA-256 hashes of the training
  files and the evaluation results. `models/phase3/c2/README.md` is a short summary.
- **Repository:** <https://github.com/jeraddunne/dmaic-planner>
- **Contact:** Jerad Dunne (GitHub `jeraddunne`).

## Intended use

### Direct use

Decision support when choosing an improvement route. A person who has a process-problem narrative
in front of them gets the model's top route and second route, reads both route definitions
against the narrative, and makes the call themselves.

- **Users:** continuous-improvement practitioners and intake reviewers who want a second opinion,
  students learning how the five routes differ, and teams taking a first pass through a backlog of
  problem reports.
- **Input:** one English narrative describing a problem in a work process. The training narratives
  ran from 27 to 650 words (dataset card).
- **Output:** five probabilities that sum to 1, the top route, the second route, and the
  confidence label.

### Out-of-scope use

- **Staffing, hiring, performance or disciplinary decisions**, or any judgment about the people
  who wrote or appear in a narrative. No route label is about a person.
- **Safety-critical triage.** The model does not judge urgency, severity or risk. Do not use it to
  decide how fast a patient-safety event, incident or outage gets attention, or to make any
  clinical decision.
- **A replacement for a Lean Six Sigma lead.** Choosing DMAIC or DMADV commits a team for months
  (the annotation guidelines put DMAIC at about 4 months and DMADV at about 5). That call belongs
  to a trained practitioner and the project sponsor.
- **Automatic approval or rejection** of projects, funding requests or consumer complaints. A
  wrong `NOT_CPI` call in particular can send a real problem back unfixed (dataset card).
- **Text in other languages**, or text that is not a description of a work problem. The model
  does not check either; it returns five probabilities for any text, and for such input they
  mean nothing.
- **General claims about automating route selection.** The model was trained on 60 public
  narratives labeled by students, with low agreement between annotators.

**Who should not rely on it:** anyone who must make or defend a funding, chartering or staffing
decision without reading the narrative themselves; anyone triaging patient-safety events,
security incidents or other urgent cases; and managers assessing employees or the writers of
complaints.

## How to use

Run from the repository root with `src` on `PYTHONPATH`. The repository README gives the install
steps.

```python
from dmaic_planner.phase3_models import load_deployed
model = load_deployed("models/phase3/c2")  # first load downloads the pinned MiniLM revision
proba = model.predict_proba(["Claims sit in the review queue for days and nobody knows why."])[0]
conf = model.confidence(proba)
print(model.version, conf["top"], conf["second"], conf["text"])
```

- `predict_proba` takes a list of strings and returns one dictionary per narrative: route code to
  probability, five entries summing to 1.
- `confidence` returns the top route, the second route, the gap between their probabilities and
  the tier text. For this version the text is always "Low confidence: compare the top two routes".
- `load_deployed` refuses to load if the encoder does not reproduce the training-time definition
  vectors (largest cosine difference above 0.001), which catches a wrong encoder revision. Set
  `HF_HUB_OFFLINE=1` to forbid downloads once the encoder is cached, and `DMAIC_THREADS` to change
  the number of CPU threads (default 4).

For the browser app and its API, see the repository README.

## Training data

The model was trained on the 60 labeled narratives of the public DMAIC Planner dataset
(`train.csv`, 40 items, and `test.csv`, 20 items), the data of the ARI 410/510 Kaggle
competition. The [dataset card](dataset_card.md) covers the sources, annotation process,
agreement scores, how gold labels were decided, the splits and the licenses; this card does not
repeat them.

- **Scrubbed release.** The deployed model was refit on the public release, in which names of
  private individuals in the text were replaced with `[person]` (one item changed; dataset card).
  The SHA-256 hashes of both files are in `model.json` (`train.csv` starts `671e2bab`, `test.csv`
  starts `ba3de783`).
- **The five route definitions** (the table above) were added as five extra training points, one
  per route.
- **Label distribution** (`model.json` for the totals, dataset card for the splits):

| Label | train | test | all 60 |
|---|---|---|---|
| `JUST_DO_IT` | 10 | 5 | 15 |
| `KAIZEN_EVENT` | 7 | 3 | 10 |
| `DMAIC` | 12 | 6 | 18 |
| `DMADV` | 1 | 2 | 3 |
| `NOT_CPI` | 10 | 4 | 14 |
| **total** | 40 | 20 | 60 |

- **Label quality.** Nine annotators reached Fleiss' kappa 0.08 on the 15 items they all labeled
  (target 0.70). 45 of the 60 labels rest on a single annotator, and 13 were settled by a
  confidence-weighted tie-break (dataset card).

## Training procedure

How one prediction is made (`src/dmaic_planner/phase3_models.py`, `model.json`):

1. **Embed.** `all-MiniLM-L6-v2`, frozen, embeds the narrative. The encoder reads 256 tokens at a
   time, so long narratives are split into chunks of up to 254 wordpieces (two tokens go to the
   start and end markers). Each chunk is embedded, the chunk vectors are averaged weighted by their
   token counts, and the result is scaled to length 1.
2. **Classify.** A class-balanced logistic regression on that vector gives five probabilities.
3. **Compare with the definitions.** The cosine similarity between the narrative vector and each
   route definition's vector, divided by a temperature of 0.3, goes through a softmax.
4. **Blend.** Final probability = 0.75 x the classifier's probability + 0.25 x the
   definition-similarity probability.

Settings (`model.json`):

| Setting | Value |
|---|---|
| Logistic regression | scikit-learn 1.9.1, `class_weight="balanced"`, C = 0.1 (strong regularization), `max_iter=5000` |
| Definition points | the five definition vectors, each labeled with its own route, sample weight 5 |
| Blend weight | 0.25 on definition similarity, 0.75 on the classifier |
| Temperature | 0.3: the value in {0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0} with the lowest log loss of the definition-similarity softmax on the 60 training items. The same rule picked 0.2 on the 40-item fit (Step 1 run output). |
| Training rows | 60 narratives + 5 definitions |

**How the settings were chosen.** C, the definition weight and the blend weight were picked by
cross-validation on the 40 training items only: stratified 5-fold, repeated with seeds 42, 123
and 2026. The grid had 48 configurations (C in {0.1, 1, 10, 100}, definition weight in {0, 1, 5},
blend in {0, 0.25, 0.5, 0.75}), ranked by CV macro-F1, then accuracy, then the simpler model. The
winner was C = 0.1, definition weight 5, blend 0.25, with CV macro-F1 0.2840 and accuracy 0.3846;
C1 scored 0.2467 and 0.3590 on the same folds (Step 1 memo). The single DMADV training item stayed
in the training part of every fold, because holding it out would leave no DMADV example to learn
from.

**Order of work.**

1. Choose the settings on 40-item cross-validation.
2. Fit on the 40 training items and score once on the 20 test items.
3. Refit the same recipe on all 60 items. This is the deployed model. The settings were not
   re-tuned on 60; only the temperature was refit, by the rule above.
4. Run cross-validation on the 60 items to set the confidence display and give an updated score
   estimate.

**Software** (`model.json`; Python from the deploy measurement): sentence-transformers 6.3.0,
transformers 5.24.1, torch 2.15.0+cpu, scikit-learn 1.9.1, Python 3.12.10.

**Reproduce** (in the private course repository): `python tasks.py phase3-models` (settings, test score, Step 1 measurements), then
`python tasks.py phase3-deploy` (refit on 60, `model.json`, confidence tier, latency). The deploy
step checks that the weights written to JSON reproduce the fitted model's probabilities to within
1e-9.

## Evaluation

### Test results (the same recipe fit on 40 items)

The deployed model has seen all 60 labeled items, so it has no held-out score of its own. The
results below are for the same recipe fit on the 40 training items and scored once on the 20 test
items, before the refit. The metric is macro-F1, the competition metric: the F1 score of each of
the five routes, averaged with equal weight.

| Metric | Value |
|---|---|
| Macro-F1, full test set (20 items) | 0.22020 |
| 95% bootstrap interval (2,000 draws over the 20 items) | 0.08-0.34 |
| Macro-F1, public half / private half (10 items each) | 0.23333 / 0.19429 |
| Accuracy | 0.30 |

Source: `model.json` (`evaluation.test_from_40_item_fit`) and the Step 1 memo.

Per-route F1 on the full test set, with C1 and gpt-5.5 for comparison (Step 1 memo):

| Model | `JUST_DO_IT` | `KAIZEN_EVENT` | `DMAIC` | `DMADV` | `NOT_CPI` |
|---|---|---|---|---|---|
| C2 (this recipe) | 0.000 | 0.222 | 0.545 | 0.000 | 0.333 |
| C1 (Hina Kramer's approach, reproduced) | 0.000 | 0.000 | 0.600 | 0.000 | 0.286 |
| gpt-5.5 zero-shot | 0.400 | 0.250 | 0.545 | 0.400 | 0.000 |

### Comparison with the other candidates and baselines

All rows are scored on the same 20 test items (Step 1 memo). Latency is the median of 100 warm,
single-narrative predictions on the laptop described under
[Compute, speed and cost](#compute-speed-and-cost). The full leaderboard, with every participant
run, is in the [dataset card](dataset_card.md#leaderboard).

| Run | What it is | Full macro-F1 (95% CI) | Public / Private | Accuracy | Median latency | Cost per prediction |
|---|---|---|---|---|---|---|
| gpt-5.5 (Phase 2a LLM baseline) | zero-shot, guidelines prompt, U-M gateway, temperature 1.0 | 0.31909 (0.11-0.50) | 0.21333 / 0.38095 | 0.35 | not measured | not measured; needs a U-M gateway key |
| Random (Phase 2a baseline) | uniform random label, one seeded draw | 0.26333 (0.06-0.43) | 0.30000 / 0.16667 | 0.25 | n/a | $0 |
| **C2 (this model's recipe)** | MiniLM + logistic regression + route definitions | **0.22020 (0.08-0.34)** | 0.23333 / 0.19429 | 0.30 | 62.3 ms | $0, local CPU |
| gpt-6-astra (Phase 2a LLM run) | zero-shot, same prompt and settings | 0.20303 (0.06-0.33) | 0.06667 / 0.29333 | 0.25 | not measured | not measured |
| Hina Kramer, `dmaic_minilm_v1` (best participant run) | MiniLM, nearest route definition, no training labels | 0.18667 (0.08-0.27) | 0.20000 / 0.16667 | 0.30 | not measured | not measured |
| C1 | our reproduction of Hina Kramer's run | 0.17714 (0.06-0.26) | 0.20000 / 0.11429 | 0.25 | 61.0 ms | $0, local CPU |
| Majority (Phase 2a baseline) | always the most common training label | 0.09231 (0.04-0.13) | 0.09231 / 0.09231 | 0.30 | n/a | $0 |
| TF-IDF + SVM (Phase 2a baseline) | TF-IDF 1-2 grams, class-balanced linear SVM | 0.08333 (0.00-0.16) | 0.12000 / 0.06667 | 0.15 | 1.1 ms | $0, local CPU |

How to read this table:

- **No gap here is statistically clear.** One-sided paired bootstrap, 5,000 resamples (Step 1
  memo): gpt-5.5 over C2, gap 0.0989, p = 0.200; C2 over C1, gap 0.0431, p = 0.216; C2 over Hina
  Kramer's run, gap 0.0335, p = 0.227; random over C2, gap 0.0431, p = 0.310.
- **The random row was a lucky draw.** Averaged over 2,000 draws, random guessing scores 0.18
  macro-F1 on this test set (Step 1 memo).
- **Why C2 was chosen over gpt-5.5.** C2 has the highest score of any run that works on a CPU at
  no cost, and it was chosen on training-set cross-validation alone. It needs no API key and no
  network at prediction time, gives the same answer every time (gpt-5.5 ran at temperature 1.0),
  and returns a probability for every route. gpt-5.5's cost and latency were never measured, and
  serving it from a public link would mean putting a U-M gateway key behind it (Step 1 memo).

### Cross-validation estimate on all 60 items (not a held-out test score)

After the refit there is no unseen labeled data left, so the deploy step ran the same
cross-validation on all 60 items: stratified 5-fold, seeds 42, 123 and 2026, the same settings,
with the model refit inside every fold (`model.json`, `evaluation.cv_estimate_60`). These are
out-of-fold predictions, not a test score, and the settings were chosen on 40 of these 60 items,
so the estimate may be slightly optimistic.

| Estimate | Macro-F1 | Per seed | Accuracy | Top-2 accuracy | Predictions |
|---|---|---|---|---|---|
| Main (3 DMADV items kept in training) | 0.2576 | 0.264, 0.2339, 0.275 | 0.3450 | 0.6257 | 171 (57 items x 3 seeds) |
| Sensitivity (DMADV items held out too) | 0.2453 | 0.2682, 0.2184, 0.2495 | 0.3278 | 0.5889 | 180 (60 items x 3 seeds) |

In the main estimate the 3 DMADV items stay in training in every fold and are never scored, so
the DMADV part of macro-F1 is always 0 and the score cannot exceed 0.80. The sensitivity run
holds each DMADV item out in a different fold, which leaves 2 in training each time.

### Per-route notes

- **`DMAIC`** is the model's best route (test F1 0.545). It is also the easiest route for every
  system in the competition (mistake patterns).
- **`NOT_CPI`** (test F1 0.333) is the route the model over-predicts. In the main
  cross-validation it predicted `NOT_CPI` 65 times out of 171 (`model.json`), while the 14
  `NOT_CPI` items, each scored once per seed, account for 42 of the 171.
- **`KAIZEN_EVENT`** (test F1 0.222) was predicted 30 times in the main cross-validation, the same
  as the 30 scorings of its 10 items.
- **`JUST_DO_IT`** (test F1 0.000) is under-predicted. On the test set the 40-item fit predicted it
  once in 20 (Step 1 memo); in the main cross-validation it was predicted 26 times against 45
  scorings of its 15 items.
- **`DMADV`** (test F1 0.000) is almost never predicted. The 40-item fit had one DMADV example and
  never predicted the route on the test set. The deployed model has three examples; it predicted
  DMADV 4 times out of 171 in the main cross-validation and 3 times out of 180 in the sensitivity
  run (`model.json`). On this test set only gpt-5.5 had a non-zero DMADV F1 (0.400; Step 1 memo).
  Because macro-F1 gives DMADV a fifth of the weight, a model that never predicts it is capped at
  0.80.

## Confidence: how to read it

**What the numbers mean.** The model gives each of the five routes a probability, and the five add
up to 1. With five routes, 0.20 each would be a pure guess. This model's probabilities are flat:
for the 40-item fit, the top probability on the 20 test narratives ranged only from 0.206 to 0.279
(Step 1 memo), and in the 60-item cross-validation the median gap between the top two
probabilities was 0.017 (`model.json`). Read the probabilities as an order of preference, not as a
chance of being right.

**Why every prediction gets the same label.** We tested whether a bigger lead for the top route
means a more reliable answer, using the 171 out-of-fold predictions (`model.json`,
`confidence_tiers`). It does not:

- The lead's ability to tell right answers from wrong ones scored 0.48 (area under the ROC curve;
  0.50 means no signal).
- Split at the median lead, the half with the bigger lead was right 0.326 of the time and the half
  with the smaller lead 0.365.
- Split into thirds, the biggest leads were right 0.298 of the time, the middle third 0.386 and the
  smallest leads 0.351.

The rule was to show a higher tier only where accuracy rises by at least 0.10 across the boundary.
It never rose by that much, and for the biggest leads it was lower, so the model reports one tier
for every prediction:

| Tier | Applies to | Out-of-fold accuracy of the top route | n |
|---|---|---|---|
| Low confidence: compare the top two routes | every prediction | 0.345 | 171 |

**What to do with a prediction.**

1. Look at the top two routes, not only the top one. The right route was in the top two in 0.626
   of out-of-fold predictions (`model.json`). A random ordering would put it there 2 times in 5.
2. Read both route definitions against the narrative. The deciding facts are usually whether the
   cause and the fix are already stated, whether a process exists today, and whether the real ask
   is for money, staff or policy.
3. Make the call yourself, and check it against the
   [annotation guidelines](annotation_guidelines.md), which give a worked example and a
   tie-breaker order for each route.

## Limitations and biases

- **`DMAIC` is the default wrong answer across the competition.** Of the 158 wrong predictions made
  by the 10 systems studied, 62 were `DMAIC`; `JUST_DO_IT` items were most often called `DMAIC`
  (22 times) or `NOT_CPI` (14) (mistake patterns). Most narratives describe a process that is
  failing, which on the surface is what DMAIC means. This model's own lean is toward `NOT_CPI`
  (see the per-route notes), so expect `DMAIC` or `NOT_CPI` when the narrative actually states the
  cause and a small fix.
- **`DMADV` is almost never predicted.** There are 3 DMADV items in the whole dataset. Expect the
  model to miss narratives where no process exists yet or the current one could never meet a new
  requirement.
- **Tie-break items are the hardest.** On 3 test items, only 4 of 9 annotators chose the label that
  became gold through the tie-break; each was wrong for 9 of the 10 systems studied. The mean
  share of systems wrong was 0.90 on tie-break items, 0.775 on single-annotator items and 0.70 on
  the one majority item (mistake patterns). Some of what looks like model error may be label
  noise.
- **Low annotator agreement caps what any model can show.** Fleiss' kappa was 0.08 (target 0.70),
  and two annotators' labels on the same item matched 30% of the time against 24% by chance
  (dataset card). 45 of the 60 labels, and 16 of the 20 test items, rest on one annotator. When
  people agree this rarely, a test score measures agreement with one reader as much as it measures
  the model.
- **The test set is 20 items, so intervals are wide.** One item is 5 percentage points of accuracy,
  the 2 DMADV test items carry a fifth of the macro-F1 weight between them (dataset card), and
  C2's interval runs from 0.08 to 0.34. 18 of the 20 test items were wrong for more than half of
  the 10 systems studied (mistake patterns).
- **No held-out score for the deployed model.** The test result above is for the 40-item fit. The
  60-item number is a cross-validation estimate.
- **Source and sector coverage.** The data comes from eight mostly U.S. sources, uneven by sector:
  healthcare 19 items, federal administration 10, financial services 9, workplace operations 8,
  project management 7, IT services 7, and no manufacturing (dataset card). Source and label
  travel together (both Baldrige items are `NOT_CPI`; the 3 DMADV items come only from GAO and
  PSNet), so the model may learn a source's writing style instead of the problem. All 19
  healthcare items are summaries written by the team in one plain style. Test-set differences by
  source (2 to 4 items each) cannot be told apart from chance (mistake patterns).
- **Plain resource requests may be missed.** Every narrative was collected as a process problem;
  the 14 `NOT_CPI` labels are annotators deciding that a collected problem was really a request for
  money, staff or policy. A short "we need two more people" request is not like anything in
  training (dataset card).
- **Long narratives are averaged.** Text beyond 254 wordpieces is split into chunks whose vectors
  are averaged, so a deciding sentence in a long narrative counts for less than it would on its
  own.
- **Annotators were students, not practitioners.** The labels reflect the written guidelines and
  the annotators' reading, and may differ from what an experienced improvement lead would choose
  (dataset card).
- **English only, and no input check inside the model.** It returns five probabilities for any
  string, including text in another language or text that is not about a work problem.

## Compute, speed and cost

### Laptop measurement

Measured by `python tasks.py phase3-deploy` on the deployed artifact, loaded the way the app loads
it (deploy measurement). This is a laptop, not the hosting service.

| Measure | Value |
|---|---|
| Hardware | 13th Gen Intel Core i7-13620H, Windows 11, CPU only, 4 torch threads |
| Median time per prediction (one narrative) | 67.3 ms |
| 90th percentile | 101.7 ms |
| Fastest / slowest | 11.6 ms / 129.4 ms |
| Model load (one-time, at start-up) | 5.3 s |
| Peak memory (working set) | 578 MB (162 MB before the model loaded) |
| Encoder on disk | 87.3 MB (86.7 MB of it the weights file) |
| Head (`model.json`) | 56,994 bytes |

The timings are 100 single-narrative predictions (the 20 test narratives, 5 times each, after 3
warm-up calls). Load time may include a network check against the Hugging Face hub (Step 1 memo).
The Step 1 memo's figures for C2 (62.3 ms, 764 MB) were measured on the 40-item candidate in a
process that also fitted the head; the figures above are for the shipped artifact.

### Deployment

The app runs on Google Cloud Run (service `dmaic-planner`, us-central1, 1 CPU, 2 GiB, 0 to 2
instances): https://dmaic-planner-466247443045.us-central1.run.app

- **Time per prediction on Cloud Run** (measured 2026-11-26): median 59 ms of server time over
  6 warm calls (the first took 128 ms); about 580 ms round trip from a laptop through
  `gradio_client`.
- **Starting a new instance** took about 50 s from start to ready, from the Cloud Run logs of the
  revision's first start, which includes pulling the 2.5 GB image.

### Cost and environmental impact

- **$0 per prediction in API fees.** The model calls no paid API and needs no network at
  prediction time once the encoder is cached. Hosting costs are those of the server it runs on.
- **CPU only.** No GPU was used for training or prediction. Training is a logistic-regression fit
  on 65 vectors (60 narratives and 5 definitions); the encoder is used as published, not trained.
- Energy use and emissions were not measured.

## Citation

```bibtex
@misc{dmaic_planner_route_model_2026,
  title        = {{DMAIC Planner} route model c2-all60-2026-11-26},
  author       = {Dunne, Jerad and Jain, Reshu and Sarcona, Shaun and Moore, Bradley and Taylor, Turrell},
  year         = {2026},
  howpublished = {ARI 410/510, University of Michigan-Flint},
  url          = {https://github.com/jeraddunne/dmaic-planner},
  note         = {Weights licensed CC BY-SA 4.0. Builds on Hina Kramer's dmaic\_minilm\_v1.}
}
```

Please also cite the dataset (see the [dataset card](dataset_card.md#citation-information)) and
the sentence encoder's method:

```bibtex
@inproceedings{reimers-2019-sentence-bert,
  title     = {Sentence-{BERT}: Sentence Embeddings using Siamese {BERT}-Networks},
  author    = {Reimers, Nils and Gurevych, Iryna},
  booktitle = {Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing},
  year      = {2019},
  publisher = {Association for Computational Linguistics},
  url       = {https://arxiv.org/abs/1908.10084}
}
```

## Acknowledgments

- **Hina Kramer**, for the definitions-only MiniLM approach (`dmaic_minilm_v1`) that C1 reproduces
  and C2 builds on.
- The other competition participants, whose runs and descriptions are on the leaderboard in the
  [dataset card](dataset_card.md#leaderboard).
- The nine annotators: team members Reshu Jain, Shaun Sarcona, Bradley Moore and Turrell Taylor,
  and five ARI 410/510 classmates credited by ID (`ext01` to `ext05`).
- Open-source tools: sentence-transformers and the `all-MiniLM-L6-v2` encoder (Apache 2.0),
  PyTorch, and scikit-learn.
