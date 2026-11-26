# Phase 3, Steps 0 and 1: leaderboard and model choice

> **Public copy.** This document comes from the project's private course repository, which
> holds the full project history and is available to the ARI 410/510 instructor on request.
> Commands such as `python tasks.py ...`, issue and pull-request numbers, and files that are
> not in this repository refer to that private repository.

DMAIC Planner, ARI 410/510 Group project, Phase 3 ("From Leaderboard to Usable System").
Phase 3 is due Tue Dec 8, 1:30 PM EST (Canvas). Written 2026-11-26.

This memo holds aggregate numbers only (scores, per-class F1, counts). Per-item results
and gold labels stay in the private course repository.

Reproduce every number here, in the private course repository, with:

```
python tasks.py phase3-models   # C1 and C2: chosen on train CV, scored once on test, measured
python tasks.py leaderboard     # every run re-scored, checked against Kaggle, mistakes analysis
```

## Summary

- **Recommended: C2**, MiniLM sentence embeddings + class-balanced logistic regression on
  the 40 training labels, with the five route definitions added as extra training points
  and blended with the definitions-only scores. Full-test macro-F1 0.22020, the best of any
  run that works on a CPU at no cost. 62 ms per prediction on a laptop CPU, an 87 MB model,
  and a 764 MB peak working set.
- **Strongest alternative: gpt-5.5 zero-shot** (our Phase 2a LLM baseline). Highest
  full-test score (0.31909), but it needs a key to the U-M AI gateway, we did not log
  its cost or per-prediction latency, and its gap over C2 is within test-set noise
  (paired bootstrap p = 0.200).
- Nothing separates clearly on 20 test items. A single seeded random guess (0.26333) beat
  every participant run, and the 95% intervals of the top runs overlap widely (gpt-5.5
  0.11-0.50, C2 0.08-0.34, the best participant run 0.08-0.27).
- Decided 2026-11-26: deploy C2, refit on all 60 items (see Decisions).

## Step 0: the leaderboard

Every run re-scored on the full test set (20 items, public and private halves together)
with macro-F1 over the five labels, the competition metric (`src/dmaic_planner/leaderboard.py`).
Participant files are the host download from Kaggle on 2026-11-26. Approaches are as described
on each participant's Phase 2b form.

| # | Participant | Run ID | Approach | Full macro-F1 | 95% CI | Public | Private | Accuracy |
|---|---|---|---|---|---|---|---|---|
| 1 | Host (Phase 2a LLM baseline) | llm_gpt_5_5 | gpt-5.5 zero-shot, guidelines prompt, U-M gateway, temperature 1.0 | 0.31909 | 0.11-0.50 | 0.21333 | 0.38095 | 0.35000 |
| 2 | Host (Phase 2a) | random | Uniform random label, one seeded draw | 0.26333 | 0.06-0.43 | 0.30000 | 0.16667 | 0.25000 |
| 3 | Host (Phase 3 candidate) | C2 | MiniLM + logistic regression + definitions (this memo) | 0.22020 | 0.08-0.34 | 0.23333 | 0.19429 | 0.30000 |
| 4 | Host (Phase 2a LLM run) | llm_gpt_6_astra | gpt-6-astra zero-shot, same prompt and settings | 0.20303 | 0.06-0.33 | 0.06667 | 0.29333 | 0.25000 |
| 5 | Hina Kramer | dmaic_minilm_v1 | MiniLM embedding of the narrative vs. the five route definitions, nearest definition; no training labels | 0.18667 | 0.08-0.27 | 0.20000 | 0.16667 | 0.30000 |
| 6 | Host (Phase 3 candidate) | C1 | Our reproduction of Hina Kramer's run | 0.17714 | 0.06-0.26 | 0.20000 | 0.11429 | 0.25000 |
| 7 | Belhassen Khefacha | run1 | BERT [CLS] embeddings + Lab 3 MLP (hidden 64, 23 epochs) | 0.17167 | 0.02-0.30 | 0.18000 | 0.13000 | 0.20000 |
| 8 | Belhassen Khefacha | run2 (selected on Kaggle) | all-mpnet-base-v2 embeddings + Lab 3 MLP with class weights (hidden 256, 8 epochs) | 0.16457 | 0.03-0.29 | 0.28000 | 0.05714 | 0.20000 |
| 9 | Aymen Masmoudi | run1 | MiniLM embeddings + MLP (32 units, alpha 0.1), chosen by leave-one-out CV | 0.15043 | 0.03-0.27 | 0.19429 | 0.06667 | 0.20000 |
| 10 | Host (Phase 2a) | majority | Always the most common training label | 0.09231 | 0.04-0.13 | 0.09231 | 0.09231 | 0.30000 |
| 11 | Abdulhakim YM Abayu | run1 | Linear SVM (C=1) on word + character TF-IDF plus route keyword cues | 0.08970 | 0.00-0.17 | 0.05714 | 0.10000 | 0.15000 |
| 12 | ShaunWS (no form response) | none | No form response | 0.08333 | 0.02-0.13 | 0.09231 | 0.07273 | 0.25000 |
| 13 | Host (Phase 2a) | tfidf_svm | TF-IDF (1-2 grams) + class-balanced linear SVM | 0.08333 | 0.00-0.16 | 0.12000 | 0.06667 | 0.15000 |
| 14 | Abdulhakim YM Abayu | not in form | Second submission, not described in the form | 0.02857 | 0.00-0.07 | 0.00000 | 0.05714 | 0.05000 |

