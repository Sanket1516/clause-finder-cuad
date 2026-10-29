"""Single-command improvement loop (TRAIN data only).

    python 03_experiments/run_improvement_loop.py [--max-iterations 20]

Restartable: progress is read from 03_experiments/experiment_log.jsonl. See 03_experiments/optimization_objective.md."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "04_src"))

from contract_intel.experiments.loop import run_loop  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--baseline-config", type=Path, default=ROOT / "03_experiments" / "configs" / "baseline.yaml")
    ap.add_argument("--catalogue", type=Path, default=ROOT / "03_experiments" / "proposals" / "catalogue.yaml")
    ap.add_argument("--max-iterations", type=int, default=20, help="maximum iterations beyond the baseline")
    ap.add_argument("--restart", action="store_true", help="archive the existing log/iterations to 03_experiments/previous_runs/ and re-run from scratch")
    a = ap.parse_args()
    if a.restart:
        from contract_intel.experiments.archive import archive_previous
        print("archived to:", archive_previous(ROOT, "experiment_log.jsonl", "[0-9][0-9]-*"))
    out = run_loop(ROOT, a.baseline_config, a.catalogue, a.max_iterations, "python " + " ".join(sys.argv))
    print(json.dumps({k: out[k] for k in ("n_iterations_beyond_baseline", "decisions", "accepted_sequence")}, indent=1))
    print("best train:", out["best_train"]["experiment_id"], "R@4 =", round(out["best_train"]["R@4"], 4))


if __name__ == "__main__":
    main()
