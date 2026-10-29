"""Single-command, restartable, train-only improvement loop.

  evaluate parent on train -> diagnose failures -> propose a catalogue entry -> evaluate candidate on the SAME train queries
  -> apply the declared acceptance rule -> append to the experiment log -> repeat.

State lives entirely in the append-only log (experiment_log.jsonl) and the per-iteration folders, so re-running the same command
after an interruption continues where it stopped. Nothing here can reach the test split: evaluate() is called with
purpose="development" and the guard raises for anything else."""
import csv
import json
import platform
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..common.config import PipelineConfig, config_hash, dump_config, load_config
from ..common.logging import get_logger
from ..data.loader import load_store
from ..data.queries import load_queries
from ..evaluation.evaluator import evaluate, headline, save_run
from ..evaluation.guard import git_commit
from ..pipeline import Pipeline
from .acceptance import decide
from .proposer import label_counts, load_catalogue, propose

log = get_logger()
SPLIT, PURPOSE = "train", "development"


def _flat(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        out.update(_flat(v, key + ".") if isinstance(v, dict) else {key: v})
    return out


def config_diff(before: PipelineConfig, after: PipelineConfig) -> dict:
    a, b = _flat(before.model_dump(mode="json")), _flat(after.model_dump(mode="json"))
    return {k: [a.get(k), b.get(k)] for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k) and k not in ("name", "description")}


def _run(cfg: PipelineConfig, store, queries):
    pipe = Pipeline(cfg, store)
    res = evaluate(pipe, SPLIT, PURPOSE, queries=queries)
    return pipe, res


def _recalls(res: dict, pk: int) -> list[float]:
    return [r["metrics"]["ranking"][str(pk)]["recall"] for r in sorted(res["records"], key=lambda r: r["query_id"]) if r["answerable"]]


