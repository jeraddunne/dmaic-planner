"""
Phase 3, Step 1: the candidate models, chosen on train only, scored once on test.

    python tasks.py phase3-models        # CV choice, one test score, practical measures
    python tasks.py leaderboard          # then: puts C1 and C2 on the leaderboard

  C1  MiniLM definitions only. A reproduction of Hina Kramer's run dmaic_minilm_v1
      (Phase 2b form): embed the narrative and the five route definitions with
      all-MiniLM-L6-v2 and predict the most similar route. No training labels.
      The definitions are the Kaggle Overview table's "What it means" column
      (kaggle/page/overview.md, generated from schema.ROUTE_DEFINITIONS), word for word.
      Long narratives are split into chunks of up to 254 wordpieces, each chunk is
      embedded, and the chunk vectors are averaged weighted by token count, as her
      form describes. Probabilities: softmax of the five cosine similarities with
      one temperature, chosen by log loss on the 40 training items.
  C2  MiniLM + class-balanced logistic regression on the 40 labels, with the five
      definition vectors added as extra labeled points (weight w) and the result
      blended with C1's probabilities (share a). C, w and a are picked by
      cross-validation on train.

Cross-validation: stratified 5-fold, repeated with seeds 42, 123 and 2026. The one
DMADV training item cannot be held out and still leave DMADV in training, so it is
in the training part of every fold (as the participants did) and never scored in
CV. Macro-F1 is computed over all five labels on each repetition's pooled held-out
predictions, so the DMADV term is always 0 and CV macro-F1 is 0.8 x the mean F1 of
the other four labels; the ranking of configurations is the same either way.

Test discipline: every choice is made on train. Each candidate is then scored on
the 20 test items once.

Writes (gitignored, under kaggle/private/phase3/):
  predictions/<candidate>.csv, <candidate>_proba.csv, candidates.json
  phase3_models.json, phase3_models.md

The deployed model (Jerad's choice: C2, refit on all 60 labeled items):

    python tasks.py phase3-deploy        # -> models/phase3/c2/model.json + README.md

refits C2 with the hyperparameters above on the public release
(kaggle/private/phase3/release_staging/train.csv + test.csv), writes the weights as
plain JSON (no pickle), sets confidence tiers from out-of-fold predictions on the
60 items, and measures latency. The app loads it with load_deployed().
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import pickle
import platform
import statistics
import subprocess
import sys
import time
import warnings
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

# Only the schema at import time: loading the deployed model (load_deployed) needs nothing
# else from the project. The training and evaluation code below imports what it uses
# (baselines, leaderboard) inside the functions that use it.
from dmaic_planner.schema import METHODOLOGIES, ROUTE_DEFINITIONS as _DEFINITIONS

ROOT = Path(__file__).resolve().parents[2]
KAGGLE = ROOT / "kaggle"
OUT = KAGGLE / "private" / "phase3"
LABELS = np.array(METHODOLOGIES)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"  # the hub commit these results used
MAX_WORDPIECES = 254  # the model reads 256 tokens; two go to [CLS] and [SEP]
TORCH_THREADS = 4

# The Kaggle Overview table, word for word: what participants saw as the routes.
ROUTE_DEFINITIONS = {m: _DEFINITIONS[m] for m in METHODOLOGIES}

CV_SEEDS = (42, 123, 2026)
CV_FOLDS = 5
TEMPERATURES = (0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0)
C2_GRID = {"C": (0.1, 1.0, 10.0, 100.0), "def_weight": (0.0, 1.0, 5.0), "blend": (0.0, 0.25, 0.5, 0.75)}

# What Hina Kramer reported for dmaic_minilm_v1 on the Phase 2b form.
HINA_DEV_MACRO_F1 = 0.2447
HINA_PUBLIC = 0.20000


# --------------------------------------------------------------------------- #
# the encoder
# --------------------------------------------------------------------------- #

class MiniLMEncoder:
    """Frozen all-MiniLM-L6-v2. Long texts: 254-wordpiece chunks, embedded one by one,
    averaged weighted by each chunk's token count, then normalised to length 1."""

    def __init__(self, model_name: str = MODEL_NAME, revision: str | None = MODEL_REVISION,
                 threads: int = TORCH_THREADS):
        try:
            import torch
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError("pip install sentence-transformers (see requirements.txt, Phase 3)") from e
        torch.set_num_threads(threads)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.model = SentenceTransformer(model_name, revision=revision, device="cpu")
        self.tokenizer = self.model.tokenizer

    def chunks(self, text: str) -> list[list[int]]:
        ids = self.tokenizer(text, add_special_tokens=False, verbose=False)["input_ids"]
        return [ids[i:i + MAX_WORDPIECES] for i in range(0, len(ids), MAX_WORDPIECES)] or [[]]

    def encode(self, texts) -> np.ndarray:
        texts = list(texts)
        pieces, owner, weight = [], [], []
        for k, t in enumerate(texts):
            for c in self.chunks(t):
                pieces.append(self.tokenizer.decode(c))
                owner.append(k)
                weight.append(max(len(c), 1))
        emb = np.asarray(self.model.encode(pieces, normalize_embeddings=True, batch_size=32,
                                           show_progress_bar=False))
        out = np.zeros((len(texts), emb.shape[1]))
        np.add.at(out, np.array(owner), emb * np.array(weight, float)[:, None])
        return out / np.linalg.norm(out, axis=1, keepdims=True)


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def log_loss(y, proba: np.ndarray) -> float:
    """Mean negative log probability of the true label; proba columns in METHODOLOGIES
    order. (sklearn's log_loss assumes sorted label order, which this is not.)"""
    idx = np.array([METHODOLOGIES.index(v) for v in y])
    return float(-np.mean(np.log(np.clip(proba[np.arange(len(idx)), idx], 1e-12, 1))))


def choose_temperature(sims: np.ndarray, y) -> float:
    """The temperature with the lowest log loss on these items."""
    losses = [log_loss(y, softmax(sims / t)) for t in TEMPERATURES]
    return TEMPERATURES[int(np.argmin(losses))]


# --------------------------------------------------------------------------- #
# the candidates
# --------------------------------------------------------------------------- #