The 95% interval is a 2,000-draw bootstrap over the 20 test items (`baselines.bootstrap_ci`).
Ranks follow full macro-F1, then accuracy (rows 12 and 13 tie on macro-F1).

**The scorer is Kaggle's.** For all 7 participant files, the re-scored public and private
scores match Kaggle's own scores export (joined on SubmissionId) to 1e-6. The four
participants who wrote a public score on the form also match it to 0.001. The five host
files match the private leaderboard page (which cuts to five decimals). No mismatches.

Notes on the participant rows (facts from the Kaggle export and the forms):

- Belhassen Khefacha: run1 (58451301) matches his form. run2 (58451852) was submitted and is
  his selected entry, although his form left run2's public score blank.
- Abdulhakim YM Abayu (form name "abdulhakim Abayu", team field "na"): run1 (58847443)
  matches the form. 58848065 is a second submission the form does not describe.
- ShaunWS (Kaggle user shaunws): one submission (57959591) on 2026-11-03, before the Phase 2b
  window, with no form response. Its predictions are not all DMAIC (18 DMAIC, 1 JUST_DO_IT,
  1 NOT_CPI). Its public score equals the majority baseline's (0.09231); its private score
  (0.07273) does not.
- Hina Kramer (58283948) and Aymen Masmoudi (58313799): one submission each, matching their forms.

## Step 1: the candidates

| | What it is | Uses the 40 labels? |
|---|---|---|
| C1 | Hina Kramer's "MiniLM definitions only", reproduced: all-MiniLM-L6-v2 embeds the narrative and the five route definitions; the most similar definition wins. | No (only to set the confidence temperature) |
| C2 | Ours: the same embeddings, class-balanced logistic regression on the 40 training narratives plus the five definition vectors as extra labeled points (weight 5), blended 75/25 with C1's probabilities. | Yes |
| C3 | gpt-5.5 zero-shot, the existing Phase 2a predictions (no new API calls). | No |

Route definitions: the "What it means" column of the Kaggle Overview table, word for word
(the same text is `ROUTE_DEFINITIONS` in `src/dmaic_planner/schema.py`).
Long narratives are split into chunks of up to 254 wordpieces and averaged by token count,
as Hina Kramer's form describes. Encoder: `sentence-transformers/all-MiniLM-L6-v2`, hub
revision 1110a243, frozen.

