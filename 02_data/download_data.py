"""Download ONLY benchmarks/cuad.json and the corpus/cuad files referenced by the 194 CUAD-mini queries
from the HF mirror awinml/legalbench-rag, at a pinned revision, verifying sha256 against the mirror's SHA256SUMS.

    python 02_data/download_data.py            # idempotent; skips files that already verify

Writes 02_data/raw/ (git-ignored) and 02_data/acquisition_record.json (committed).
"""
import hashlib
import json
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "04_src"))

from huggingface_hub import hf_hub_download  # noqa: E402

from contract_intel.data.benchmark import load_tests, select_mini_with_ids  # noqa: E402

REPO = "awinml/legalbench-rag"
REVISION = "2b9c248bc8179ef0908fd6ba01d50b156facd48b"  # dataset commit observed 2026-10-29 (lastModified 2026-09-28)
RAW = ROOT / "02_data" / "raw"
BASE_URL = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fetch(rel: str) -> Path:
    """hf_hub_download into RAW, trying the path as given and its NFC/NFD spellings."""
    last = None
    for cand in dict.fromkeys([rel, unicodedata.normalize("NFC", rel), unicodedata.normalize("NFD", rel)]):
        try:
            p = hf_hub_download(REPO, cand, repo_type="dataset", revision=REVISION, local_dir=RAW)
            return Path(p)
        except Exception as e:  # noqa: BLE001 - try next spelling
            last = e
    raise RuntimeError(f"could not download {rel}: {last}")


def main() -> None:
    started = datetime.now(timezone.utc)
    sums_path = fetch("SHA256SUMS")
    sums = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            sums[unicodedata.normalize("NFC", name.strip())] = digest

    cuad = fetch("benchmarks/cuad.json")
    rec = {"benchmark": {"path": "benchmarks/cuad.json", "sha256": sha256_file(cuad)}}
    assert rec["benchmark"]["sha256"] == sums["benchmarks/cuad.json"], "cuad.json checksum mismatch"

    mini = select_mini_with_ids(load_tests(cuad))
    needed = sorted({unicodedata.normalize("NFC", m["test"]["snippets"][0]["file_path"]) for m in mini}
                    | {unicodedata.normalize("NFC", s["file_path"]) for m in mini for s in m["test"]["snippets"]})
    files = []
    for rel in needed:
        p = fetch("corpus/" + rel)  # NFC spelling matches the mirror's file name
        digest = sha256_file(p)
        expect = sums.get("corpus/" + rel)
        if digest != expect:
            raise SystemExit(f"checksum mismatch for {rel}: {digest} != {expect}")
        files.append({"doc_id": rel, "sha256": digest, "bytes": p.stat().st_size})

    record = {
        "source": f"https://huggingface.co/datasets/{REPO}",
        "revision": REVISION,
        "base_url": BASE_URL,
        "acquired_at_utc": started.isoformat(timespec="seconds"),
        "files_requested": ["benchmarks/cuad.json", "SHA256SUMS", f"{len(files)} files under corpus/cuad/"],
        "benchmark": rec["benchmark"],
        "n_documents": len(files),
        "documents": files,
        "checksums_verified_against": "SHA256SUMS (mirror)",
        "note": "full mirror not downloaded; only files referenced by the 194 CUAD-mini queries",
    }
    (ROOT / "02_data" / "acquisition_record.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK: cuad.json + {len(files)} documents verified (revision {REVISION[:8]})")


if __name__ == "__main__":
    main()
