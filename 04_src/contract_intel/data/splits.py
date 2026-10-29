"""The prescribed train/test split. Must not be altered (the split is mandated)."""
import hashlib


def assign_split(query: str) -> str:
    h = int(hashlib.sha256(query.strip().encode("utf-8")).hexdigest(), 16)
    return "test" if h % 10 < 3 else "train"