**How the choices were made.** Everything was chosen by cross-validation on the 40 training
items only: stratified 5-fold, repeated with seeds 42, 123 and 2026. The single DMADV training
item is in the training part of every fold (as the participants did), so it is never scored
in CV and CV macro-F1 is 0.8 times the mean F1 of the other four labels. C2's grid was 48
configurations: C in {0.1, 1, 10, 100}, definition weight in {0, 1, 5}, blend in {0, 0.25,
0.5, 0.75}. Best: C = 0.1, definition weight 5, blend 0.25 (CV macro-F1 0.2840, accuracy
0.3846; C1 on the same folds: 0.2467, 0.3590). C1's temperature (0.2) was picked by log loss
on the 40 training items. Each candidate was then scored on the 20 test items once.

**Did C1 reproduce Hina Kramer's run?** Close, not exact. Her public score was 0.20000; C1's
public score is 0.20000 (match). On the 40 training items C1 scores 0.2436 against her
reported development score of 0.2447. C1's test predictions are identical to her submitted
file on 17 of 20 items, so its full-test score (0.17714) differs from her file's (0.18667).
The leaderboard uses her actual file. We tried other definition wordings (with the label name
in front, the label in words, either half of the definition) and token-level chunking; none
matched her file better than 17 of 20, so C1 uses the table text as published.

## Comparison: score and practical criteria

Latencies are measured on the laptop, not on Cloud Run: a 13th Gen Intel Core i7-13620H,
Windows 11, torch 2.15.0 CPU build with 4 threads. Each number is the median of 100 warm,
single-narrative predictions (the 20 test narratives, 5 times each, after 3 warm-up calls),
each in a fresh process (`phase3_models.measure`).

| Candidate | Full macro-F1 (95% CI) | Public / Private | Median latency per prediction | p90 | Model on disk | Peak RAM | Cost per prediction | Runs on CPU | Fits Cloud Run 2 GB |
|---|---|---|---|---|---|---|---|---|---|
| **C2 (recommended)** | 0.22020 (0.08-0.34) | 0.23333 / 0.19429 | 62.3 ms | 99.8 ms | 87.3 MB model + 31 KB head | 764 MB | $0 (local) | y | y: 764 MB peak on the laptop, which includes fitting the head in the same process |
| C1 | 0.17714 (0.06-0.26) | 0.20000 / 0.11429 | 61.0 ms | 95.9 ms | 87.3 MB model + 15 KB | 580 MB | $0 (local) | y | y: 580 MB peak on the laptop |
| C3 gpt-5.5 | 0.31909 (0.11-0.50) | 0.21333 / 0.38095 | not measured | not measured | remote | remote | not measured | n/a (remote API) | y as a thin API client, but it needs the gateway key as a secret |
| Reference: gpt-6-astra | 0.20303 (0.06-0.33) | 0.06667 / 0.29333 | not measured | not measured | remote | remote | not measured | n/a | as C3 |
| Reference: tfidf_svm | 0.08333 (0.00-0.16) | 0.12000 / 0.06667 | 1.1 ms | 1.4 ms | 590 KB (pickled fitted pipeline) | 168 MB | $0 | y | y |
| Reference: random | 0.26333 (0.06-0.43) | 0.30000 / 0.16667 | n/a | n/a | none | n/a | $0 | y | y |
| Reference: majority | 0.09231 (0.04-0.13) | 0.09231 / 0.09231 | n/a | n/a | none | n/a | $0 | y | y |

Per-class F1 on the full test set:

| Candidate | JUST_DO_IT | KAIZEN_EVENT | DMAIC | DMADV | NOT_CPI |
|---|---|---|---|---|---|
| C2 | 0.000 | 0.222 | 0.545 | 0.000 | 0.333 |
| C1 | 0.000 | 0.000 | 0.600 | 0.000 | 0.286 |
| gpt-5.5 | 0.400 | 0.250 | 0.545 | 0.400 | 0.000 |

What the practical columns rest on:

- Model size: the files of the MiniLM hub snapshot (86.7 MB of it is `model.safetensors`).
  Head size: the pickled logistic regression, definition vectors and temperature.
- Peak RAM: the peak working set of the measuring process on Windows. A Linux container will
  differ; not measured. Cloud Run's file system is held in memory, so a model downloaded at
  start-up adds about 87 MB to the container's memory; baking it into the image avoids that.