class DefinitionsOnly:
    """C1: nearest route definition. Nothing is learned from labels except the
    temperature, which changes the probabilities and never the predicted label."""

    name = "c1_minilm_definitions"

    def __init__(self, encoder: MiniLMEncoder, temperature: float = 0.05,
                 definitions: dict[str, str] = ROUTE_DEFINITIONS):
        self.encoder, self.temperature = encoder, temperature
        self.def_emb = encoder.encode([definitions[m] for m in METHODOLOGIES])

    def similarities(self, emb: np.ndarray) -> np.ndarray:
        return emb @ self.def_emb.T

    def proba_from_embeddings(self, emb: np.ndarray) -> np.ndarray:
        return softmax(self.similarities(emb) / self.temperature)

    def predict(self, texts) -> tuple[list[str], np.ndarray]:
        """Labels, and per-class probabilities in METHODOLOGIES order (rows sum to 1)."""
        p = self.proba_from_embeddings(self.encoder.encode(texts))
        return LABELS[p.argmax(1)].tolist(), p


class DefinitionsLogReg:
    """C2: logistic regression on MiniLM vectors of the training narratives plus the
    five definition vectors (weight def_weight), blended with C1's probabilities."""

    name = "c2_minilm_logreg_defs"

    def __init__(self, encoder: MiniLMEncoder | None, C: float = 1.0, def_weight: float = 1.0,
                 blend: float = 0.25, def_emb: np.ndarray | None = None):
        self.encoder, self.C, self.def_weight, self.blend = encoder, C, def_weight, blend
        if def_emb is None:
            def_emb = encoder.encode([ROUTE_DEFINITIONS[m] for m in METHODOLOGIES])
        self.def_emb = def_emb

    def fit_embeddings(self, emb: np.ndarray, y) -> "DefinitionsLogReg":
        y = np.asarray(y)
        X, Y, w = emb, y, np.ones(len(y))
        if self.def_weight > 0:
            X = np.vstack([emb, self.def_emb])
            Y = np.concatenate([y, LABELS])
            w = np.concatenate([w, np.full(len(LABELS), self.def_weight)])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.clf_ = LogisticRegression(C=self.C, class_weight="balanced", max_iter=5000).fit(X, Y, sample_weight=w)
        self.order_ = [list(self.clf_.classes_).index(m) for m in METHODOLOGIES]
        self.temperature_ = choose_temperature(emb @ self.def_emb.T, y) if self.blend > 0 else None
        return self

    def fit(self, texts, y) -> "DefinitionsLogReg":
        return self.fit_embeddings(self.encoder.encode(texts), y)

    def proba_from_embeddings(self, emb: np.ndarray) -> np.ndarray:
        p = self.clf_.predict_proba(emb)[:, self.order_]
        if self.blend > 0:
            p = (1 - self.blend) * p + self.blend * softmax((emb @ self.def_emb.T) / self.temperature_)
        return p

    def predict(self, texts) -> tuple[list[str], np.ndarray]:
        p = self.proba_from_embeddings(self.encoder.encode(texts))
        return LABELS[p.argmax(1)].tolist(), p


# --------------------------------------------------------------------------- #
# cross-validation on train
# --------------------------------------------------------------------------- #

def cv_splits(y, seeds=CV_SEEDS, k: int = CV_FOLDS, always_train_below: int | None = None):
    """(seed, train_idx, held_out_idx). A class with fewer than always_train_below
    items (default k: DMADV, with 1 item in train and 3 in all 60) stays in training
    in every fold and is never held out. always_train_below=0 holds out every class."""
    y = np.asarray(y)
    below = k if always_train_below is None else always_train_below
    counts = {c: int((y == c).sum()) for c in set(y)}
    always = np.array([i for i, c in enumerate(y) if counts[c] < below], dtype=int)
    rest = np.array([i for i, c in enumerate(y) if counts[c] >= below], dtype=int)
    for seed in seeds:
        skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=seed)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # "least populated class has only 3 members"
            folds = list(skf.split(rest, y[rest]))
        for tr, te in folds:
            yield seed, np.concatenate([rest[tr], always]), rest[te]


def cv_score(fit_predict, emb: np.ndarray, y) -> dict:
    """fit_predict(train_emb, train_y, held_out_emb) -> probabilities. Pooled held-out
    predictions per repetition, then the mean over repetitions."""
    from dmaic_planner.baselines import macro_f1
    y = np.asarray(y)
    per_seed: dict[int, dict] = {}
    for seed, tr, te in cv_splits(y):
        p = fit_predict(emb[tr], y[tr], emb[te])
        d = per_seed.setdefault(seed, {"idx": [], "proba": []})
        d["idx"].extend(te.tolist())
        d["proba"].append(p)
    f1s, accs, lls = [], [], []
    for d in per_seed.values():
        yt, p = y[d["idx"]], np.vstack(d["proba"])
        pred = LABELS[p.argmax(1)]
        f1s.append(macro_f1(yt, pred))
        accs.append(float(np.mean(pred == yt)))
        lls.append(log_loss(yt, p))
    return {"macro_f1": float(np.mean(f1s)), "macro_f1_per_seed": [round(x, 4) for x in f1s],
            "accuracy": float(np.mean(accs)), "log_loss": float(np.mean(lls)), "n_held_out": len(d["idx"])}


def grid() -> list[dict]:
    return [{"C": c, "def_weight": w, "blend": a} for c in C2_GRID["C"]
            for w in C2_GRID["def_weight"] for a in C2_GRID["blend"]]


def c2_rank_key(cfg: dict, cv: dict) -> tuple:
    """Best CV macro-F1, then accuracy, then the simpler model (less blending, fewer
    definition points, C nearer 1)."""
    return (-round(cv["macro_f1"], 4), -round(cv["accuracy"], 4), cfg["blend"], cfg["def_weight"],
            abs(np.log10(cfg["C"])))


# --------------------------------------------------------------------------- #
# practical measures (run in a fresh process each, one at a time)
# --------------------------------------------------------------------------- #

