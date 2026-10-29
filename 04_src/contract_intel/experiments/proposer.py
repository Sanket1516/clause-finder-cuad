"""Rule-based proposer over the pre-registered catalogue. It sees only failure-label counts computed on TRAIN predictions."""
from collections import Counter
from pathlib import Path

import yaml

from ..common.config import PipelineConfig, _deep_merge, config_from_dict, config_hash


def load_catalogue(path: Path) -> list[dict]:
    entries = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["entries"]
    ids = [e["id"] for e in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate catalogue ids")
    return entries


def label_counts(records: list[dict]) -> Counter:
    """Ranking-view failure labels of the answerable train queries (hits excluded)."""
    return Counter(r["label"] for r in records if r["answerable"] and r["label"] != "hit")


def propose(catalogue: list[dict], counts: Counter, parent: PipelineConfig, tried_ids: set[str], tried_hashes: set[str],
            n_done: int) -> tuple[dict, PipelineConfig, str] | None:
    """Return (entry, candidate_config, why) or None when nothing applicable is left."""
    parent_raw = parent.model_dump(mode="json")
    for label, n in counts.most_common():
        for e in catalogue:
            if e["id"] in tried_ids or label not in e["targets"]:
                continue
            raw = _deep_merge(parent_raw, e["overrides"])
            raw["name"] = f"{n_done + 1:02d}-{e['id']}"
            raw["description"] = e["hypothesis"].strip()
            cand = config_from_dict(raw)
            if config_hash(cand) in tried_hashes:
                continue
            return e, cand, f"most frequent train failure is '{label}' ({n} of {sum(counts.values())} failing queries); entry targets it"
    # fall back to entries whose targets were not the top labels (e.g. abstention variants) in catalogue order
    for e in catalogue:
        if e["id"] in tried_ids:
            continue
        raw = _deep_merge(parent_raw, e["overrides"])
        raw["name"] = f"{n_done + 1:02d}-{e['id']}"
        raw["description"] = e["hypothesis"].strip()
        cand = config_from_dict(raw)
        if config_hash(cand) not in tried_hashes:
            return e, cand, "no entry targets a remaining failure label; next untried catalogue entry"
    return None
