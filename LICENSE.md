# Licensing

This repository holds code and data under two licenses. Which one applies depends on the files.

| What | License | Full text |
|---|---|---|
| **Code and documentation:** `app/`, `src/`, `tests/`, `rules/`, `deploy/`, `docs/`, `Dockerfile`, `README.md` | **MIT** | [`LICENSE-CODE.txt`](LICENSE-CODE.txt) |
| **The dataset:** `data/train.csv` and `data/test.csv` (text and labels) | **CC BY-SA 4.0** | [`LICENSE-DATA.txt`](LICENSE-DATA.txt) |
| **The model weights:** `models/phase3/c2/model.json`, derived from the dataset | **CC BY-SA 4.0** | [`LICENSE-DATA.txt`](LICENSE-DATA.txt) |

The base sentence encoder, `sentence-transformers/all-MiniLM-L6-v2`, is licensed Apache 2.0 by its
authors. It is not stored in this repository; it downloads from Hugging Face at the revision pinned
in `model.json`.

## The dataset: CC BY-SA 4.0

Creative Commons Attribution-ShareAlike 4.0 International,
<https://creativecommons.org/licenses/by-sa/4.0/>. You may share and adapt the dataset, including
commercially, if you give attribution and license what you make from it under CC BY-SA 4.0 too.

**Why share-alike.** The Stack Exchange items are licensed CC BY-SA (version 2.5, 3.0 or 4.0, by the
question's posting date), and CC BY-SA requires a collection that includes them to be shared alike.
CC BY-SA 4.0 can carry the more permissive sources (CC BY 4.0, CC0 and U.S. Government works)
along with them, so it is the one license for the whole dataset. Each item's own terms are in its
`license` column:

| Items | Source | Terms of the text in `text` |
|---:|---|---|
| 15 | Stack Exchange | CC BY-SA 2.5 (1); CC BY-SA 3.0 (8); CC BY-SA 4.0 (6) |
| 11 | AHRQ PSNet WebM&M | CC BY-SA 4.0 (team-written paraphrase; the source text is not included) |
| 10 | GAO Reports | Public domain (U.S. Government work) |
| 9 | CFPB Consumer Complaint Database | Public domain (CC0 / U.S. Government work) |
| 7 | Mendeley Help Desk Tickets | CC BY 4.0 |
| 6 | PA Patient Safety Authority | CC BY-SA 4.0 (team-written paraphrase; the source text is not included) |
| 2 | NIST Baldrige Application Summaries | CC BY-SA 4.0 (team-written paraphrase; the source text is not included) |

**Paraphrases.** For 19 items (`storage_mode` = `paraphrase`) the source does not allow its text to be
redistributed. Their `text` is a summary written by the project team, with `source_url` pointing to
the original. The summaries are the team's own writing and are released under CC BY-SA 4.0; the
source documents remain with their owners. Keep the `storage_mode` marking if you redistribute, and
do not replace a paraphrase with the source text.

**Attribution.** For the dataset as a whole:

> DMAIC Planner dataset. Dunne, J., Jain, R., Sarcona, S., Moore, B., & Taylor, T. (2026).
> ARI 410/510, University of Michigan-Flint. Licensed CC BY-SA 4.0.

Each item's credit line is in its `attribution` column. For the Stack Exchange items it names the
author's public username and links to their profile, as Stack Exchange's attribution rules ask;
keep that column with the items if you redistribute them. Annotators are credited by anonymous ID
(`ext01` to `ext05`), not by name. More detail: [the dataset card](docs/dataset_card.md#licensing-information).

## The code and documentation: MIT

Everything that is not data or model weights is MIT licensed: reuse it freely, including in
proprietary work, as long as the copyright notice travels with it. The dataset's share-alike terms
do not reach the code.
