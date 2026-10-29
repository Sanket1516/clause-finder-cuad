"""Round 2: abstention stage (TRAIN only, post hoc; see optimization_objective.md Amendment 1).

    python 03_experiments/run_abstention_stage.py

Run AFTER run_improvement_loop.py. Restartable via experiment_log_round2.jsonl."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "04_src"))

from contract_intel.experiments.abstention_stage import run_stage  # noqa: E402

if __name__ == "__main__":
    out = run_stage(ROOT, ROOT / "03_experiments" / "proposals" / "catalogue_round2.yaml", "python " + " ".join(sys.argv))
    print(json.dumps(out, indent=1))