def _read_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _append(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_loop(root: Path, baseline_config: Path, catalogue_path: Path, max_iterations: int = 20, command: str = "",
             store=None, queries=None) -> dict:
    exp = root / "03_experiments"
    log_path, iter_dir = exp / "experiment_log.jsonl", exp / "iterations"
    store = store or load_store()
    queries = queries or load_queries(SPLIT)  # the loop never loads anything else
    if any(q.split != SPLIT for q in queries):
        raise ValueError("the improvement loop only accepts train queries")
    n_un = sum(1 for q in queries if not q.answerable)
    catalogue = load_catalogue(catalogue_path)
    entries = _read_log(log_path)

    # ---- iteration 0: baseline (re-evaluated, and checked against the committed baseline run for determinism) ----
    base_cfg = load_config(baseline_config)
    if not entries:
        t0 = time.perf_counter()
        pipe, res = _run(base_cfg, store, queries)
        d0 = iter_dir / "00-baseline"
        save_run(res, d0, command, overwrite=True)
        committed = exp / "baseline" / "train_metrics.json"
        if committed.exists():
            ref = json.loads(committed.read_text(encoding="utf-8"))
            same = all(abs(ref["retrieval_ranking_view"][k]["recall"] - res["metrics"]["retrieval_ranking_view"][k]["recall"]) < 1e-12
                       for k in ref["retrieval_ranking_view"]) and ref["threshold"] == res["metrics"]["threshold"]
            if not same:
                raise RuntimeError("baseline re-evaluation does not reproduce the committed baseline run; refusing to continue")
            log.info("baseline reproduced exactly from the committed run")
        entry = {"iteration": 0, "id": "baseline", "experiment_id": pipe.experiment_id, "parent_experiment_id": None,
                 "proposer": "human", "hypothesis": "Simplest reasonable pipeline; reference for all comparisons.",
                 "why_tried": "required baseline", "config_path": str((d0 / "resolved_config.yaml").relative_to(root)),
                 "config_hash": pipe.config_hash, "diff": {}, "split": SPLIT, "purpose": PURPOSE, "command": command,
                 "metrics": headline(res["metrics"]), "decision": "baseline", "decision_reason": "reference configuration",
                 "delta_primary": 0.0, "bootstrap": None, "guardrails": None,
                 "failure_labels": dict(label_counts(res["records"])), "runtime_s": round(time.perf_counter() - t0, 3),
                 "git_commit": git_commit(), "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "python": platform.python_version()}
        _append(log_path, entry)
        entries = [entry]

    # ---- restore state from the log ----
    accepted = [e for e in entries if e["decision"] in ("baseline", "accepted")]
    parent_entry = accepted[-1]
    parent_cfg = load_config(root / parent_entry["config_path"]) if parent_entry["iteration"] else base_cfg
    tried_ids = {e["id"] for e in entries}
    tried_hashes = {e["config_hash"] for e in entries}
    pk = base_cfg.evaluation.primary_k
    parent_pipe, parent_res = _run(parent_cfg, store, queries)
    if parent_pipe.config_hash != parent_entry["config_hash"]:
        raise RuntimeError("parent configuration hash differs from the log; the log or configs were edited")
    log.info("parent: %s  R@%d=%.4f", parent_pipe.experiment_id, pk, headline(parent_res["metrics"])[f"R@{pk}"])

    # ---- iterate ----
    while len(entries) - 1 < max_iterations:
        it = len(entries)
        counts = label_counts(parent_res["records"])
        prop = propose(catalogue, counts, parent_cfg, tried_ids, tried_hashes, it - 1)
        if prop is None:
            log.info("catalogue exhausted after %d iterations", it - 1)
            break
        entry_def, cand_cfg, why = prop
        t0 = time.perf_counter()
        pipe, res = _run(cand_cfg, store, queries)
        d = iter_dir / f"{it:02d}-{entry_def['id']}"
        if d.exists():  # leftover of an interrupted iteration that never reached the log
            shutil.rmtree(d)
        save_run(res, d, command)
        dump_config(cand_cfg, d / "config.yaml")
        ph, ch = headline(parent_res["metrics"]), headline(res["metrics"])
        verdict = decide(ph, ch, _recalls(parent_res, pk), _recalls(res, pk), pk, n_un)
        entry = {"iteration": it, "id": entry_def["id"], "experiment_id": pipe.experiment_id,
                 "parent_experiment_id": parent_pipe.experiment_id, "proposer": f"rule:catalogue/{entry_def['id']}",
                 "hypothesis": " ".join(entry_def["hypothesis"].split()), "why_tried": why,
                 "config_path": str((d / "config.yaml").relative_to(root)), "config_hash": pipe.config_hash,
                 "diff": config_diff(parent_cfg, cand_cfg), "split": SPLIT, "purpose": PURPOSE, "command": command,
                 "metrics": ch, "decision": verdict["decision"], "decision_reason": verdict["reason"],
                 "delta_primary": verdict["delta_primary"], "bootstrap": verdict["bootstrap"], "guardrails": verdict["guardrails"],
                 "failure_labels": dict(label_counts(res["records"])), "runtime_s": round(time.perf_counter() - t0, 3),
                 "git_commit": git_commit(), "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "python": platform.python_version()}
        (d / "decision.json").write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _append(log_path, entry)
        entries.append(entry)
        tried_ids.add(entry_def["id"])
        tried_hashes.add(pipe.config_hash)
        log.info("iter %d %-16s R@%d %.4f -> %.4f  %s", it, entry_def["id"], pk, ph[f"R@{pk}"], ch[f"R@{pk}"], verdict["decision"].upper())
        if verdict["decision"] == "accepted":
            parent_cfg, parent_pipe, parent_res = cand_cfg, pipe, res

    return write_outputs(root, entries, base_cfg, store, queries, command)


def write_outputs(root: Path, entries: list[dict], base_cfg: PipelineConfig, store, queries, command: str) -> dict:
    exp, res_dir = root / "03_experiments", root / "06_results"
    (exp / "configs").mkdir(parents=True, exist_ok=True)
    res_dir.mkdir(parents=True, exist_ok=True)
    accepted = [e for e in entries if e["decision"] in ("baseline", "accepted")]
    best = accepted[-1]
    best_cfg = load_config(root / best["config_path"]) if best["iteration"] else base_cfg
    # final configuration (unresolved: threshold calibrated on train) + frozen resolved twin used by search/web/test
    pipe, res = _run(best_cfg, store, queries)
    final = best_cfg.model_copy(update={"name": "final"})
    dump_config(final, exp / "configs" / "final.yaml")
    dump_config(res["resolved_config"].model_copy(update={"name": "final"}), exp / "configs" / "final_resolved.yaml")

    pk = base_cfg.evaluation.primary_k
    ks = base_cfg.evaluation.ks
    cols = (["iteration", "id", "experiment_id", "parent_experiment_id", "proposer", "decision"] + [f"R@{k}" for k in ks]
            + [f"P@{k}" for k in ks] + ["CAR", "FAR", "AUROC", "p95_ms", "build_s", "delta_primary", "p_gain", "runtime_s"])
    with (res_dir / "improvement_history.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for e in entries:
            m, b = e["metrics"], e["bootstrap"] or {}
            w.writerow([e["iteration"], e["id"], e["experiment_id"], e["parent_experiment_id"], e["proposer"], e["decision"]]
                       + [m[f"R@{k}"] for k in ks] + [m[f"P@{k}"] for k in ks]
                       + [m["CAR"], m["FAR"], m["AUROC"], m["p95_ms"], m["build_s"], e["delta_primary"], b.get("p_gain", ""), e["runtime_s"]])

    base_h, best_h = entries[0]["metrics"], best["metrics"]
    comparison = {"split": "train", "note": "TRAIN metrics only. The held-out test split has not been evaluated.",
                  "primary_metric": f"character recall@{pk} (ranking view)", "n_answerable": base_h["n_answerable"],
                  "n_unanswerable": base_h["n_unanswerable"], "baseline": {"experiment_id": entries[0]["experiment_id"], **base_h},
                  "best_train": {"experiment_id": best["experiment_id"], "iteration": best["iteration"], **best_h},
                  "delta": {k: best_h[k] - base_h[k] for k in best_h if isinstance(best_h[k], (int, float)) and k in base_h},
                  "n_iterations_beyond_baseline": len(entries) - 1,
                  "decisions": {d: sum(1 for e in entries[1:] if e["decision"] == d) for d in ("accepted", "rejected", "inconclusive")},
                  "accepted_sequence": [e["id"] for e in entries[1:] if e["decision"] == "accepted"]}
    (res_dir / "train_comparison.json").write_text(json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    L = ["# Experiment summary (train only)", "",
         f"{len(entries) - 1} iterations beyond the baseline. Primary metric: character recall@{pk} on {base_h['n_answerable']} train "
         f"answerable queries (ranking view). Acceptance rule: `03_experiments/optimization_objective.md`. Held-out test: **not evaluated**.", "",
         f"| # | experiment | proposer | R@{pk} | dR@{pk} | P(gain) | P@{pk} | R@1 | correct-abst. | decision |", "|---|---|---|---|---|---|---|---|---|---|"]
    for e in entries:
        m, b = e["metrics"], e["bootstrap"] or {}
        L.append(f"| {e['iteration']} | `{e['id']}` | {e['proposer']} | {m[f'R@{pk}']:.4f} | {e['delta_primary']:+.4f} | "
                 f"{b.get('p_gain', float('nan')):.3f} | {m[f'P@{pk}']:.4f} | {m['R@1']:.4f} | {m['CAR']:.3f} | **{e['decision']}** |")
    L += ["", "## What each iteration tried", ""]
    for e in entries[1:]:
        ch = ", ".join(f"`{k}`: {v[0]} -> {v[1]}" for k, v in e["diff"].items())
        L += [f"### {e['iteration']}. {e['id']} - {e['decision']}", f"- hypothesis: {e['hypothesis']}", f"- why now: {e['why_tried']}",
              f"- change: {ch}", f"- result: R@{pk} {entries[0]['metrics'][f'R@{pk}']:.4f} (baseline) | this run {e['metrics'][f'R@{pk}']:.4f} "
              f"| delta vs parent {e['delta_primary']:+.4f}; runtime {e['runtime_s']}s", f"- decision: {e['decision_reason']}", ""]
    L += [f"## Selected configuration (best on train)", "", f"`{best['experiment_id']}` (iteration {best['iteration']}); accepted sequence: "
          f"{', '.join(comparison['accepted_sequence']) or '(none)'}. Saved as `03_experiments/configs/final.yaml` "
          "(+ `final_resolved.yaml` with the frozen abstention threshold).", ""]
    (exp / "experiment_summary.md").write_text("\n".join(L), encoding="utf-8")
    return comparison