def peak_ram_mb() -> float | None:
    """Peak working set (Windows) or max RSS (POSIX) of this process, in MB."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        k32 = ctypes.WinDLL("kernel32")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi")
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        if psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return pmc.PeakWorkingSetSize / 2**20
        return None
    try:
        import resource
        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return r / 2**20 if sys.platform == "darwin" else r / 1024
    except (ImportError, OSError):
        return None


def cpu_name() -> str:
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
                return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
        except OSError:
            pass
    return platform.processor() or platform.machine()


def model_disk_mb() -> dict:
    from huggingface_hub import snapshot_download

    path = Path(snapshot_download(MODEL_NAME, revision=MODEL_REVISION, local_files_only=True))
    files = [p for p in path.rglob("*") if p.is_file()]
    return {"snapshot_mb": sum(p.stat().st_size for p in files) / 2**20,
            "weights_mb": sum(p.stat().st_size for p in files if p.suffix == ".safetensors") / 2**20}


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def measure(which: str, config: dict, kaggle: Path = KAGGLE, reps: int = 5) -> dict:
    """Latency of one prediction for one narrative, warm, on this machine's CPU.
    Uses the test narratives' text only (never a label) as realistic inputs."""
    train = read_rows(kaggle / "public" / "train.csv")
    texts = [r["text"] for r in read_rows(kaggle / "public" / "test.csv")]
    ram_start = peak_ram_mb()
    t0 = time.perf_counter()
    if which == "tfidf_svm":
        from dmaic_planner.baselines import frame, models

        est = models()["tfidf_svm"][2].fit(frame(r["text"] for r in train), [r["label"] for r in train])
        predict = lambda t: est.predict(frame([t]))  # noqa: E731
        load_s, head_bytes, disk = None, len(pickle.dumps(est)), {"snapshot_mb": None, "weights_mb": None}
    elif which == "deployed":
        # The artifact as the app loads it: model.json + the cached encoder. Head size
        # is the JSON file's size.
        deployed = load_deployed(config.get("path", DEPLOY_DIR))
        load_s = time.perf_counter() - t0
        predict = lambda t: deployed.predict_proba([t])  # noqa: E731
        head_bytes = (resolve_deploy_dir(config.get("path", DEPLOY_DIR)) / "model.json").stat().st_size
        disk = model_disk_mb()
    else:
        enc = MiniLMEncoder()
        load_s = time.perf_counter() - t0
        if which == "c1":
            model = DefinitionsOnly(enc, temperature=config["temperature"])
            head_bytes = model.def_emb.nbytes
        else:
            model = DefinitionsLogReg(enc, C=config["C"], def_weight=config["def_weight"], blend=config["blend"])
            model.fit([r["text"] for r in train], [r["label"] for r in train])
            head_bytes = len(pickle.dumps((model.clf_, model.def_emb, model.temperature_)))
        predict = lambda t: model.predict([t])  # noqa: E731
        disk = model_disk_mb()
    for t in texts[:3]:
        predict(t)  # warm-up
    times = []
    for t in texts:
        for _ in range(reps):
            s = time.perf_counter()
            predict(t)
            times.append((time.perf_counter() - s) * 1000)
    q = statistics.quantiles(times, n=10)
    return {"which": which, "cpu": cpu_name(), "torch_threads": TORCH_THREADS if which != "tfidf_svm" else None,
            "n_timed": len(times), "median_ms": statistics.median(times), "p90_ms": q[-1],
            "min_ms": min(times), "max_ms": max(times), "load_s": load_s,
            "peak_ram_mb": peak_ram_mb(), "ram_before_model_mb": ram_start,
            "model_snapshot_mb": disk["snapshot_mb"], "model_weights_mb": disk["weights_mb"],
            "head_kb": head_bytes / 1024, "python": platform.python_version(), "os": platform.platform()}


def measure_in_subprocess(which: str, config: dict) -> dict:
    """One fresh process per candidate, so peak RAM is that candidate's alone."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    out = subprocess.run([sys.executable, "-m", "dmaic_planner.phase3_models", "measure", which,
                          json.dumps(config)], capture_output=True, text=True, cwd=ROOT, env=env, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


# --------------------------------------------------------------------------- #
# the run
# --------------------------------------------------------------------------- #

def write_predictions(folder: Path, name: str, ids: list[str], labels: list[str], proba: np.ndarray) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f"{name}.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "label"])
        w.writerows(zip(ids, labels))
    with (folder / f"{name}_proba.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", *METHODOLOGIES])
        w.writerows([i, *(f"{v:.6f}" for v in row)] for i, row in zip(ids, proba))


def hina_file(kaggle: Path) -> Path | None:
    """Hina Kramer's submitted file, found through the submissions manifest."""
    manifest = kaggle / "submissions" / "manifest.csv"
    if not manifest.exists():
        return None
    for r in read_rows(manifest):
        if r.get("run_id") == "dmaic_minilm_v1" and r.get("file"):
            p = kaggle / "submissions" / r["file"]
            return p if p.exists() else None
    return None


