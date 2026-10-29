"""Pipeline configuration: YAML with `extends:` inheritance, strict pydantic validation, canonical hash.
Every pipeline choice lives here; code defaults exist only where a field is documented as presentation-only."""
import copy
import hashlib
import json
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChunkingConfig(_Strict):
    strategy: Literal["fixed", "paragraph", "clause"] = "fixed"
    size_chars: int = Field(500, ge=50, le=20000)
    overlap_chars: int = Field(0, ge=0)  # only used by `fixed`
    min_chars: int = Field(20, ge=1)  # chunks shorter than this (after trimming) are dropped

    @model_validator(mode="after")
    def _check(self):
        if self.overlap_chars >= self.size_chars:
            raise ValueError("overlap_chars must be smaller than size_chars")
        return self


class TokenizerConfig(_Strict):
    lowercase: bool = True
    stopwords: Literal["none", "english"] = "none"
    stem: Literal["none", "light"] = "none"
    min_token_len: int = Field(1, ge=1)


class Bm25Config(_Strict):
    k1: float = Field(1.5, gt=0)
    b: float = Field(0.75, ge=0, le=1)
    tokenizer: TokenizerConfig = TokenizerConfig()


class QueryConfig(_Strict):
    # Remove the leading 'Consider the <title>;' clause from the text that is scored against chunks.
    strip_title_prefix: bool = False


class RoutingConfig(_Strict):
    mode: Literal["none", "boost", "filter"] = "none"
    top_docs: int = Field(1, ge=1)
    head_chars: int = Field(3000, ge=100)  # beginning of each contract used to match the query's title
    boost: float = Field(1.0, ge=0)  # multiplier added to the chunk score for routed docs (mode=boost)


class RetrievalConfig(_Strict):
    method: Literal["bm25"] = "bm25"
    candidates: int = Field(100, ge=1, le=5000)  # candidate pool size before overlap removal
    bm25: Bm25Config = Bm25Config()


class RankingConfig(_Strict):
    remove_overlaps: bool = True  # drop lower-ranked passages overlapping a higher-ranked one (same document)
    expand_chars: int = Field(0, ge=0)  # grow each passage by this many chars on both sides (snapped to document bounds)


class AbstentionConfig(_Strict):
    signal: Literal["top1_score", "top1_norm", "margin_norm", "coverage", "title_match", "top1_norm_x_title", "coverage_x_title"] = "top1_score"
    threshold: Optional[float] = None  # None => must be calibrated on train before use
    target_far: float = Field(0.05, ge=0, le=1)  # calibration target: false-abstention rate on answerable train queries


SIGNALS_NEEDING_ROUTER = {"title_match", "top1_norm_x_title", "coverage_x_title"}


class EvaluationConfig(_Strict):
    ks: list[int] = [1, 2, 4, 8, 16, 32, 64]
    primary_k: int = 4

    @model_validator(mode="after")
    def _check(self):
        if self.primary_k not in self.ks or sorted(set(self.ks)) != self.ks or min(self.ks) < 1:
            raise ValueError("ks must be sorted unique positive ints and contain primary_k")
        return self


class PipelineConfig(_Strict):
    name: str
    description: str = ""
    chunking: ChunkingConfig = ChunkingConfig()
    query: QueryConfig = QueryConfig()
    routing: RoutingConfig = RoutingConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    ranking: RankingConfig = RankingConfig()
    abstention: AbstentionConfig = AbstentionConfig()
    evaluation: EvaluationConfig = EvaluationConfig()

    @model_validator(mode="after")
    def _cross_checks(self):
        if self.abstention.signal in SIGNALS_NEEDING_ROUTER and self.routing.mode == "none":
            raise ValueError(f"abstention.signal '{self.abstention.signal}' needs routing.mode != 'none' (it uses the title match)")
        return self


class ConfigError(ValueError):
    pass


def _deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _load_raw(path: Path, _seen: tuple = ()) -> dict:
    path = Path(path).resolve()
    if path in _seen:
        raise ConfigError(f"circular extends: {path}")
    if not path.exists():
        raise ConfigError(f"config not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"invalid YAML in {path}: {e}") from e
    if not isinstance(raw, dict):
        raise ConfigError(f"config root must be a mapping: {path}")
    parent = raw.pop("extends", None)
    if parent:
        return _deep_merge(_load_raw(path.parent / parent, _seen + (path,)), raw)
    return raw


def config_from_dict(raw: dict) -> PipelineConfig:
    try:
        return PipelineConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(str(e)) from e


def load_config(path: Path | str) -> PipelineConfig:
    return config_from_dict(_load_raw(Path(path)))


def config_hash(cfg: PipelineConfig) -> str:
    """sha256 of the canonical resolved config, ignoring name/description (labels, not behaviour)."""
    d = cfg.model_dump(mode="json")
    d.pop("name", None)
    d.pop("description", None)
    return hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def dump_config(cfg: PipelineConfig, path: Path | str) -> None:
    Path(path).write_text(yaml.safe_dump(cfg.model_dump(mode="json"), sort_keys=False), encoding="utf-8")
