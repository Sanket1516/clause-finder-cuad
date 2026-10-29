"""Runs a pipeline over one explicitly named split and produces per-query evidence plus aggregate metrics."""
import json
import platform
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..abstention.gate import calibrate_threshold, decide
from ..common.config import PipelineConfig, config_from_dict
from ..common.logging import get_logger
from ..data.queries import EvalQuery, load_queries
from ..pipeline import Pipeline
from .diagnose import LABELS_ANSWERABLE, diagnose_answerable, diagnose_unanswerable
from .guard import check_split, git_commit, record_test_run
from .metrics import abstention_metrics, aggregate_retrieval, auroc, char_precision_recall

log = get_logger()


def _iv(passages) -> list:
    return [(p.doc_id, p.start, p.end) for p in passages]


def evaluate(pipeline: Pipeline, split: str, purpose: str = "development", confirm_test: bool = False,
             queries: list[EvalQuery] | None = None, calibrate_on: list[EvalQuery] | None = None) -> dict:
    """Return {'records', 'metrics', 'resolved_config', 'errors', 'timing'}.

    The abstention threshold is taken from the config. If it is null it is calibrated on the ANSWERABLE queries of this run
    (train only; calibration on test is refused) and written into `resolved_config`."""
    check_split(split, purpose, confirm_test)
    cfg: PipelineConfig = pipeline.cfg
    ks, pk = cfg.evaluation.ks, cfg.evaluation.primary_k
    queries = queries if queries is not None else load_queries(split)
    t_all = time.perf_counter()
    raw, errors = [], []
    for q in queries:
        try:
            cands, conf, lat = pipeline.retrieve(q.query)  # the ONLY thing the pipeline receives is the question text
            raw.append((q, cands[: max(ks)], conf, lat, len(cands)))
        except Exception as e:  # noqa: BLE001 - recorded, never silently dropped
            errors.append({"query_id": q.query_id, "error": f"{type(e).__name__}: {e}"})
            log.error("query %s failed: %s", q.query_id, e)
    if errors:
        raise RuntimeError(f"{len(errors)} queries failed; first: {errors[0]}")

    tau = cfg.abstention.threshold
    if tau is None:
        if split != "train":
            raise ValueError("threshold is not calibrated; calibrate on train and freeze it in the config before evaluating test")
        tau = calibrate_threshold([c for q, _, c, _, _ in raw if q.answerable], cfg.abstention.target_far)
        log.info("calibrated abstention threshold on %d train answerable queries: %.4f", sum(q.answerable for q, *_ in raw), tau)
    resolved = config_from_dict({**cfg.model_dump(mode="json"), "abstention": {**cfg.abstention.model_dump(mode="json"), "threshold": tau}})

    records = []
    for q, cands, conf, lat, n_total in raw:
        decision, reason = decide(conf, n_total, tau)
        abstained = decision != "answered"
        offsets_ok = all(pipeline.store.text(p.doc_id)[p.start:p.end] == p.text for p in cands)
        rec = {"query_id": q.query_id, "split": split, "query": q.query, "answerable": q.answerable, "category": q.category,
               "decision": decision, "abstained": abstained, "abstention_reason": reason, "confidence": conf, "threshold": tau,
               "passages": [{"rank": p.rank, "doc_id": p.doc_id, "start": p.start, "end": p.end, "score": p.score} for p in cands],
               "gold_for_evaluation_only": [{"doc_id": g.doc_id, "start": g.start, "end": g.end} for g in q.gold],
               "latency_ms": lat, "experiment_id": pipeline.experiment_id, "config_hash": pipeline.config_hash}
        if q.answerable:
            gold = [(g.doc_id, g.start, g.end) for g in q.gold]
            rank_view = {str(k): char_precision_recall(_iv(cands[:k]), gold) for k in ks}
            e2e_view = {str(k): char_precision_recall([] if abstained else _iv(cands[:k]), gold) for k in ks}
            d = diagnose_answerable(_iv(cands), gold, rank_view[str(pk)]["recall"], pk, len(pipeline.store.text(q.gold[0].doc_id)), offsets_ok)
            rec["metrics"] = {"ranking": rank_view, "end_to_end": e2e_view}
            rec["e2e_label"] = "false_abstention" if abstained else d["label"]
        else:
            d = diagnose_unanswerable(abstained)
            rec["e2e_label"] = d["label"]
        rec.update({"label": d["label"], "found_rank": d["found_rank"], "top1_doc_correct": d["top1_doc_correct"], "flags": d["flags"],
                    "offsets_ok": offsets_ok})
        records.append(rec)

    ans = [r for r in records if r["answerable"]]
    un = [r for r in records if not r["answerable"]]
    lat_total = sorted(sum(r["latency_ms"].values()) for r in records)
    metrics = {
        "experiment_id": pipeline.experiment_id, "config_hash": pipeline.config_hash, "split": split, "purpose": purpose,
        "n_queries": len(records), "n_answerable": len(ans), "n_unanswerable": len(un),
        "threshold": tau, "primary_k": pk,
        "retrieval_ranking_view": aggregate_retrieval(ans, ks, "ranking"),
        "retrieval_end_to_end": aggregate_retrieval(ans, ks, "end_to_end"),
        "abstention": abstention_metrics([{"answerable": r["answerable"], "abstained": r["abstained"]} for r in records]),
        "confidence_auroc_answerable_vs_unanswerable": auroc([r["confidence"] for r in ans], [r["confidence"] for r in un]),
        "label_counts_answerable": dict(Counter(r["label"] for r in ans)),
        "e2e_label_counts": dict(Counter(r["e2e_label"] for r in records)),
        "unanswerable_by_category": {c: {"n": sum(1 for r in un if r["category"] == c),
                                         "correct_abstentions": sum(1 for r in un if r["category"] == c and r["abstained"])}
                                     for c in sorted({r["category"] for r in un})},
        "document_hit_at_1": sum(1 for r in ans if r["top1_doc_correct"]) / max(len(ans), 1),
        "offset_integrity_failures": sum(1 for r in records if not r["offsets_ok"]),
        "latency_ms": {"p50": lat_total[len(lat_total) // 2] if lat_total else None,
                       "p95": lat_total[min(len(lat_total) - 1, int(0.95 * len(lat_total)))] if lat_total else None},
        "index_build_seconds": pipeline.build_seconds, "n_chunks": len(pipeline.chunks),
        "wall_seconds": round(time.perf_counter() - t_all, 3),
    }
    return {"records": records, "metrics": metrics, "resolved_config": resolved, "errors": errors}


def save_run(result: dict, out_dir: Path, command: str, overwrite: bool = False, ledger: Path | None = None) -> dict:
    """Write predictions, metrics, resolved config, run info. Refuses to overwrite earlier results unless asked."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    m = result["metrics"]
    paths = {"predictions": out_dir / f"{m['split']}_predictions.jsonl", "metrics": out_dir / f"{m['split']}_metrics.json",
             "config": out_dir / "resolved_config.yaml", "run_info": out_dir / f"{m['split']}_run_info.json",
             "errors": out_dir / f"{m['split']}_errors.log"}
    if not overwrite:
        existing = [p.name for p in paths.values() if p.exists()]
        if existing:
            raise FileExistsError(f"refusing to overwrite earlier results in {out_dir}: {existing}")
    paths["predictions"].write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in result["records"]), encoding="utf-8")
    paths["metrics"].write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["config"].write_text(yaml.safe_dump(result["resolved_config"].model_dump(mode="json"), sort_keys=False), encoding="utf-8")
    paths["errors"].write_text("\n".join(json.dumps(e) for e in result["errors"]) + ("\n" if result["errors"] else ""), encoding="utf-8")
    paths["run_info"].write_text(json.dumps({
        "command": command, "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git_commit": git_commit(),
        "python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine(),
        "split": m["split"], "purpose": m["purpose"], "experiment_id": m["experiment_id"], "config_hash": m["config_hash"],
        "wall_seconds": m["wall_seconds"], "index_build_seconds": m["index_build_seconds"]}, indent=2) + "\n", encoding="utf-8")
    if m["split"] == "test":
        n = (record_test_run(m["experiment_id"], m["config_hash"], "final reporting", str(paths["metrics"]), ledger)
             if ledger else record_test_run(m["experiment_id"], m["config_hash"], "final reporting", str(paths["metrics"])))
        log.warning("TEST SPLIT EVALUATED (run #%d recorded in the ledger)", n)
    return {k: str(v) for k, v in paths.items()}


def headline(m: dict) -> dict:
    """Flat view used by logs, the loop and tables."""
    r, e = m["retrieval_ranking_view"], m["retrieval_end_to_end"]
    a = m["abstention"]
    out = {"n_answerable": m["n_answerable"], "n_unanswerable": m["n_unanswerable"], "threshold": m["threshold"]}
    for k in r:
        out[f"R@{k}"], out[f"P@{k}"] = r[k]["recall"], r[k]["precision"]
        out[f"e2e_R@{k}"], out[f"e2e_P@{k}"] = e[k]["recall"], e[k]["precision"]
    out.update({"FAR": a["false_abstention_rate"], "CAR": a["correct_abstention_rate"], "false_answer_rate": a["false_answer_rate"],
                "AUROC": m["confidence_auroc_answerable_vs_unanswerable"], "doc_hit@1": m["document_hit_at_1"],
                "p95_ms": m["latency_ms"]["p95"], "build_s": m["index_build_seconds"]})
    return out


__all__ = ["evaluate", "save_run", "headline", "LABELS_ANSWERABLE"]
