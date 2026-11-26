# Where the models fail: mistake patterns on the test set

> **Public copy.** This document comes from the project's private course repository, which
> holds the full project history and is available to the ARI 410/510 instructor on request.
> Commands such as `python tasks.py ...`, issue and pull-request numbers, and files that are
> not in this repository refer to that private repository.

Phase 3, Step 1 ("Look at the mistakes"). Aggregates only: no item ids and no per-item
labels. The per-item table (`mistakes.md`) and the numbers behind this page
(`mistake_patterns.json`) stay in the private course repository, both written by
`python tasks.py leaderboard`.

**Systems counted: 10.** The 7 participant submissions downloaded from Kaggle, plus the
host's gpt-5.5, gpt-6-astra and TF-IDF + SVM runs. The majority and random baselines are left
out because a constant and a coin say nothing about how hard an item is. The Phase 3
candidates (C1, C2) are not counted, since C1 reproduces a submitted run.

## 1. Almost every test item is hard

- 18 of the 20 test items were wrong for more than half of the 10 systems.
- 4 items were wrong for all 10, 5 for 9, 4 for 8 and 5 for 7. Only two items were
  right for most systems (wrong for 4 and for 2).
- C2, the recommended model, gets 5 of the 18 hard items right; C1 gets 4.

So the question "what do the hardest items have in common" has a blunt answer: they are most
of the test set. The task is hard for every approach tried, including two frontier LLMs.

## 2. DMAIC is the default wrong answer

- Of the 158 wrong predictions the 10 systems made, 62 were DMAIC, 36 NOT_CPI,
  30 JUST_DO_IT, 24 KAIZEN_EVENT and 6 DMADV.
- DMAIC was the most common wrong answer on 9 of the 18 hard items.
- Items whose gold label is DMAIC are the easiest (wrong for 60% of systems on average,
  6 items); every other class is wrong for 84% or more of systems on average.
- JUST_DO_IT items were most often called DMAIC (22 times) or NOT_CPI (14). NOT_CPI items
  were most often called DMAIC (15) or JUST_DO_IT (12). KAIZEN_EVENT items were most often
  called DMAIC (16).

Two likely reasons, neither tested here: DMAIC is the largest class in training (12 of 40),
and most narratives describe a process that is failing, which on the surface is what DMAIC
means. The routes turn on details a model can miss: whether the cause and the fix are already
stated (JUST_DO_IT) or whether the real ask is money, staff or policy (NOT_CPI).

## 3. DMADV is the class nobody predicts

- DMADV has 1 training item and 2 test items. Those 2 test items were wrong for 95% of
  systems on average.
- 8 of the 12 model runs on the leaderboard (the 10 counted here plus C1 and C2) never
  predict DMADV at all, C2 included. Only gpt-5.5 has a non-zero DMADV F1.
- KAIZEN_EVENT is the next weakest: 3 runs never predict it, and only 5 of the 12 have a
  non-zero KAIZEN_EVENT F1 (the same count as NOT_CPI; JUST_DO_IT 6, DMAIC all 12).

Macro-F1 gives DMADV a fifth of the score, so a model that never predicts it is capped at
0.80 before it makes any other mistake.

## 4. The items annotators split on are hard, but so is everything else

- 16 of the 20 test items had a single annotator in round 1, so their disagreement is
  unknown. The other 4 were labeled by 9 annotators.
- All 4 multi-annotated items are among the hard ones. On 3 of them only 4 of 9 annotators
  (0.44) chose the label that became gold, through the tie-break; each was wrong for 9 of
  the 10 systems. On the fourth, 7 of 9 annotators (0.78) agreed, and 7 of 10 systems were
  wrong.
- By how the gold label was decided, the mean share of systems wrong is 0.90 for tie-break
  (adjudicated) items (3), 0.775 for single-annotator items (16) and 0.70 for the one
  majority item.
- The 18 hard items are 14 single-annotator, 3 tie-break and 1 majority item, the same mix
  as the test set as a whole (16, 3, 1).

The tie-break items are the hardest group, which fits the idea that the models fail where
people disagree. But the difficulty is not only disagreement: 14 hard items had one
annotator, and for those the dataset cannot tell us whether a second annotator would have
agreed with the gold label. Some of what looks like model error may be label noise.

## 5. No clear source effect

Mean share of systems wrong, by source (items in the test set in brackets):
workplace.stackexchange.com 0.93 (3), Mendeley help-desk tickets 0.90 (2), AHRQ PSNet 0.80 (4),
CFPB complaints 0.80 (2), pm.stackexchange.com 0.80 (2), GAO reports 0.73 (4),
PA Patient Safety Authority 0.63 (3).

With 2 to 4 items per source, these differences cannot be told apart from chance. The
workplace questions and help-desk threads are the hardest by a little; the patient-safety
paraphrases, written by our team, are the easiest by a little.

## What this means for the user guide (Limitations)

- Expect DMADV to be missed: the model has seen one example of it.
- Expect DMAIC as the fallback answer when a narrative describes a failing process, even if the
  cause and fix are stated or the request is really for resources.
- The test set is 20 items, 16 of them labeled by one person. Scores on it carry wide
  intervals (C2: 0.08 to 0.34), and some "mistakes" may be cases where reasonable annotators
  would disagree.
