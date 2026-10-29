"""The acceptance rule declared in 03_experiments/optimization_objective.md. Pure functions; no I/O."""
import numpy as np

MIN_DELTA = 0.010       # minimum absolute gain in primary metric
MIN_P_GAIN = 0.90       # paired-bootstrap probability that the gain is > 0
G1_PRECISION_FLOOR = 0.90
G3_R1_DROP = 0.02
G4_P95_MS = 2000.0
G5_BUILD_S = 900.0
BOOTSTRAP_B = 2000
BOOTSTRAP_SEED = 0


def paired_bootstrap(parent: list[float], cand: list[float], b: int = BOOTSTRAP_B, seed: int = BOOTSTRAP_SEED) -> dict:
    """Resample query indices with replacement (same indices for both arms) and look at the mean per-query difference."""
    if len(parent) != len(cand) or not parent:
        raise ValueError("paired bootstrap needs equal-length, non-empty per-query vectors")
    d = np.asarray(cand) - np.asarray(parent)
    rng = np.random.default_rng(seed)
    means = d[rng.integers(0, len(d), size=(b, len(d)))].mean(axis=1)
    return {"mean_delta": float(d.mean()), "p_gain": float((means > 0).mean()),
            "ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))], "B": b, "seed": seed}


def guardrails(parent: dict, cand: dict, pk: int, n_unanswerable: int) -> dict:
    """parent/cand are `headline()` dicts. Returns {id: {value, limit, pass}}."""
    car_tol = 1.0 / n_unanswerable if n_unanswerable else 0.0
    g = {
        "G1_precision": {"value": cand[f"P@{pk}"], "limit": G1_PRECISION_FLOOR * parent[f"P@{pk}"]},
        "G2_correct_abstention": {"value": cand["CAR"], "limit": parent["CAR"] - car_tol - 1e-12},
        "G3_recall_at_1": {"value": cand["R@1"], "limit": parent["R@1"] - G3_R1_DROP},
        "G4_p95_latency_ms": {"value": cand["p95_ms"], "limit": G4_P95_MS},
        "G5_build_seconds": {"value": cand["build_s"], "limit": G5_BUILD_S},
    }
    for k, v in g.items():
        v["pass"] = v["value"] <= v["limit"] if k in ("G4_p95_latency_ms", "G5_build_seconds") else v["value"] >= v["limit"]
    return g


def decide(parent: dict, cand: dict, parent_recalls: list[float], cand_recalls: list[float], pk: int, n_unanswerable: int) -> dict:
    boot = paired_bootstrap(parent_recalls, cand_recalls)
    gr = guardrails(parent, cand, pk, n_unanswerable)
    delta = cand[f"R@{pk}"] - parent[f"R@{pk}"]
    failed = [k for k, v in gr.items() if not v["pass"]]
    if failed:
        decision, reason = "rejected", f"guardrail failed: {', '.join(failed)}"
    elif delta >= MIN_DELTA and boot["p_gain"] >= MIN_P_GAIN:
        decision, reason = "accepted", f"R@{pk} +{delta:.4f} >= {MIN_DELTA} and P(gain)={boot['p_gain']:.3f} >= {MIN_P_GAIN}; all guardrails pass"
    elif delta >= MIN_DELTA:
        decision, reason = "inconclusive", f"R@{pk} +{delta:.4f} >= {MIN_DELTA} but P(gain)={boot['p_gain']:.3f} < {MIN_P_GAIN}"
    else:
        decision, reason = "rejected", f"R@{pk} change {delta:+.4f} is below the minimum gain {MIN_DELTA}"
    return {"decision": decision, "reason": reason, "delta_primary": delta, "bootstrap": boot, "guardrails": gr}