def run(kaggle: Path = KAGGLE, out: Path = OUT, do_measure: bool = True) -> dict:
    from dmaic_planner.baselines import macro_f1
    from dmaic_planner.leaderboard import load_solution, score_predictions

    train = read_rows(kaggle / "public" / "train.csv")
    test = read_rows(kaggle / "public" / "test.csv")
    y = np.array([r["label"] for r in train])
    ids = [r["id"] for r in test]

    enc = MiniLMEncoder()
    E_tr = enc.encode(r["text"] for r in train)  # frozen encoder: no label touches these
    E_te = enc.encode(r["text"] for r in test)
    c1 = DefinitionsOnly(enc)
    D = c1.def_emb

    # ---- C1: temperature on train (probabilities only), CV on the same folds as C2
    c1.temperature = choose_temperature(c1.similarities(E_tr), y)
    c1_train_pred = LABELS[c1.similarities(E_tr).argmax(1)]
    c1_cv = cv_score(lambda Xtr, ytr, Xte: softmax((Xte @ D.T) / choose_temperature(Xtr @ D.T, ytr)), E_tr, y)

    # ---- C2: grid search on train CV
    def c2_fit_predict(cfg):
        return lambda Xtr, ytr, Xte: DefinitionsLogReg(None, def_emb=D, **cfg).fit_embeddings(Xtr, ytr) \
            .proba_from_embeddings(Xte)
    table = [(cfg, cv_score(c2_fit_predict(cfg), E_tr, y)) for cfg in grid()]
    table.sort(key=lambda t: c2_rank_key(*t))
    best_cfg, best_cv = table[0]

    # ---- scored once on test, after every choice above
    c2 = DefinitionsLogReg(None, def_emb=D, **best_cfg).fit_embeddings(E_tr, y)
    p1, p2 = c1.proba_from_embeddings(E_te), c2.proba_from_embeddings(E_te)
    pred1, pred2 = LABELS[p1.argmax(1)].tolist(), LABELS[p2.argmax(1)].tolist()
    sol = load_solution(kaggle)
    s1 = score_predictions(dict(zip(ids, pred1)), sol)
    s2 = score_predictions(dict(zip(ids, pred2)), sol)

    pred_dir = out / "predictions"
    write_predictions(pred_dir, DefinitionsOnly.name, ids, pred1, p1)
    write_predictions(pred_dir, DefinitionsLogReg.name, ids, pred2, p2)
    cfg_txt = f"C={best_cfg['C']:g}, definition weight {best_cfg['def_weight']:g}, blend {best_cfg['blend']:g}"
    candidates = {
        DefinitionsOnly.name: {"description": "C1: MiniLM definitions only (reproduction of Hina Kramer's "
                                              "dmaic_minilm_v1); nearest route definition, no training labels",
                               "credit": "Hina Kramer"},
        DefinitionsLogReg.name: {"description": f"C2: MiniLM + class-balanced logistic regression on the 40 "
                                                 f"labels plus definition points, blended with C1 ({cfg_txt}); "
                                                 f"chosen on train CV",
                                 "credit": "Builds on Hina Kramer's definitions idea"},
    }
    (pred_dir / "candidates.json").write_text(json.dumps(candidates, indent=2), encoding="utf-8", newline="\n")

    # ---- the reproduction check against Hina's submitted file (predictions vs predictions)
    hf = hina_file(kaggle)
    agree = None
    if hf is not None:
        hina = {r["id"]: r["label"] for r in read_rows(hf)}
        agree = sum(hina.get(i) == p for i, p in zip(ids, pred1))
    repro = {"train_macro_f1": macro_f1(y, c1_train_pred), "hina_dev_macro_f1": HINA_DEV_MACRO_F1,
             "test_public_macro_f1": s1["public"]["macro_f1"], "hina_public": HINA_PUBLIC,
             "test_predictions_identical_to_hina_file": agree, "n_test": len(ids),
             "public_matches": abs(s1["public"]["macro_f1"] - HINA_PUBLIC) <= 0.001}

    def pack(s):
        return {"full": s["full"], "public": s["public"], "private": s["private"], "per_class": s["per_class"],
                "ci": s["ci"], "predicted_counts": dict(s["predicted"])}

    result = {
        "model": MODEL_NAME, "revision": MODEL_REVISION, "max_wordpieces": MAX_WORDPIECES,
        "cv": {"seeds": CV_SEEDS, "folds": CV_FOLDS, "dmadv": "in training every fold, never held out"},
        "c1": {"temperature": c1.temperature, "cv": c1_cv, "test": pack(s1), "reproduction": repro,
               "train_predicted_counts": {m: int((c1_train_pred == m).sum()) for m in METHODOLOGIES}},
        "c2": {"config": best_cfg, "temperature": c2.temperature_, "cv": best_cv, "test": pack(s2),
               "grid": [{**cfg, **{k: round(v, 4) if isinstance(v, float) else v for k, v in cv.items()}}
                        for cfg, cv in table]},
        "versions": versions(),
    }
    if do_measure:
        del enc, c1, c2  # free the model before the measuring processes load their own
        result["measures"] = {
            "c1": measure_in_subprocess("c1", {"temperature": result["c1"]["temperature"]}),
            "c2": measure_in_subprocess("c2", best_cfg),
            "tfidf_svm": measure_in_subprocess("tfidf_svm", {}),
        }
    (out / "phase3_models.json").write_text(json.dumps(result, indent=2), encoding="utf-8", newline="\n")
    (out / "phase3_models.md").write_text(report(result), encoding="utf-8", newline="\n")
    return result


def versions() -> dict:
    import sklearn
    out = {"python": platform.python_version(), "numpy": np.__version__, "scikit-learn": sklearn.__version__}
    for name in ("torch", "sentence_transformers", "transformers"):
        try:
            out[name] = __import__(name).__version__
        except ImportError:
            out[name] = None
    return out


def report(r: dict) -> str:
    f = lambda x: f"{x:.4f}"  # noqa: E731
    c1, c2, rp = r["c1"], r["c2"], r["c1"]["reproduction"]
    lines = ["# Phase 3 candidates C1 and C2", "",
             "**Private: test scores per class. Keep off GitHub.** Built by `python tasks.py phase3-models`.", "",
             f"Encoder: {r['model']} at revision {r['revision'][:10]}, chunks of up to {r['max_wordpieces']} "
             f"wordpieces, token-count weighted. CV: stratified {r['cv']['folds']}-fold x seeds "
             f"{', '.join(map(str, r['cv']['seeds']))}; DMADV {r['cv']['dmadv']}.", "",
             "## C1 reproduction of Hina Kramer's dmaic_minilm_v1", "",
             f"- Train macro-F1 (all 40, no training): {f(rp['train_macro_f1'])}; her form: {rp['hina_dev_macro_f1']}",
             f"- Test predictions identical to her submitted file: {rp['test_predictions_identical_to_hina_file']} "
             f"of {rp['n_test']}",
             f"- Public macro-F1: {f(rp['test_public_macro_f1'])}; her form and Kaggle: {rp['hina_public']:.5f}; "
             f"match: {'yes' if rp['public_matches'] else 'no'}",
             f"- Temperature (log loss on train): {c1['temperature']}", "",
             "## C2 grid (train CV only; top 10 of " + str(len(c2["grid"])) + ")", "",
             "| C | definition weight | blend | CV macro-F1 | per seed | CV accuracy | CV log loss |",
             "|---|---|---|---|---|---|---|"]
    for g in c2["grid"][:10]:
        lines.append(f"| {g['C']:g} | {g['def_weight']:g} | {g['blend']:g} | {f(g['macro_f1'])} | "
                     f"{', '.join(map(str, g['macro_f1_per_seed']))} | {f(g['accuracy'])} | {f(g['log_loss'])} |")
    lines += ["", f"C1 on the same folds: CV macro-F1 {f(c1['cv']['macro_f1'])}, accuracy {f(c1['cv']['accuracy'])}, "
                  f"log loss {f(c1['cv']['log_loss'])}.", "",
              f"Chosen C2: {c2['config']} (blend temperature {c2['temperature']}).", "",
              "## Test (scored once, after the choices)", "",
              "| Candidate | Full macro-F1 | 95% CI | Public | Private | Accuracy | " + " | ".join(METHODOLOGIES) + " |",
              "|---|---|---|---|---|---|" + "---|" * len(METHODOLOGIES)]
    for name, c in (("C1", c1), ("C2", c2)):
        t = c["test"]
        lines.append(f"| {name} | {f(t['full']['macro_f1'])} | {t['ci'][0]:.2f}-{t['ci'][1]:.2f} | "
                     f"{f(t['public']['macro_f1'])} | {f(t['private']['macro_f1'])} | {f(t['full']['accuracy'])} | "
                     + " | ".join(f"{t['per_class'][m]:.3f}" for m in METHODOLOGIES) + " |")
    if "measures" in r:
        lines += ["", "## Practical measures (measured on laptop, not Cloud Run)", "",
                  "| Candidate | Median ms / prediction | p90 ms | Model load s | Peak RAM MB | Model on disk MB | Head KB |",
                  "|---|---|---|---|---|---|---|"]
        for k, m in r["measures"].items():
            load = f"{m['load_s']:.1f}" if m["load_s"] is not None else "n/a"
            disk = f"{m['model_snapshot_mb']:.1f}" if m["model_snapshot_mb"] is not None else "n/a"
            lines.append(f"| {k} | {m['median_ms']:.1f} | {m['p90_ms']:.1f} | {load} | {m['peak_ram_mb']:.0f} | "
                         f"{disk} | {m['head_kb']:.1f} |")
        m = r["measures"]["c1"]
        lines += ["", f"CPU: {m['cpu']}; torch threads {TORCH_THREADS}; {m['n_timed']} timed single-narrative "
                      f"predictions (20 test narratives x 5, after 3 warm-up calls); {m['os']}."]
    lines += ["", "Versions: " + ", ".join(f"{k} {v}" for k, v in r["versions"].items())]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# the deployed model: C2 refit on all 60 labeled items
