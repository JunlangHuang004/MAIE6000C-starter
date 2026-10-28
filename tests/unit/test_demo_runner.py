"""Failure recovery and isolation tests for the TA's local demo launcher."""
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def runner():
    source = Path(__file__).resolve().parents[2] / "demo" / "run.py"
    spec = importlib.util.spec_from_file_location("demo_runner", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("port", ["", "0", "1023", "65536", "8002;echo", "eight", "８００２"])
def test_invalid_port_rejected(runner, monkeypatch, port):
    monkeypatch.setenv("NUTRICHAT_DEMO_PORT", port)
    with pytest.raises(runner.DemoError):
        runner.demo_port()


def test_port_default_and_override(runner, monkeypatch):
    monkeypatch.delenv("NUTRICHAT_DEMO_PORT", raising=False)
    assert runner.demo_port() == 8002
    monkeypatch.setenv("NUTRICHAT_DEMO_PORT", "8003")
    assert runner.demo_port() == 8003


@pytest.mark.parametrize("branch", ["test", "main", "other"])
def test_wrong_branch_rejected(runner, branch):
    with pytest.raises(runner.DemoError, match="nutrichat branch"):
        runner.guard_source({"branch": branch})


@pytest.mark.parametrize("branch", ["nutrichat", "detached", None])
def test_reproducible_checkout_or_zip_allowed(runner, branch):
    runner.guard_source({"branch": branch})


def test_invocation_uses_checkout_root_without_shell(runner, monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout="ok")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    assert runner.run(["docker", "compose", "version"]) == "ok"
    assert calls[0][1]["cwd"] == runner.ROOT
    assert "shell" not in calls[0][1]
    assert calls[0][1]["check"] is True


def test_failed_command_does_not_echo_credentials(runner, monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ["docker"], stderr="secret-test-value")

    monkeypatch.setattr(runner.subprocess, "run", fail)
    with pytest.raises(runner.DemoError) as raised:
        runner.run(["docker"])
    assert "secret-test-value" not in str(raised.value)


def test_failed_check_restores_worker_and_writes_evidence(runner, monkeypatch, tmp_path):
    output = tmp_path / "check.json"
    calls = []
    monkeypatch.setattr(runner, "OUTPUT", output)
    monkeypatch.setattr(runner, "source_metadata", lambda: {"branch": "nutrichat"})
    monkeypatch.setattr(runner, "verify_stack", lambda: {"provider": "demo"})
    monkeypatch.setattr(runner, "ai_requests", lambda: 0)
    monkeypatch.setattr(runner, "run", lambda args: calls.append(args))

    def fail_create(*args, **kwargs):
        raise runner.DemoError("synthetic failure")

    monkeypatch.setattr(runner, "request", fail_create)
    with pytest.raises(runner.DemoError, match="queued persistence"):
        runner.check()
    assert calls == [runner.COMPOSE + ["stop", "worker"],
                     runner.COMPOSE + ["start", "worker"]]
    result = json.loads(output.read_text())
    assert result["passed"] is False
    assert result["worker_restored"] is True
    assert result["failure"] == "queued persistence: synthetic failure"


def test_preflight_failure_does_not_touch_worker(runner, monkeypatch, tmp_path):
    output = tmp_path / "check.json"
    monkeypatch.setattr(runner, "OUTPUT", output)
    monkeypatch.setattr(runner, "source_metadata", lambda: {"branch": "test"})

    def unexpected_command(*args, **kwargs):
        pytest.fail("Wrong-branch preflight must not run Docker commands")

    monkeypatch.setattr(runner, "run", unexpected_command)
    with pytest.raises(runner.DemoError, match="preflight"):
        runner.check()
    assert json.loads(output.read_text())["passed"] is False


def test_stop_preserves_volume_and_only_targets_demo(runner, monkeypatch):
    calls = []
    monkeypatch.delenv("NUTRICHAT_DEMO_PORT", raising=False)
    monkeypatch.setattr(runner, "run", lambda args, **kwargs: calls.append(args))
    assert runner.main(["stop"]) == 0
    assert calls == [runner.COMPOSE + ["stop", "db", "ai", "api", "worker"]]
    assert runner.COMPOSE[runner.COMPOSE.index("-p") + 1] == "nutrichat-demo"
    assert "--env-file" in runner.COMPOSE and ".env.example" in runner.COMPOSE


def test_poll_fails_on_failed_job_instead_of_waiting(runner, monkeypatch):
    monkeypatch.setattr(runner, "request", lambda *args: {"body": {"status": "failed"}})
    with pytest.raises(runner.DemoError, match="unexpected state: failed"):
        runner.completed("/analyses/synthetic")


def test_poll_timeout_is_actionable(runner, monkeypatch):
    monkeypatch.setattr(runner, "request", lambda *args: {"body": {"status": "queued"}})
    with pytest.raises(runner.DemoError, match="Worker did not finish"):
        runner.completed("/analyses/synthetic", timeout=0)


def test_expected_totals_cover_all_four_nutrients(runner):
    runner.verify_totals({"body": {
        "calories": 310, "protein_g": 26, "fat_g": 22, "carbs_g": 2.2,
    }}, 2)
    with pytest.raises(runner.DemoError, match="carbs_g"):
        runner.verify_totals({"body": {
            "calories": 310, "protein_g": 26, "fat_g": 22, "carbs_g": 0,
        }}, 2)


def test_unexpected_account_stack_is_rejected_before_writes(runner, monkeypatch):
    monkeypatch.setattr(runner, "run", lambda args: "True")
    responses = {
        "/health/ready": {"service": "api", "status": "ok"},
        "/foods": {"provider": "demo"},
        "/openapi.json": {"paths": {
            "/analyses/{analysis_id}/confirm": {}, "/auth/me": {},
        }},
    }
    monkeypatch.setattr(runner, "request", lambda method, path: {"body": responses[path]})
    with pytest.raises(runner.DemoError, match="Unexpected account/personalization"):
        runner.verify_stack()


@pytest.fixture
def db_http_pair():
    row = {
        "analysis_id": "synthetic", "analysis_status": "confirmed", "revision": 3,
        "calories": 310, "protein_g": 26, "fat_g": 22, "carbs_g": 2.2,
        "confirmed_at": "2026-10-28T03:00:01.123456+00:00",
    }
    body = {"id": "synthetic", "status": "confirmed", "revision": 3,
            "calories": 310, "protein_g": 26, "fat_g": 22, "carbs_g": 2.2,
            "confirmed_at": "2026-10-28T03:00:01.123456Z"}
    return row, {"body": body}


def test_database_result_accepts_equivalent_timestamp_format(runner, db_http_pair):
    runner.verify_database_result(*db_http_pair)


@pytest.mark.parametrize("field,value", [
    ("analysis_id", "another-meal"), ("analysis_status", "completed"), ("revision", 2),
    ("calories", None), ("protein_g", 27), ("fat_g", 0), ("carbs_g", 0),
    ("confirmed_at", None), ("confirmed_at", "2026-10-28T03:00:02.123456+00:00"),
])
def test_database_result_rejects_any_disagreement(runner, db_http_pair, field, value):
    row, response = db_http_pair
    row[field] = value
    with pytest.raises(runner.DemoError, match="disagrees"):
        runner.verify_database_result(row, response)


def test_unconfirmed_database_result_has_no_confirmation(runner, db_http_pair):
    row, response = db_http_pair
    row["analysis_status"] = response["body"]["status"] = "completed"
    row["confirmed_at"] = response["body"]["confirmed_at"] = None
    runner.verify_database_result(row, response)