- Model load took 4.8 to 5.7 s in the measuring processes. That may include a network check
  against the Hugging Face hub (the run printed the hub's unauthenticated-request warning).
  It is a cold-start cost, not part of the per-prediction latency.
- gpt-5.5 latency and cost: not measured. The LLM run log (`RUN_LOG.md`) records the model, date,
  temperature and prompt but no timings, token counts or prices, and the gateway's billing
  is not in the repository. The only timing trace is the reply files' write times from the
  2026-10-27 run: 19 to 51 s apart over 5 gaps, each one request of 10 narratives plus the
  full guidelines prompt (about 19 KB). That is not a per-prediction latency.
- Uncertainty: paired bootstrap on the full test set (`leaderboard.paired`, 5,000 resamples,
  one-sided). gpt-5.5 over C2: gap 0.0989, p = 0.200. C2 over C1: gap 0.0431, p = 0.216.
  C2 over Hina Kramer's run: gap 0.0335, p = 0.227. Random over C2: gap 0.0431, p = 0.310.
  None is below 0.05. The expected macro-F1 of random guessing on this test set is 0.18
  (`baselines.json`, 2,000 draws); the seeded draw on the leaderboard was a
  lucky one.

## Recommendation: C2

1. It is the best run that can power a real system on the hosting we have. Among runs
   that work on a CPU for no cost, it has the highest full-test macro-F1 (0.22020, against
   0.18667 for the best participant run and 0.17714 for C1), and it was chosen on train CV
   alone (best of 48 configurations, CV macro-F1 0.2840 against C1's 0.2467).
2. It is fast and small enough for Cloud Run on a CPU: about 62 ms per prediction on the
   laptop, an 87 MB public encoder plus a 31 KB head, and a peak working set well under 2 GB.
3. It needs no API key, no paid calls and no network at prediction time, and it gives the
   same answer every time. gpt-5.5 ran at temperature 1.0, so its labels can change between
   calls.
4. It returns a probability for every route, which the app needs for its confidence display.
5. It builds on a classmate's idea: the definitions-only approach is Hina Kramer's, and the
   model card and user guide must credit her by name.

**Strongest alternative: gpt-5.5 zero-shot.** It scored best on the full test set (0.31909)
and is the only model run with a non-zero DMADV F1 (0.400). Against it: the gap over C2 is not
distinguishable from test-set noise (p = 0.200), its NOT_CPI F1 is 0.000 on this test set,
its latency and cost were never measured, and serving it publicly means putting a U-M gateway
key behind a public link.

What C2 does not do well (for the user guide's Limitations): on the test set it never
predicts DMADV and predicts JUST_DO_IT once (F1 0.000 for both), and its probabilities are
flat. Its top probability on the 20 test narratives ranges from 0.206 to 0.279 (uniform would
be 0.200), because the chosen regularisation (C = 0.1) is strong. See
`docs/mistake_patterns.md` for where all the models fail.

## Decisions (2026-11-26)

1. **Decided: deploy C2.** It is the best free option that runs on a CPU. gpt-5.5 stays in the
   comparison as the more accurate but paid option: it needs a secret key to the U-M gateway,
   and we did not log its cost or latency.
2. **Decided: refit on all 60 labeled items.** The deployed model (`models/phase3/c2/`,
   version `c2-all60-2026-11-26`) was trained on train + test (3 DMADV examples instead of 1)
   with the hyperparameters chosen on train CV. The test score reported here is still the one
   from the 40-item fit; the deployed model's own estimate is 60-item cross-validation (see
   the model card).
3. **Decided: honest percentages plus a plain tier.** The probabilities are shown as
   computed. The data did not support more than one tier (the top1-top2 margin does not
   predict correctness, AUC 0.48), so every prediction carries "Low confidence: compare the
   top two routes" with its cross-validated accuracy.

## Credit

- Hina Kramer: the definitions-only MiniLM approach that C1 reproduces and C2 builds on
  (her code link is in her Phase 2b form response, shared with the course).
- The other participants' runs are on the leaderboard with their own descriptions; their code
  links are in the Phase 2b form responses, kept in the private course repository.
- Encoder: `sentence-transformers/all-MiniLM-L6-v2` (Apache 2.0) through the
  sentence-transformers library.