# --------------------------------------------------------------------------- #

DEPLOY_DIR = Path("models") / "phase3" / "c2"
RELEASE = OUT / "release_staging"
# Chosen on train CV in Step 1 (phase3_models.json, c2.config). Not re-tuned on 60.
DEPLOY_CONFIG = {"C": 0.1, "def_weight": 5.0, "blend": 0.25}
# Confidence tiers come from the top-1 minus top-2 margin, and a tier boundary is kept
# only if out-of-fold accuracy rises by at least TIER_STEP across it: three tiers at
# the tertiles if both steps do, else two at the median if that step does, else one
# tier for every prediction (the margin does not tell right from wrong).
TIER_STEP = 0.10
TIER_TEXT = {"leaning": "Leaning {route}", "weak_lean": "Weak lean: {route}",
             "toss_up": "Toss-up: compare the top two",
             "low": "Low confidence: compare the top two routes"}


def resolve_deploy_dir(path: str | os.PathLike = DEPLOY_DIR) -> Path:
    """A relative path is tried from the working directory, then from the repo root."""
    p = Path(path)
    return p if p.is_absolute() or p.exists() else ROOT / p


class DeployedModel:
    """C2 as shipped: model.json (logistic-regression weights, blend, temperature,
    route definitions, confidence tiers) on top of all-MiniLM-L6-v2, which loads
    from the Hugging Face cache at the pinned revision. No pickle."""

    name = "c2_deployed"

    def __init__(self, spec: dict, encoder: MiniLMEncoder):
        if spec["classes"] != METHODOLOGIES:
            raise ValueError(f"model.json classes {spec['classes']} are not {METHODOLOGIES}")
        self.spec, self.encoder = spec, encoder
        self.version: str = spec["version"]
        self.coef = np.asarray(spec["logistic_regression"]["coef"], dtype=float)
        self.intercept = np.asarray(spec["logistic_regression"]["intercept"], dtype=float)
        self.blend = float(spec["blend"]["weight"])
        self.temperature = float(spec["blend"]["temperature"])
        self.tiers = spec["confidence_tiers"]["tiers"]
        self.def_emb = encoder.encode([spec["route_definitions"][m] for m in METHODOLOGIES])
        # The same encoder must give the same definition vectors as at training time.
        drift = np.abs(self.def_emb @ self.def_emb.T - np.asarray(spec["base_model"]["definition_cosines"])).max()
        if drift > 1e-3:
            raise ValueError(f"the encoder does not reproduce the training-time definition vectors "
                             f"(largest cosine difference {drift:.4f}); check the base model revision")

    def proba_from_embeddings(self, emb: np.ndarray) -> np.ndarray:
        p_lr = softmax(emb @ self.coef.T + self.intercept)
        p_def = softmax((emb @ self.def_emb.T) / self.temperature)
        p = (1 - self.blend) * p_lr + self.blend * p_def
        return p / p.sum(axis=1, keepdims=True)

    def predict_proba(self, texts: list[str]) -> list[dict[str, float]]:
        """One {label code: probability} per text, in METHODOLOGIES order, summing to 1."""
        texts = list(texts)
        if not all(isinstance(t, str) for t in texts):
            raise TypeError("predict_proba takes a list of strings")
        if not texts:
            return []
        p = self.proba_from_embeddings(self.encoder.encode(texts))
        return [dict(zip(METHODOLOGIES, map(float, row))) for row in p]

    def predict(self, texts) -> tuple[list[str], np.ndarray]:
        """The candidates' shape: labels and a (n, 5) array. What app/predictor.py wraps."""
        texts = list(texts)
        p = self.proba_from_embeddings(self.encoder.encode(texts)) if texts else np.zeros((0, len(METHODOLOGIES)))
        return LABELS[p.argmax(1)].tolist() if texts else [], p

    def confidence(self, proba: dict[str, float]) -> dict:
        """The plain-language tier for one prediction, from the top-1 minus top-2 margin."""
        ranked = sorted(proba.items(), key=lambda kv: -kv[1])
        margin = ranked[0][1] - ranked[1][1]
        tier = next(t for t in self.tiers if margin >= t["min_margin"])
        return {"tier": tier["name"], "text": tier["text"].format(route=ranked[0][0]), "margin": margin,
                "oof_accuracy": tier["oof_accuracy"], "top": ranked[0][0], "second": ranked[1][0]}


