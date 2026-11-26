# DMAIC Planner route model `c2-all60-2026-11-26`

Reads a short process-problem narrative and gives a probability for each of five routes: JUST_DO_IT, KAIZEN_EVENT, DMAIC, DMADV, NOT_CPI. Candidate C2 from Phase 3, refit on all 60 labeled narratives of the public DMAIC Planner dataset.

## Files

- `model.json`: everything the model learned or was given: logistic-regression weights, blend weight and temperature, the five route definitions word for word, confidence-tier thresholds, the base encoder's id and pinned revision, training-data hashes and scores. Plain JSON, no pickle.

## How it works

1. `sentence-transformers/all-MiniLM-L6-v2` (revision `1110a243fd`, frozen) embeds the narrative; long narratives are split into chunks of up to 254 wordpieces and averaged.
2. A class-balanced logistic regression on that vector gives one probability per route. It was trained on the 60 narratives plus the five route definitions as extra examples (weight 5), C = 0.1.
3. Those probabilities are blended 0.75 / 0.25 with a softmax of the narrative's similarity to each route definition (temperature 0.3).

## Use

```python
from dmaic_planner.phase3_models import load_deployed
model = load_deployed("models/phase3/c2")
proba = model.predict_proba(["Claims sit in the review queue for days and nobody knows why."])[0]
print(model.version, max(proba, key=proba.get), model.confidence(proba)["text"])
```

## Scores

- Test set (20 items), from the same recipe fit on the 40 training items before this refit: macro-F1 0.22020 (95% bootstrap 0.08-0.34), accuracy 0.30. This model has since seen those 20 items.
- Cross-validation estimate on all 60 (not a held-out test score): macro-F1 0.2576, accuracy 0.3450, top-2 accuracy 0.6257 (57 items x 3 seeds; the 3 DMADV items stay in training, so macro-F1 is capped at 0.8).

## Reading the confidence

The probabilities are honest but flat: with five routes, 0.20 each is a pure guess. Confidence tiers come from the gap between the top two probabilities, set on out-of-fold predictions (the gap's AUC for telling a right top answer from a wrong one: 0.48; 0.50 is no signal):

| Tier | Gap (top 1 minus top 2) | Out-of-fold accuracy | n |
|---|---|---|---|
| Low confidence: compare the top two routes | any | 0.35 | 171 |

Rule: one tier: out-of-fold accuracy does not rise with the margin, so the margin is not shown as confidence (a boundary is kept only if OOF accuracy rises by 0.1 or more across it). The right route was in the top two in 63% of out-of-fold predictions.

## Limits

- 60 training narratives; one route (DMADV) has only 3.
- In the cross-validation it predicted DMADV 4 times and JUST_DO_IT 26 times out of 171 (DMAIC 46, KAIZEN_EVENT 30, NOT_CPI 65).
- English only; trained on complaints, audit findings, help-desk tickets, workplace questions and patient-safety cases.
- A suggestion for a person to review, not a decision.

## Credit and license

- The definitions-similarity idea comes from Hina Kramer's ARI 410/510 Kaggle submission (dmaic_minilm_v1).
- Base encoder: sentence-transformers/all-MiniLM-L6-v2, Apache 2.0.
- Weights in `model.json` are derived from the DMAIC Planner dataset (CC BY-SA 4.0) and are released under CC BY-SA 4.0.
