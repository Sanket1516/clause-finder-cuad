"""CLI behaviour: output, exit codes, JSON, input validation, missing data/config, test-split protection."""
import json

import pytest
from fixtures import DOC_A, make_app_env
from typer.testing import CliRunner

from contract_intel.interfaces.cli import EXIT_ABSTAINED, EXIT_INPUT, EXIT_MISSING, EXIT_OK, EXIT_RUNTIME, app

runner = CliRunner()
Q = "Consider the Marketing Agreement between Alpha Corp and Beta LLC; What is the governing law?"


@pytest.fixture
def env(tmp_path, monkeypatch):
    return make_app_env(tmp_path, monkeypatch)


def run(*args):
    return runner.invoke(app, list(args))


def test_search_prints_ranked_passages_with_document_offsets_and_scores(env):
    r = run("search", Q, "-c", "final", "-k", "2")
    assert r.exit_code == EXIT_OK, r.output
    assert "cuad/A.txt" in r.output and "chars " in r.output and "score=" in r.output and "New York" in r.output
    assert "candidates, not legal conclusions" in r.output and r.output.count("[1]") == 1


def test_abstention_exit_code_and_wording(env):
    r = run("search", Q, "-c", "strict")
    assert r.exit_code == EXIT_ABSTAINED
    assert "NO SUFFICIENT EVIDENCE FOUND" in r.output and "not proof" in r.output and "score=" not in r.output
    weak = run("search", Q, "-c", "strict", "--show-weak")
    assert weak.exit_code == EXIT_ABSTAINED and "NOT sufficient evidence" in weak.output and "score=" in weak.output


def test_json_output_is_machine_readable_and_offsets_reproduce_text(env, tmp_path):
    out = tmp_path / "res.json"
    r = run("search", Q, "-c", "final", "--json", "--save", str(out))
    assert r.exit_code == EXIT_OK
    for data in (json.loads(r.output), json.loads(out.read_text(encoding="utf-8"))):
        assert data["abstained"] is False and data["passages"] and data["config_hash"] and data["experiment_id"].startswith("final-")
        p = data["passages"][0]
        assert DOC_A[p["start"]:p["end"]] == p["text"] and p["rank"] == 1 and isinstance(p["score"], float)


def test_abstained_json_has_empty_passages(env):
    r = run("search", Q, "-c", "strict", "--json")
    d = json.loads(r.output)
    assert r.exit_code == EXIT_ABSTAINED and d["abstained"] and d["passages"] == [] and d["abstention_reason"]


@pytest.mark.parametrize("q", ["", "   "])
def test_empty_question_is_an_input_error(env, q):
    r = run("search", q)
    assert r.exit_code == EXIT_INPUT and "enter a question" in r.output


@pytest.mark.parametrize("k", ["0", "-3", "65"])
def test_bad_k_is_an_input_error(env, k):
    r = run("search", Q, "-k", k)
    assert r.exit_code == EXIT_INPUT and "between 1 and 64" in r.output


def test_overlong_question_is_an_input_error(env):
    assert run("search", "law " * 1000).exit_code == EXIT_INPUT


def test_unknown_or_uncalibrated_config_is_a_missing_resource_error(env):
    r = run("search", Q, "-c", "nope")
    assert r.exit_code == EXIT_MISSING and "unknown configuration" in r.output
    r = run("search", Q, "-c", "uncalibrated")
    assert r.exit_code == EXIT_MISSING and "calibrated" in r.output


def test_missing_data_is_a_clear_error_not_a_traceback(tmp_path, monkeypatch):
    make_app_env(tmp_path, monkeypatch)
    monkeypatch.setenv("CONTRACT_INTEL_DATA_DIR", str(tmp_path / "nothing"))
    r = run("search", Q)
    assert r.exit_code == EXIT_MISSING and "download_data.py" in r.output and "Traceback" not in r.output


def test_unexpected_errors_get_their_own_exit_code(env, monkeypatch):
    from contract_intel.application.service import SearchService
    monkeypatch.setattr(SearchService, "search", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    r = run("search", Q)
    assert r.exit_code == EXIT_RUNTIME and "unexpected RuntimeError: boom" in r.output


def test_configs_lists_selectable_names_only(env):
    r = run("configs")
    assert r.exit_code == 0 and r.output.split() == ["final", "strict", "uncalibrated"]


def test_evaluate_refuses_test_split_without_final_flag_and_confirmation(env):
    r = run("evaluate", "-c", "final", "--split", "test")
    assert r.exit_code == EXIT_INPUT and "may not be used for development" in r.output
    r = run("evaluate", "-c", "final", "--split", "test", "--final")
    assert r.exit_code == EXIT_INPUT and "explicit confirmation" in r.output


def test_help_documents_exit_codes_and_commands():
    r = run("--help")
    assert r.exit_code == 0 and all(c in r.output for c in ("search", "evaluate", "configs"))


def test_test_split_guard_runs_before_any_data_is_touched(tmp_path, monkeypatch):
    """Regression: a fresh clone without data must still get the guard message (exit 2), not a missing-data error (exit 3)."""
    monkeypatch.setenv("CONTRACT_INTEL_DATA_DIR", str(tmp_path / "no-data-here"))
    monkeypatch.setenv("CONTRACT_INTEL_CONFIG_DIR", str(tmp_path / "no-configs-here"))
    r = run("evaluate", "-c", "final", "--split", "test")
    assert r.exit_code == EXIT_INPUT and "may not be used for development" in r.output
    r = run("evaluate", "-c", "final", "--split", "test", "--final")
    assert r.exit_code == EXIT_INPUT and "explicit confirmation" in r.output