def load_deployed(path: str | os.PathLike = DEPLOY_DIR, threads: int | None = None) -> DeployedModel:
    """Load the shipped C2 from models/phase3/c2/model.json. The encoder comes from the
    Hugging Face hub cache at the revision pinned in model.json (downloaded once if not
    cached; set HF_HUB_OFFLINE=1 to forbid that). Threads: `threads`, else the
    DMAIC_THREADS environment variable, else 4."""
    spec = json.loads((resolve_deploy_dir(path) / "model.json").read_text(encoding="utf-8"))
    if threads is None:
        threads = int(os.environ.get("DMAIC_THREADS") or TORCH_THREADS)
    base = spec["base_model"]
    encoder = MiniLMEncoder(base["id"], revision=base["revision"], threads=threads)
    if base["max_wordpieces"] != MAX_WORDPIECES:
        raise ValueError(f"model.json expects {base['max_wordpieces']}-wordpiece chunks; this code uses {MAX_WORDPIECES}")
    return DeployedModel(spec, encoder)


def sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def oof(emb: np.ndarray, y: np.ndarray, def_emb: np.ndarray, always_train_below: int | None = None) -> list[dict]:
    """Out-of-fold C2 predictions (DEPLOY_CONFIG), one record per held-out item per seed."""
    out = []
    for seed, tr, te in cv_splits(y, always_train_below=always_train_below):
        m = DefinitionsLogReg(None, def_emb=def_emb, **DEPLOY_CONFIG).fit_embeddings(emb[tr], y[tr])
        for i, p in zip(te, m.proba_from_embeddings(emb[te])):
            out.append({"seed": seed, "idx": int(i), "gold": y[i], "proba": p})
    return out


def oof_summary(records: list[dict]) -> dict:
    """Macro-F1 (five labels) and accuracy on each seed's pooled held-out predictions,
    averaged over seeds; top-2 accuracy over every held-out prediction."""
    from dmaic_planner.baselines import macro_f1
    f1s, accs = [], []
    for seed in sorted({r["seed"] for r in records}):
        rs = [r for r in records if r["seed"] == seed]
        gold = np.array([r["gold"] for r in rs])
        pred = LABELS[np.array([r["proba"].argmax() for r in rs])]
        f1s.append(macro_f1(gold, pred))
        accs.append(float(np.mean(pred == gold)))
    top2 = np.mean([r["gold"] in LABELS[np.argsort(-r["proba"])[:2]] for r in records])
    predicted = [LABELS[r["proba"].argmax()] for r in records]
    return {"macro_f1": float(np.mean(f1s)), "macro_f1_per_seed": [round(x, 4) for x in f1s],
            "accuracy": float(np.mean(accs)), "top2_accuracy": float(top2),
            "predicted_counts": {m: predicted.count(m) for m in METHODOLOGIES},
            "n_items": len({r["idx"] for r in records}), "n_predictions": len(records)}


def confidence_tiers(records: list[dict]) -> dict:
    """Thresholds on the top-1 minus top-2 margin, from out-of-fold predictions (see
    TIER_STEP for when a boundary is kept)."""
    from sklearn.metrics import roc_auc_score

    margins, right = [], []
    for r in records:
        top = np.sort(r["proba"])[::-1]
        margins.append(float(top[0] - top[1]))
        right.append(bool(LABELS[r["proba"].argmax()] == r["gold"]))
    margins, right = np.array(margins), np.array(right)

    def tier_stats(cuts: list[float]) -> list[dict]:
        bounds = [np.inf, *cuts, -np.inf]
        out = []
        for hi, lo in zip(bounds[:-1], bounds[1:]):
            sel = (margins >= lo) & (margins < hi)
            out.append({"min_margin": float(lo) if np.isfinite(lo) else 0.0, "n": int(sel.sum()),
                        "oof_accuracy": float(right[sel].mean()) if sel.any() else None})
        return out

    def rises(tiers: list[dict]) -> bool:
        accs = [t["oof_accuracy"] for t in tiers]
        return all(a is not None for a in accs) and all(a - b >= TIER_STEP for a, b in zip(accs, accs[1:]))

    three = tier_stats([float(np.quantile(margins, 2 / 3)), float(np.quantile(margins, 1 / 3))])
    two = tier_stats([float(np.median(margins))])
    if rises(three):
        tiers, names, rule = three, ["leaning", "weak_lean", "toss_up"], "three tiers at the margin tertiles"
    elif rises(two):
        tiers, names, rule = two, ["leaning", "toss_up"], "two tiers at the median margin"
    else:
        tiers, names = [{"min_margin": 0.0, "n": int(len(right)), "oof_accuracy": float(right.mean())}], ["low"]
        rule = "one tier: out-of-fold accuracy does not rise with the margin, so the margin is not shown as confidence"
    for t, n in zip(tiers, names):
        t["name"], t["text"] = n, TIER_TEXT[n]
    top2 = float(np.mean([r["gold"] in LABELS[np.argsort(-r["proba"])[:2]] for r in records]))
    return {"rule": f"{rule} (a boundary is kept only if OOF accuracy rises by {TIER_STEP:g} or more across it)",
            "margin": "top-1 probability minus top-2 probability",
            "tiers": tiers,
            "two_tier_check": two, "three_tier_check": three,
            "margin_auc_for_correct_top1": float(roc_auc_score(right, margins)) if 0 < right.sum() < len(right) else None,
            "overall_oof_accuracy": float(right.mean()), "top2_oof_accuracy": top2,
            "n_predictions": int(len(right)), "median_margin": float(np.median(margins))}


