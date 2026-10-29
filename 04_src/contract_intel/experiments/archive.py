"""Move earlier experiment logs/iterations aside (never delete) so a loop can be re-run from scratch."""
import shutil
from datetime import datetime, timezone
from pathlib import Path


def archive_previous(root: Path, log_name: str, iteration_glob: str) -> Path | None:
    exp = Path(root) / "03_experiments"
    items = [p for p in [exp / log_name, *sorted((exp / "iterations").glob(iteration_glob))] if p.exists()]
    if not items:
        return None
    dest = exp / "previous_runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (dest / "iterations").mkdir(parents=True, exist_ok=True)
    for p in items:
        shutil.move(str(p), str(dest / ("iterations" if p.is_dir() else "") / p.name))
    return dest
