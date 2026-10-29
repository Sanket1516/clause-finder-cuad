"""Protects the held-out test split. Development code (including the improvement loop) uses purpose='development',
which can only ever see train. Test is reachable only with purpose='final' AND an explicit confirmation, and every
test evaluation is appended to an append-only ledger so the number of test runs can be reported."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[3] / "06_results" / "test_runs" / "ledger.jsonl"


class SplitGuardError(RuntimeError):
    pass


def check_split(split: str, purpose: str, confirm_test: bool = False) -> None:
    if split not in ("train", "test"):
        raise SplitGuardError(f"unknown split {split!r}")
    if purpose not in ("development", "final"):
        raise SplitGuardError(f"unknown purpose {purpose!r}")
    if split == "test" and purpose != "final":
        raise SplitGuardError("the held-out test split may not be used for development, tuning or the improvement loop")
    if split == "test" and not confirm_test:
        raise SplitGuardError("test evaluation requires explicit confirmation (confirm_test=True / --confirm-test)")


def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=LEDGER.parents[2],
                              timeout=10).stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def record_test_run(experiment_id: str, config_hash: str, reason: str, metrics_path: str, ledger: Path = LEDGER) -> int:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    n = sum(1 for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()) + 1 if ledger.exists() else 1
    entry = {"run_no": n, "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "experiment_id": experiment_id,
             "config_hash": config_hash, "git_commit": git_commit(), "reason": reason, "metrics_path": metrics_path}
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return n