def build_deployed(release: Path = RELEASE, out_dir: Path | None = None, created: str | None = None) -> dict:
    """Refit C2 on all 60 items of the public release and write model.json + README.md."""
    import sklearn
    from datetime import date

    out_dir = out_dir or ROOT / DEPLOY_DIR
    created = created or date.today().isoformat()
    files = {name: release / name for name in ("train.csv", "test.csv")}
    rows = [r for f in files.values() for r in read_rows(f)]
    texts, y = [r["text"] for r in rows], np.array([r["label"] for r in rows])

    enc = MiniLMEncoder()
    emb = enc.encode(texts)
    def_emb = enc.encode([ROUTE_DEFINITIONS[m] for m in METHODOLOGIES])

    records = oof(emb, y, def_emb)                              # DMADV in training every fold
    records_all = oof(emb, y, def_emb, always_train_below=0)    # sensitivity: DMADV held out too
    tiers = confidence_tiers(records)
    model = DefinitionsLogReg(None, def_emb=def_emb, **DEPLOY_CONFIG).fit_embeddings(emb, y)
    coef = model.clf_.coef_[model.order_]
    intercept = model.clf_.intercept_[model.order_]

    stage_a = json.loads((OUT / "phase3_models.json").read_text(encoding="utf-8"))["c2"] \
        if (OUT / "phase3_models.json").exists() else None
    import sentence_transformers
    import torch
    import transformers
    spec = {
        "version": f"c2-all60-{created}",
        "created": created,
        "model": "C2: MiniLM sentence embeddings + class-balanced logistic regression on the labeled narratives "
                 "and the five route definitions, blended with definition similarity",
        "classes": METHODOLOGIES,
        "base_model": {"id": MODEL_NAME, "revision": MODEL_REVISION, "max_wordpieces": MAX_WORDPIECES,
                       "pooling": "the model's mean pooling, normalised; long texts in chunks of up to "
                                  f"{MAX_WORDPIECES} wordpieces, averaged by token count, normalised again",
                       "sentence_transformers_version": sentence_transformers.__version__,
                       "transformers_version": transformers.__version__, "torch_version": torch.__version__,
                       "definition_cosines": np.round(def_emb @ def_emb.T, 6).tolist()},
        "route_definitions": dict(ROUTE_DEFINITIONS),
        "logistic_regression": {"C": DEPLOY_CONFIG["C"], "class_weight": "balanced",
                                "definition_point_weight": DEPLOY_CONFIG["def_weight"],
                                "scikit_learn_version": sklearn.__version__,
                                "coef": coef.tolist(), "intercept": intercept.tolist()},
        "blend": {"weight": DEPLOY_CONFIG["blend"], "temperature": model.temperature_,
                  "formula": "p = (1 - weight) * softmax(x @ coef.T + intercept) "
                             "+ weight * softmax((x @ definitions.T) / temperature)",
                  "temperature_procedure": "refit on the 60 items: the value in "
                                           f"{list(TEMPERATURES)} with the lowest log loss of the "
                                           "definition-similarity softmax on the training items"},
        "hyperparameters": {**DEPLOY_CONFIG, "chosen_by": "stratified 5-fold CV on the 40 training items, "
                                                          "seeds 42/123/2026 (Phase 3 Step 1); not re-tuned on 60"},
        "training_data": {
            "description": "DMAIC Planner dataset, public release: train.csv (40) + test.csv (20), the 60 "
                           "labeled narratives of the ARI 410/510 competition, CC BY-SA 4.0",
            "rows": len(rows), "label_counts": {m: int((y == m).sum()) for m in METHODOLOGIES},
            "sha256": {name: sha256(f) for name, f in files.items()}},
        "evaluation": {
            "test_from_40_item_fit": None if stage_a is None else {
                "note": "C2 fit on the 40 training items only and scored once on the 20 test items, before this "
                        "refit. This deployed model has seen those 20 items, so it has no held-out score.",
                "full_macro_f1": stage_a["test"]["full"]["macro_f1"], "ci95": stage_a["test"]["ci"],
                "public_macro_f1": stage_a["test"]["public"]["macro_f1"],
                "private_macro_f1": stage_a["test"]["private"]["macro_f1"],
                "accuracy": stage_a["test"]["full"]["accuracy"], "per_class_f1": stage_a["test"]["per_class"]},
            "cv_estimate_60": {
                "note": "Cross-validation estimate, not a held-out test score: out-of-fold predictions on the 60 "
                        "items, stratified 5-fold x seeds 42/123/2026, same hyperparameters. The 3 DMADV items "
                        "stay in training in every fold and are never scored, so the DMADV F1 term is 0 and "
                        "macro-F1 is capped at 0.8.",
                **oof_summary(records)},
            "cv_estimate_60_dmadv_held_out": {
                "note": "Sensitivity check: the same CV, but the 3 DMADV items are held out too (each in a "
                        "different fold, leaving 2 in training).",
                **oof_summary(records_all)},
        },
        "confidence_tiers": tiers,
        "intended_use": "Suggest which continuous-improvement route (JUST_DO_IT, KAIZEN_EVENT, DMAIC, DMADV, "
                        "NOT_CPI) fits a short English process-problem narrative, as a starting point for a person "
                        "to review. Not for decisions without human review.",
        "credit": "The definitions-similarity idea comes from Hina Kramer's ARI 410/510 Kaggle submission "
                  "(dmaic_minilm_v1).",
    }
    # The JSON weights must reproduce the fitted model exactly.
    check = DeployedModel.__new__(DeployedModel)
    check.coef, check.intercept, check.def_emb = coef, intercept, def_emb
    check.blend, check.temperature = DEPLOY_CONFIG["blend"], model.temperature_
    assert np.abs(check.proba_from_embeddings(emb) - model.proba_from_embeddings(emb)).max() < 1e-9

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "model.json").write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8", newline="\n")
    (out_dir / "README.md").write_text(deployed_readme(spec), encoding="utf-8", newline="\n")
    # Per-item out-of-fold predictions carry gold labels: private only.
    with (OUT / "deployed_oof.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["seed", "id", "gold", *METHODOLOGIES])
        w.writerows([r["seed"], rows[r["idx"]]["id"], r["gold"], *(f"{v:.6f}" for v in r["proba"])] for r in records)
    return spec


def deployed_readme(spec: dict) -> str:
    ev, tiers = spec["evaluation"], spec["confidence_tiers"]
    t40, cv = ev["test_from_40_item_fit"], ev["cv_estimate_60"]
    lines = [f"# DMAIC Planner route model `{spec['version']}`", "",
             "Reads a short process-problem narrative and gives a probability for each of five routes: "
             "JUST_DO_IT, KAIZEN_EVENT, DMAIC, DMADV, NOT_CPI. Candidate C2 from Phase 3, refit on all 60 labeled "
             "narratives of the public DMAIC Planner dataset.", "",
             "## Files", "",
             "- `model.json`: everything the model learned or was given: logistic-regression weights, blend weight "
             "and temperature, the five route definitions word for word, confidence-tier thresholds, the base "
             "encoder's id and pinned revision, training-data hashes and scores. Plain JSON, no pickle.",
             "", "## How it works", "",
             f"1. `{spec['base_model']['id']}` (revision `{spec['base_model']['revision'][:10]}`, frozen) embeds the "
             f"narrative; long narratives are split into chunks of up to {spec['base_model']['max_wordpieces']} "
             "wordpieces and averaged.",
             "2. A class-balanced logistic regression on that vector gives one probability per route. It was trained "
             "on the 60 narratives plus the five route definitions as extra examples (weight "
             f"{spec['logistic_regression']['definition_point_weight']:g}), C = {spec['logistic_regression']['C']:g}.",
             f"3. Those probabilities are blended {1 - spec['blend']['weight']:.2f} / {spec['blend']['weight']:.2f} with a "
             f"softmax of the narrative's similarity to each route definition (temperature "
             f"{spec['blend']['temperature']:g}).", "",
             "## Use", "",
             "```python",
             "from dmaic_planner.phase3_models import load_deployed",
             "model = load_deployed(\"models/phase3/c2\")",
             "proba = model.predict_proba([\"Claims sit in the review queue for days and nobody knows why.\"])[0]",
             "print(model.version, max(proba, key=proba.get), model.confidence(proba)[\"text\"])",
             "```", "",
             "## Scores", ""]
    if t40:
        lines.append(f"- Test set (20 items), from the same recipe fit on the 40 training items before this refit: "
                     f"macro-F1 {t40['full_macro_f1']:.5f} (95% bootstrap {t40['ci95'][0]:.2f}-{t40['ci95'][1]:.2f}), "
                     f"accuracy {t40['accuracy']:.2f}. This model has since seen those 20 items.")
    lines += [f"- Cross-validation estimate on all 60 (not a held-out test score): macro-F1 {cv['macro_f1']:.4f}, "
              f"accuracy {cv['accuracy']:.4f}, top-2 accuracy {cv['top2_accuracy']:.4f} "
              f"({cv['n_items']} items x 3 seeds; the 3 DMADV items stay in training, so macro-F1 is capped at 0.8).",
              "", "## Reading the confidence", "",
              "The probabilities are honest but flat: with five routes, 0.20 each is a pure guess. Confidence tiers "
              "come from the gap between the top two probabilities, set on out-of-fold predictions"
              + (f" (the gap's AUC for telling a right top answer from a wrong one: "
                 f"{tiers['margin_auc_for_correct_top1']:.2f}; 0.50 is no signal)"
                 if tiers.get("margin_auc_for_correct_top1") is not None else "") + ":", "",
              "| Tier | Gap (top 1 minus top 2) | Out-of-fold accuracy | n |", "|---|---|---|---|"]
    upper = None
    for t in tiers["tiers"]:
        gap = "any" if len(tiers["tiers"]) == 1 else (
            f"{t['min_margin']:.4f} or more" if upper is None else f"{t['min_margin']:.4f} to {upper:.4f}")
        lines.append(f"| {t['text'].format(route='<route>')} | {gap} | {t['oof_accuracy']:.2f} | {t['n']} |")
        upper = t["min_margin"]
    lines += ["", f"Rule: {tiers['rule']}. The right route was in the top two in "
                  f"{tiers['top2_oof_accuracy']:.0%} of out-of-fold predictions."]
    counts = cv["predicted_counts"]
    lines += ["", "## Limits", "",
              "- 60 training narratives; one route (DMADV) has only 3.",
              f"- In the cross-validation it predicted DMADV {counts['DMADV']} times and JUST_DO_IT "
              f"{counts['JUST_DO_IT']} times out of {cv['n_predictions']} (DMAIC {counts['DMAIC']}, KAIZEN_EVENT "
              f"{counts['KAIZEN_EVENT']}, NOT_CPI {counts['NOT_CPI']}).",
              "- English only; trained on complaints, audit findings, help-desk tickets, workplace questions and "
              "patient-safety cases.",
              "- A suggestion for a person to review, not a decision.", "",
              "## Credit and license", "",
              f"- {spec['credit']}",
              "- Base encoder: sentence-transformers/all-MiniLM-L6-v2, Apache 2.0.",
              "- Weights in `model.json` are derived from the DMAIC Planner dataset (CC BY-SA 4.0) and are released "
              "under CC BY-SA 4.0.", ""]
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "measure":
        print(json.dumps(measure(sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else {})))
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "deploy":
        spec = build_deployed()
        size = (ROOT / DEPLOY_DIR / "model.json").stat().st_size
        m = measure_in_subprocess("deployed", {})
        cv, t = spec["evaluation"]["cv_estimate_60"], spec["confidence_tiers"]
        (OUT / "deployed_measure.json").write_text(json.dumps({"model_json_bytes": size, **m}, indent=2),
                                                   encoding="utf-8", newline="\n")
        print(f"{spec['version']}: wrote {DEPLOY_DIR}/model.json ({size / 1024:.1f} KB) and README.md")
        print(f"CV estimate on 60 (not a test score): macro-F1 {cv['macro_f1']:.4f}, accuracy {cv['accuracy']:.4f}, "
              f"top-2 {cv['top2_accuracy']:.4f}, {cv['n_predictions']} held-out predictions")
        print(f"tiers ({t['rule']}): " + "; ".join(f"{x['name']} margin>={x['min_margin']:.4f} acc "
                                                   f"{x['oof_accuracy']:.3f} n={x['n']}" for x in t["tiers"]))
        print(f"latency on {m['cpu']}: median {m['median_ms']:.1f} ms, p90 {m['p90_ms']:.1f} ms; "
              f"load {m['load_s']:.1f} s; peak RAM {m['peak_ram_mb']:.0f} MB")
        return
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--no-measure", action="store_true", help="skip latency / RAM / size")
    args = ap.parse_args()
    r = run(args.kaggle, args.out, do_measure=not args.no_measure)
    rp = r["c1"]["reproduction"]
    print(f"C1 reproduction: train macro-F1 {rp['train_macro_f1']:.4f} (form {rp['hina_dev_macro_f1']}), "
          f"{rp['test_predictions_identical_to_hina_file']}/{rp['n_test']} test predictions identical to her file, "
          f"public {rp['test_public_macro_f1']:.5f} (form {rp['hina_public']:.5f})")
    print(f"C2 chosen on CV: {r['c2']['config']}  CV macro-F1 {r['c2']['cv']['macro_f1']:.4f}")
    for k in ("c1", "c2"):
        t = r[k]["test"]
        print(f"{k.upper()} test: full {t['full']['macro_f1']:.5f}  public {t['public']['macro_f1']:.5f}  "
              f"private {t['private']['macro_f1']:.5f}")
    print(f"wrote {args.out}/phase3_models.md, .json, predictions/. Next: python tasks.py leaderboard")


if __name__ == "__main__":
    main()
