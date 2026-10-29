"""Round 2: gate-only abstention stage (rule declared in 03_experiments/optimization_objective.md, Amendment 1; post hoc).

Same machinery as the main loop (train only, append-only log, restartable), different objective: correct abstention on the
train unanswerables at a threshold calibrated on the answerable train queries. Retrieval must not change."""
import csv
import json
import platform
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from ..common.config import PipelineConfig, _deep_merge, config_from_dict, config_hash, dump_config, load_config
from ..common.logging import get_logger
from ..data.loader import load_store
from ..data.queries import load_queries
from ..evaluation.evaluator import evaluate, headline, save_run
from ..evaluation.guard import git_commit
from ..pipeline import Pipeline
from .acceptance import paired_bootstrap
from .loop import config_diff, _append, _read_log

log = get_logger()
MIN_GAIN_QUERIES = 2
MIN_P_GAIN = 0.90
CATEGORY_TOLERANCE = 1
FAR_SLACK = 1 / 140


def _abstained_vector(res: dict) -> list[float]:
    return [1.0 if r["abstained"] else 0.0 for r in sorted(res["records"], key=lambda r: r["query_id"]) if not r["answerable"]]


def _by_category(res: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in res["records"]:
        if not r["answerable"]:
            out[r["category"]] = out.get(r["category"], 0) + int(r["abstained"])
    return out


def decide_stage(parent_h, cand_h, parent_res, cand_res, target_far) -> dict:
    n_un = cand_h["n_unanswerable"]
    pv, cv = _abstained_vector(parent_res), _abstained_vector(cand_res)
    boot = paired_bootstrap(pv, cv)
    gain = int(sum(cv) - sum(pv))
    ks = [k for k in parent_h if k.startswith("R@")] + [k for k in parent_h if k.startswith("P@")]
    r1 = all(abs(parent_h[k] - cand_h[k]) < 1e-12 for k in ks)
    pc, cc = _by_category(parent_res), _by_category(cand_res)
    r2 = all(cc[c] >= pc[c] - CATEGORY_TOLERANCE for c in pc)
    r3 = cand_h["FAR"] <= target_far + FAR_SLACK + 1e-12
    guards = {"R1_retrieval_identical": r1, "R2_no_category_loses_more_than_1": r2, "R3_false_abstention_within_budget": r3}
    if not r1:
        raise RuntimeError("a gate-only candidate changed retrieval metrics; the stage is invalid")
    if not (r2 and r3):
        d, why = "rejected", "guardrail failed: " + ", ".join(k for k, v in guards.items() if not v)
    elif gain >= MIN_GAIN_QUERIES and boot["p_gain"] >= MIN_P_GAIN:
        d, why = "accepted", f"+{gain} correct abstentions (>= {MIN_GAIN_QUERIES}) and P(gain)={boot['p_gain']:.3f} >= {MIN_P_GAIN}; guardrails pass"
    elif gain >= MIN_GAIN_QUERIES:
        d, why = "inconclusive", f"+{gain} correct abstentions but P(gain)={boot['p_gain']:.3f} < {MIN_P_GAIN}"
    else:
        d, why = "rejected", f"gain of {gain} correct abstentions is below the minimum of {MIN_GAIN_QUERIES}"
    return {"decision": d, "reason": why, "gain_queries": gain, "delta_primary": gain / n_un if n_un else 0.0, "bootstrap": boot,
            "guardrails": guards, "category_parent": pc, "category_candidate": cc}


def run_stage(root: Path, catalogue_path: Path, command: str = "", store=None, queries=None, start_config: Path | None = None) -> dict:
    exp, res_dir = root / "03_experiments", root / "06_results"
    cfg_dir, log_path = exp / "configs", exp / "experiment_log_round2.jsonl"
    store = store or load_store()
    queries = queries or load_queries("train")
    if any(q.split != "train" for q in queries):
        raise ValueError("the abstention stage only accepts train queries")
    import yaml
    catalogue = yaml.safe_load(Path(catalogue_path).read_text(encoding="utf-8"))["entries"]

    # keep the round-1 selection as its own files before final.yaml is overwritten
    for stem in ("final", "final_resolved"):
        src, dst = cfg_dir / f"{stem}.yaml", cfg_dir / f"{stem.replace('final', 'final_round1')}.yaml"
        if src.exists() and not dst.exists():
            shutil.copy(src, dst)
    start = load_config(start_config or cfg_dir / "final_round1.yaml")
    start = start.model_copy(update={"abstention": start.abstention.model_copy(update={"threshold": None})})
    target_far = start.abstention.target_far

    def run(cfg: PipelineConfig):
        pipe = Pipeline(cfg, store)
        return pipe, evaluate(pipe, "train", "development", queries=queries)

    entries = _read_log(log_path)
    accepted = [e for e in entries if e["decision"] in ("baseline", "accepted")]
    parent_cfg = load_config(root / accepted[-1]["config_path"]) if accepted and accepted[-1]["iteration"] else start
    parent_pipe, parent_res = run(parent_cfg)
    if not entries:
        ph = headline(parent_res["metrics"])
        d0 = exp / "iterations" / "r2-00-round1-final"
        save_run(parent_res, d0, command, overwrite=True)
        e0 = {"iteration": 0, "id": "round1-final", "experiment_id": parent_pipe.experiment_id, "parent_experiment_id": None,
              "proposer": "human", "hypothesis": "Round-1 selection; reference for round 2.", "why_tried": "reference",
              "config_path": str((d0 / "train_resolved_config.yaml").relative_to(root)), "config_hash": parent_pipe.config_hash, "diff": {},
              "split": "train", "purpose": "development", "command": command, "metrics": ph, "decision": "baseline",
              "decision_reason": "reference", "delta_primary": 0.0, "bootstrap": None, "guardrails": None,
              "category_correct_abstentions": _by_category(parent_res), "runtime_s": 0.0, "git_commit": git_commit(),
              "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "python": platform.python_version()}
        _append(log_path, e0)
        entries = [e0]
    tried_ids = {e["id"] for e in entries}
    tried_hashes = {e["config_hash"] for e in entries}

    for entry_def in catalogue:
        if entry_def["id"] in tried_ids:
            continue
        it = len(entries)
        raw = _deep_merge(parent_cfg.model_dump(mode="json"), entry_def["overrides"])
        raw["name"], raw["description"] = f"r2-{it:02d}-{entry_def['id']}", " ".join(entry_def["hypothesis"].split())
        cand_cfg = config_from_dict(raw)
        if config_hash(cand_cfg) in tried_hashes:
            continue
        t0 = time.perf_counter()
        pipe, res = run(cand_cfg)
        d = exp / "iterations" / f"r2-{it:02d}-{entry_def['id']}"
        if d.exists():
            shutil.rmtree(d)
        save_run(res, d, command)
        dump_config(cand_cfg, d / "config.yaml")
        ph, ch = headline(parent_res["metrics"]), headline(res["metrics"])
        v = decide_stage(ph, ch, parent_res, res, target_far)
        e = {"iteration": it, "id": entry_def["id"], "experiment_id": pipe.experiment_id, "parent_experiment_id": parent_pipe.experiment_id,
             "proposer": f"rule:catalogue_round2/{entry_def['id']}", "hypothesis": " ".join(entry_def["hypothesis"].split()),
             "why_tried": "round-2 catalogue order (post hoc abstention stage)", "config_path": str((d / "config.yaml").relative_to(root)),
             "config_hash": pipe.config_hash, "diff": config_diff(parent_cfg, cand_cfg), "split": "train", "purpose": "development",
             "command": command, "metrics": ch, "decision": v["decision"], "decision_reason": v["reason"], "delta_primary": v["delta_primary"],
             "gain_queries": v["gain_queries"], "bootstrap": v["bootstrap"], "guardrails": v["guardrails"],
             "category_correct_abstentions": v["category_candidate"], "runtime_s": round(time.perf_counter() - t0, 3),
             "git_commit": git_commit(), "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "python": platform.python_version()}
        (d / "decision.json").write_text(json.dumps(e, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _append(log_path, e)
        entries.append(e)
        tried_ids.add(entry_def["id"])
        tried_hashes.add(pipe.config_hash)
        log.info("r2 %d %-22s CAR %.3f -> %.3f (%+d) AUROC %.3f %s", it, entry_def["id"], ph["CAR"], ch["CAR"], v["gain_queries"], ch["AUROC"], v["decision"].upper())
        if v["decision"] == "accepted":
            parent_cfg, parent_pipe, parent_res = cand_cfg, pipe, res

    # ---- outputs ----
    best = [e for e in entries if e["decision"] in ("baseline", "accepted")][-1]
    best_cfg = load_config(root / best["config_path"]) if best["iteration"] else start
    pipe, res = run(best_cfg)
    seq = [e["id"] for e in entries[1:] if e["decision"] == "accepted"]
    desc = ("Round-1 selection (routing + paragraph chunks + light stemming) plus round-2 gate: "
            + (", ".join(seq) if seq else "unchanged (no round-2 candidate accepted)"))
    dump_config(best_cfg.model_copy(update={"name": "final", "description": desc}), cfg_dir / "final.yaml")
    dump_config(res["resolved_config"].model_copy(update={"name": "final", "description": desc}), cfg_dir / "final_resolved.yaml")
    with (res_dir / "improvement_history_round2.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["iteration", "id", "experiment_id", "decision", "CAR", "FAR", "AUROC", "R@4", "P@4", "gain_queries", "p_gain", "threshold"])
        for e in entries:
            m, b = e["metrics"], e["bootstrap"] or {}
            w.writerow([e["iteration"], e["id"], e["experiment_id"], e["decision"], m["CAR"], m["FAR"], m["AUROC"], m["R@4"], m["P@4"],
                        e.get("gain_queries", ""), b.get("p_gain", ""), m["threshold"]])
    L = ["# Round 2 summary: abstention stage (train only, post hoc)", "",
         "Objective and rule: `03_experiments/optimization_objective.md`, Amendment 1. Retrieval metrics are identical across all rows by construction (guardrail R1).",
         "", "| # | gate signal | correct abstention | gain (queries) | P(gain) | AUROC | absent_clause (of 26) | not_in_corpus (of 7) | out_of_scope (of 6) | decision |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for e in entries:
        m, b, c = e["metrics"], e["bootstrap"] or {}, e["category_correct_abstentions"]
        L.append(f"| {e['iteration']} | `{e['id']}` | {m['CAR']:.3f} ({round(m['CAR'] * m['n_unanswerable'])}/{m['n_unanswerable']}) | {e.get('gain_queries', '')} | "
                 f"{b.get('p_gain', float('nan')):.3f} | {m['AUROC']:.3f} | {c.get('absent_clause', 0)} | {c.get('not_in_corpus', 0)} | {c.get('out_of_scope', 0)} | **{e['decision']}** |")
    L += ["", f"Selected gate: {desc}. Saved as `03_experiments/configs/final.yaml` / `final_resolved.yaml`; round-1 selection preserved as `final_round1*.yaml`."]
    (exp / "experiment_summary_round2.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return {"n_iterations": len(entries) - 1, "accepted": seq, "best": best["experiment_id"], "best_CAR": best["metrics"]["CAR"]}
