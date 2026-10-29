"""Application layer shared by the CLI and the web app. It owns config resolution, pipeline construction and input/
error handling, and contains NO retrieval logic: all retrieval happens in `Pipeline`."""
from pathlib import Path

from ..common.config import ConfigError, PipelineConfig, config_from_dict, load_config
from ..common.schemas import SearchResponse
from ..data.loader import MissingDataError, load_store
from ..data.queries import ROOT
from ..pipeline import Pipeline

CONFIG_DIR = ROOT / "03_experiments" / "configs"
MAX_QUERY_CHARS = 2000


class ApplicationError(Exception):
    """Base class for errors that should be shown to the user as a message (not a traceback)."""


class InvalidQuery(ApplicationError):
    pass


class ConfigNotCalibrated(ApplicationError):
    pass


def list_configs(config_dir: Path = CONFIG_DIR) -> list[str]:
    """Named configurations that can be selected (excludes resolved/frozen helper files)."""
    return sorted(p.stem for p in Path(config_dir).glob("*.yaml") if not p.stem.endswith("_resolved"))


def resolve_config_path(name_or_path: str, config_dir: Path = CONFIG_DIR) -> Path:
    p = Path(name_or_path)
    if p.suffix in (".yaml", ".yml") and p.exists():
        return p
    cand = Path(config_dir) / f"{name_or_path}.yaml"
    if cand.exists():
        return cand
    raise ConfigError(f"unknown configuration {name_or_path!r}. Available: {', '.join(list_configs(config_dir)) or '(none)'}")


def load_calibrated_config(name_or_path: str, config_dir: Path = CONFIG_DIR) -> PipelineConfig:
    """Config with a concrete abstention threshold. A config whose threshold is null is calibrated on train by the
    evaluator, which writes `<name>_resolved.yaml` next to it; that frozen file is used here."""
    path = resolve_config_path(name_or_path, config_dir)
    cfg = load_config(path)
    if cfg.abstention.threshold is None:
        frozen = path.with_name(path.stem + "_resolved.yaml")
        if not frozen.exists():
            raise ConfigNotCalibrated(
                f"configuration {cfg.name!r} has no calibrated abstention threshold. Run "
                f"`python -m contract_intel evaluate --config {path.stem} --split train` first.")
        cfg = load_config(frozen)
    return cfg


class SearchService:
    def __init__(self, config: str | Path = "final", data_dir: Path | None = None, config_dir: Path = CONFIG_DIR):
        self.cfg = load_calibrated_config(str(config), config_dir)
        try:
            self.store = load_store(data_dir) if data_dir else load_store()
        except MissingDataError as e:
            raise ApplicationError(str(e)) from e
        self.pipeline = Pipeline(self.cfg, self.store)

    @staticmethod
    def validate_query(query: str) -> str:
        if not isinstance(query, str) or not query.strip():
            raise InvalidQuery("Please enter a question.")
        q = " ".join(query.split())
        if len(q) > MAX_QUERY_CHARS:
            raise InvalidQuery(f"The question is too long ({len(q)} characters; limit {MAX_QUERY_CHARS}).")
        return q

    def search(self, query: str, k: int = 5) -> SearchResponse:
        q = self.validate_query(query)
        if not isinstance(k, int) or not (1 <= k <= 64):
            raise InvalidQuery("The number of results must be an integer between 1 and 64.")
        resp = self.pipeline.search(q, k)
        # Provenance double-check before anything is shown: every offset must reproduce the displayed text.
        for p in resp.passages + resp.ranked_candidates:
            if self.store.text(p.doc_id)[p.start:p.end] != p.text:
                raise RuntimeError(f"offset integrity violated for {p.chunk_id}")
        return resp

    def documents(self) -> list[str]:
        return self.store.doc_ids()


__all__ = ["ApplicationError", "InvalidQuery", "ConfigNotCalibrated", "SearchService", "list_configs",
           "resolve_config_path", "load_calibrated_config", "config_from_dict"]
