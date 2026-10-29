"""Command-line interface.

Exit codes:  0 passages returned | 10 abstained (no passage cleared the evidence threshold; not an error)
             2 invalid input | 3 missing data / unknown or uncalibrated configuration | 4 unexpected runtime error
"""
import json
import sys
from pathlib import Path
from typing import Optional

import typer

from ..application import ApplicationError, ConfigNotCalibrated, InvalidQuery, SearchService, list_configs, resolve_config_path
from ..common.config import ConfigError, load_config
from ..common.logging import get_logger
from ..data.loader import MissingDataError

app = typer.Typer(add_completion=False, no_args_is_help=True,
                  help="Contract clause search: returns the passages most likely to answer a question, with source offsets.")
log = get_logger()

EXIT_OK, EXIT_ABSTAINED, EXIT_INPUT, EXIT_MISSING, EXIT_RUNTIME = 0, 10, 2, 3, 4


def _fail(msg: str, code: int):
    typer.secho(f"error: {msg}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code)


def _guard(fn):
    """Run fn(); translate expected errors into messages and exit codes."""
    try:
        return fn()
    except typer.Exit:
        raise
    except InvalidQuery as e:
        _fail(str(e), EXIT_INPUT)
    except (ConfigNotCalibrated, MissingDataError, ConfigError, ApplicationError, FileNotFoundError) as e:
        _fail(str(e), EXIT_MISSING)
    except Exception as e:  # noqa: BLE001
        log.exception("unexpected error")
        _fail(f"unexpected {type(e).__name__}: {e}", EXIT_RUNTIME)


@app.command()
def configs():
    """List the selectable retrieval configurations."""
    for c in list_configs():
        typer.echo(c)


@app.command()
def search(
    question: str = typer.Argument(..., help="Natural-language contract question, e.g. 'Consider the <contract>; What is the governing law?'"),
    config: str = typer.Option("final", "--config", "-c", help="Configuration name (see `configs`) or path to a YAML file."),
    k: int = typer.Option(5, "--k", "-k", help="Number of passages to return (1-64)."),
    json_out: bool = typer.Option(False, "--json", help="Print the full response as JSON."),
    save: Optional[Path] = typer.Option(None, "--save", help="Also write the full JSON response to this file."),
    show_weak: bool = typer.Option(False, "--show-weak", help="When abstaining, also list the best passages found (NOT sufficient evidence)."),
):
    """Find the passages that answer QUESTION, or report that no passage cleared the evidence threshold."""
    def run():
        svc = SearchService(config)
        resp = svc.search(question, k)
        if save:
            Path(save).write_text(resp.model_dump_json(indent=2), encoding="utf-8")
        if json_out:
            typer.echo(resp.model_dump_json(indent=2))
        else:
            typer.echo(f"config: {resp.experiment_id}   confidence: {resp.confidence:.3f}   threshold: {resp.threshold:.3f}")
            if resp.abstained:
                typer.secho("NO SUFFICIENT EVIDENCE FOUND", fg=typer.colors.YELLOW, bold=True)
                typer.echo(resp.abstention_reason or "")
                typer.echo("Note: this is not proof that the contract lacks such a clause. Review the contract manually.")
                if show_weak:
                    typer.echo("\nBest passages found (below threshold, NOT sufficient evidence):")
                    for p in resp.ranked_candidates[:k]:
                        _print_passage(p)
            else:
                typer.echo(f"{len(resp.passages)} passage(s) cleared the evidence threshold (candidates, not legal conclusions):\n")
                for p in resp.passages:
                    _print_passage(p)
        raise typer.Exit(EXIT_ABSTAINED if resp.abstained else EXIT_OK)
    _guard(run)


def _print_passage(p) -> None:
    typer.secho(f"[{p.rank}] score={p.score:.3f}  {p.doc_id}  chars {p.start}-{p.end}", bold=True)
    typer.echo("    " + " ".join(p.text.split())[:600] + ("..." if len(" ".join(p.text.split())) > 600 else ""))
    typer.echo("")


@app.command()
def evaluate(
    config: str = typer.Option("baseline", "--config", "-c", help="Configuration name or YAML path."),
    split: str = typer.Option("train", "--split", help="train (development) or test (final reporting only)."),
    final: bool = typer.Option(False, "--final", help="Mark this as a final-reporting run (required for --split test)."),
    confirm_test: bool = typer.Option(False, "--confirm-test", help="Explicitly confirm that the held-out test split may be used."),
    out_dir: Optional[Path] = typer.Option(None, "--out-dir", help="Where to write predictions/metrics (default 03_experiments/runs/<experiment_id>)."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Allow overwriting an earlier run in out-dir."),
):
    """Evaluate a configuration on ONE explicitly named split and save per-query evidence and metrics."""
    from ..data.queries import ROOT
    from ..evaluation.evaluator import evaluate as run_eval, headline, save_run
    from ..evaluation.guard import SplitGuardError
    from ..data.loader import load_store
    from ..pipeline import Pipeline

    def run():
        cfg = load_config(resolve_config_path(config))
        if cfg.abstention.threshold is None and split == "test":
            frozen = resolve_config_path(config).with_name(resolve_config_path(config).stem + "_resolved.yaml")
            if not frozen.exists():
                _fail("threshold not calibrated: evaluate on train first", EXIT_MISSING)
            cfg = load_config(frozen)
        typer.secho(f"evaluating {cfg.name} on split={split} (purpose={'final' if final else 'development'})", err=True)
        pipe = Pipeline(cfg, load_store())
        try:
            res = run_eval(pipe, split, "final" if final else "development", confirm_test)
        except SplitGuardError as e:
            _fail(str(e), EXIT_INPUT)
        target = out_dir or (ROOT / "03_experiments" / "runs" / res["metrics"]["experiment_id"])
        paths = save_run(res, target, " ".join(["python", "-m", "contract_intel"] + sys.argv[1:]), overwrite)
        if split == "train":  # freeze the calibrated threshold so search/web can use this config
            from ..common.config import dump_config
            src = resolve_config_path(config)
            if load_config(src).abstention.threshold is None:
                dump_config(res["resolved_config"], src.with_name(src.stem + "_resolved.yaml"))
        h = headline(res["metrics"])
        typer.echo(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in h.items()}, indent=1))
        typer.echo(f"saved: {paths['metrics']}")
    _guard(run)


if __name__ == "__main__":
    app()
