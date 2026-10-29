"""Write 03_experiments/configs/final_freeze.json: checksums, commit, environment and rationale for the frozen configurations.
Run BEFORE the held-out evaluation:  python 03_experiments/freeze_record.py"""
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "04_src"))

from contract_intel.common.config import config_hash, load_config  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> None:
    cfgs = ROOT / "03_experiments" / "configs"
    out = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(),
           "git_dirty_files": [l[3:] for l in subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=ROOT).stdout.splitlines()
                               if not l.endswith("/") and "gitkeep" not in l],
           "configs": {}}
    for name in ("baseline", "final"):
        unres, res = cfgs / f"{name}.yaml", cfgs / f"{name}_resolved.yaml"
        c = load_config(res)
        out["configs"][name] = {"file": f"03_experiments/configs/{res.name}", "file_sha256": sha(res), "unresolved_file_sha256": sha(unres),
                                "config_hash": config_hash(c), "abstention_threshold": c.abstention.threshold,
                                "abstention_signal": c.abstention.signal, "contents": c.model_dump(mode="json")}
    out["dataset"] = {k: sha(ROOT / "02_data" / k) for k in ("query_manifest.jsonl", "gold_annotations.jsonl", "document_manifest.jsonl",
                                                             "split_manifest.json", "unanswerable_queries.jsonl")}
    out["dataset"]["source_revision"] = json.loads((ROOT / "02_data" / "acquisition_record.json").read_text(encoding="utf-8"))["revision"]
    out["environment"] = {"python": platform.python_version(), "platform": platform.platform(), "machine": platform.machine(),
                          "packages": {p: metadata.version(p) for p in ("pydantic", "PyYAML", "numpy", "typer", "streamlit", "huggingface_hub", "pytest")}}
    out["selection_rationale"] = (
        "Chosen on TRAIN only. Round 1 (15 pre-registered candidates, primary metric train recall@4): accepted title routing, paragraph-aware chunks, light "
        "stemming. Round 2 (post hoc, declared before running; gate-only candidates; primary metric train correct abstention at <=5% false abstention): "
        "accepted the normalised top-score gate. See 03_experiments/experiment_summary.md and experiment_summary_round2.md.")
    out["rules"] = "No configuration or threshold may be changed after this record. The test split is evaluated once per configuration."
    (cfgs / "final_freeze.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"commit": out["git_commit"][:8], "dirty": out["git_dirty_files"],
                      **{n: (v["config_hash"][:8], v["abstention_threshold"]) for n, v in out["configs"].items()}}))


if __name__ == "__main__":
    main()
