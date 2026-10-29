"""Deterministic synthetic corpus for tests (no downloaded data needed)."""
from pathlib import Path

from contract_intel.common.config import config_from_dict
from contract_intel.data.corpus import DocumentStore

DOC_A = ("MARKETING AGREEMENT between Alpha Corp and Beta LLC.\n\n"
         "1. TERM. This agreement expires on December 31, 2030.\n\n"
         "2. GOVERNING LAW. This agreement shall be governed by the laws of the State of New York.\n\n"
         "3. ASSIGNMENT. Neither party may assign this agreement without prior written consent.\n\n")
DOC_B = ("SUPPLY AGREEMENT between Gamma Inc and Delta Ltd.\n\n"
         "1. PRICE. Delta shall pay the fees listed in Schedule A.\n\n"
         "2. WARRANTY. Gamma warrants the goods for twelve months.\n\n")
DOC_C = "x" * 40 + "\n" + "Short unrelated notice with zebra and quokka words only.\n"


def make_store(tmp_path: Path) -> DocumentStore:
    d = tmp_path / "corpus" / "cuad"
    d.mkdir(parents=True)
    for name, text in {"A.txt": DOC_A, "B.txt": DOC_B, "C.txt": DOC_C}.items():
        (d / name).write_text(text, encoding="utf-8")
    return DocumentStore(tmp_path / "corpus", ["cuad/A.txt", "cuad/B.txt", "cuad/C.txt"])


def make_config(**over):
    raw = {"name": "test", "chunking": {"strategy": "fixed", "size_chars": 100, "overlap_chars": 0},
           "abstention": {"threshold": 0.0}, "evaluation": {"ks": [1, 2, 4], "primary_k": 2}}
    for k, v in over.items():
        raw[k] = {**raw.get(k, {}), **v} if isinstance(v, dict) else v
    return config_from_dict(raw)


def make_app_env(tmp_path: Path, monkeypatch, threshold: float = 0.0):
    """A self-contained 'installation': data dir (manifest + corpus) and config dir, selected through the env vars."""
    import json

    from contract_intel.common.config import dump_config
    data = tmp_path / "data"
    corpus = data / "raw" / "corpus" / "cuad"
    corpus.mkdir(parents=True)
    for name, text in {"A.txt": DOC_A, "B.txt": DOC_B, "C.txt": DOC_C}.items():
        (corpus / name).write_text(text, encoding="utf-8")
    (data / "document_manifest.jsonl").write_text(
        "".join(json.dumps({"doc_id": f"cuad/{n}.txt"}) + "\n" for n in "ABC"), encoding="utf-8")
    cfgs = tmp_path / "configs"
    cfgs.mkdir()
    dump_config(make_config(name="final", query={"strip_title_prefix": True}, routing={"mode": "filter"}, abstention={"threshold": threshold}), cfgs / "final.yaml")
    dump_config(make_config(name="strict", query={"strip_title_prefix": True}, routing={"mode": "filter"}, abstention={"threshold": 1e9}), cfgs / "strict.yaml")
    dump_config(make_config(name="uncalibrated", abstention={"threshold": None}), cfgs / "uncalibrated.yaml")
    monkeypatch.setenv("CONTRACT_INTEL_DATA_DIR", str(data))
    monkeypatch.setenv("CONTRACT_INTEL_CONFIG_DIR", str(cfgs))
    return data, cfgs
