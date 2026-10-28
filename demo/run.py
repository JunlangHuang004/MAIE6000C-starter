"""Start and verify the isolated, key-free NutriChat TA demo.

Host requirements: Python 3.10+ and Docker Compose 2.24.4+ with Docker running.
The application and verification HTTP client run inside Docker, not host Python.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "demo" / "output" / "check.json"
PROJECT = "nutrichat-demo"
SERVICES = ["db", "ai", "api", "worker"]
COMPOSE = [
    "docker", "compose", "-p", PROJECT, "--env-file", ".env.example",
    "-f", "compose.yaml", "-f", "demo/compose.demo.yaml",
]
HTTP = """import json,sys,urllib.request,urllib.error
method,path,payload = sys.argv[1:]
request = urllib.request.Request('http://api:8000'+path, method=method,
    data=payload.encode() if payload else None,
    headers={'Content-Type':'application/json'})
try:
    response = urllib.request.urlopen(request, timeout=10)
except urllib.error.HTTPError as error:
    response = error
with response:
    content = response.read().decode('utf-8')
try:
    body = json.loads(content)
except ValueError:
    body = content
print(json.dumps({'status':response.status,'body':body}))
"""


class DemoError(RuntimeError):
    """A failed prerequisite or demo verification step."""


def run(args, timeout=90, stream=False):
    """Run from the checkout root even when invoked from another directory."""
    try:
        result = subprocess.run(
            args, cwd=ROOT, text=True, check=True, timeout=timeout,
            stdout=None if stream else subprocess.PIPE,
            stderr=None if stream else subprocess.PIPE,
        )
    except FileNotFoundError as error:
        raise DemoError(f"Required command not found: {args[0]}") from error
    except subprocess.TimeoutExpired as error:
        raise DemoError(f"Command timed out after {timeout}s: {args[0]}") from error
    except subprocess.CalledProcessError as error:
        # Do not print arbitrary container logs, environment variables or credentials.
        raise DemoError(
            f"{args[0]} command failed (exit {error.returncode}). "
            "Check Docker is running, the demo is started, and the selected port is free."
        ) from error
    return result.stdout or ""


def require(condition, message):
    if not condition:
        raise DemoError(message)


def demo_port():
    value = os.getenv("NUTRICHAT_DEMO_PORT", "8002")
    require(value.isascii() and value.isdigit(), "NUTRICHAT_DEMO_PORT must be an integer.")
    port = int(value)
    require(1024 <= port <= 65535, "NUTRICHAT_DEMO_PORT must be between 1024 and 65535.")
    return port


def source_metadata():
    try:
        commit = run(["git", "rev-parse", "HEAD"]).strip()
        branch = run(["git", "branch", "--show-current"]).strip()
        dirty = bool(run(["git", "status", "--porcelain"]).strip())
        return {"commit": commit, "branch": branch or "detached", "dirty": dirty}
    except DemoError:
        return {"commit": None, "branch": None, "dirty": None,
                "note": "Git metadata unavailable (for example, a ZIP download)."}


def guard_source(source):
    require(
        source["branch"] in (None, "detached", "nutrichat"),
        "Use the nutrichat branch for this demo; the current checkout is another branch.",
    )


def request(method, path, payload=None, status=200):
    result = json.loads(run(COMPOSE + [
        "exec", "-T", "api", "python", "-c", HTTP, method, path,
        json.dumps(payload) if payload is not None else "",
    ]))
    require(result["status"] == status,
            f"{method} {path}: expected HTTP {status}, received {result['status']}.")
    return result


def verify_stack():
    for service in ("api", "ai", "worker"):
        safe = run(COMPOSE + [
            "exec", "-T", service, "python", "-c",
            "import os; print(os.environ.get('NUTRITION_PROVIDER') == 'demo' "
            "and not os.environ.get('DASHSCOPE_API_KEY') "
            "and not os.environ.get('QWEN_BASE_URL'))",
        ]).strip()
        require(safe == "True", f"{service} is not configured as the key-free demo stack.")
    health = request("GET", "/health/ready")
    require(health["body"] == {"service": "api", "status": "ok"},
            "API/PostgreSQL readiness did not pass.")
    foods = request("GET", "/foods")["body"]
    require(foods.get("provider") == "demo", "This check requires the key-free demo provider.")
    paths = request("GET", "/openapi.json")["body"].get("paths", {})
    require("/analyses/{analysis_id}/confirm" in paths, "Meal confirmation route is missing.")
    require(not any(path.startswith(("/auth/", "/profile", "/tracking")) for path in paths),
            "Unexpected account/personalization routes: rebuild from the nutrichat branch.")
    page = request("GET", "/app")["body"]
    require(isinstance(page, str) and "NutriChat" in page, "The meal UI was not served.")
    return {"health": health, "provider": foods["provider"],
            "supported_demo_foods": foods["foods"], "app_http_status": 200}


def database(job_id):
    query = (
        "SELECT row_to_json(t) FROM (SELECT j.id AS job_id,j.status AS job_status,"
        "j.attempts,j.claimed_at,j.completed_at,a.id AS analysis_id,"
        "a.status AS analysis_status,a.revision,a.calories,a.protein_g,a.fat_g,"
        "a.carbs_g,a.confirmed_at FROM jobs j JOIN analyses a ON a.id=j.analysis_id "
        f"WHERE j.id={int(job_id)}) t;"
    )
    return json.loads(run(COMPOSE + [
        "exec", "-T", "db", "psql", "-U", "postgres", "-d", "maie6000c", "-Atc", query,
    ]))


def ai_requests():
    script = (
        "import urllib.request; "
        "lines=urllib.request.urlopen('http://ai:8100/metrics',timeout=10)"
        ".read().decode().splitlines(); "
        "print(next(float(line.split()[1]) for line in lines "
        "if line.startswith('ai_nutrition_analysis_requests_total ')))"
    )
    return float(run(COMPOSE + ["exec", "-T", "api", "python", "-c", script]).strip())


def completed(path, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = request("GET", path)
        state = result["body"]["status"]
        if state == "completed":
            return result
        require(state == "queued", f"Meal entered unexpected state: {state}.")
        time.sleep(0.5)
    raise DemoError(f"Worker did not finish within {timeout}s. Inspect the dedicated demo worker.")


def verify_totals(result, multiplier):
    expected = {"calories": 155, "protein_g": 13, "fat_g": 11, "carbs_g": 1.1}
    for nutrient, per_100g in expected.items():
        require(result["body"].get(nutrient) == round(per_100g * multiplier, 1),
                f"Unexpected {nutrient} for the synthetic egg fixture.")


def verify_job(row):
    require(row["job_status"] == "completed", "Job did not persist completed status.")
    require(row["attempts"] == 1, "Expected exactly one worker claim.")
    require(row["claimed_at"] and row["completed_at"], "Job timestamps were not persisted.")


def verify_database_result(row, result):
    body = result["body"]
    for stored, returned in (("analysis_id", "id"), ("analysis_status", "status"),
                             ("revision", "revision"), ("calories", "calories"),
                             ("protein_g", "protein_g"), ("fat_g", "fat_g"),
                             ("carbs_g", "carbs_g")):
        require(row.get(stored) == body.get(returned),
                f"Database {stored} disagrees with the HTTP response.")
    stored_at, returned_at = row.get("confirmed_at"), body.get("confirmed_at")
    if stored_at is None or returned_at is None:
        require(stored_at == returned_at,
                "Database confirmation timestamp disagrees with the HTTP response.")
    else:
        # PostgreSQL and Pydantic can format the same UTC timestamp differently.
        stored_time = datetime.fromisoformat(stored_at.replace("Z", "+00:00"))
        returned_time = datetime.fromisoformat(returned_at.replace("Z", "+00:00"))
        require(stored_time == returned_time,
                "Database confirmation timestamp disagrees with the HTTP response.")


def worker_events(job_ids, since):
    events = []
    output = run(COMPOSE + ["logs", "--since", since, "--no-color", "--no-log-prefix", "worker"])
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("job_id") in job_ids:
            # Store only lifecycle metadata, never arbitrary log bodies or exceptions.
            events.append({key: event[key] for key in
                           ("asctime", "service", "message", "job_id", "analysis_id")
                           if key in event})
    for job_id in job_ids:
        messages = {event.get("message") for event in events if event.get("job_id") == job_id}
        require({"job_claimed", "job_completed"} <= messages,
                f"Matching claim/completion log entries were missing for job {job_id}.")
    return events


def check():
    started_at = datetime.now(timezone.utc).isoformat()
    evidence = {
        "observed_at": started_at, "project": PROJECT, "passed": False,
        "source": source_metadata(),
        "scope": "Synthetic API -> PostgreSQL -> worker -> internal HTTP; offline demo provider. "
                 "Not a browser automation or live Qwen test.",
    }
    stage = "preflight"
    restore_worker = False
    failure = None
    try:
        guard_source(evidence["source"])
        evidence["stack"] = verify_stack()
        evidence["ai_requests_before"] = ai_requests()
        stage = "queued persistence"
        restore_worker = True
        run(COMPOSE + ["stop", "worker"])
        created = request("POST", "/analyses", {"food_text": "100g egg"}, status=201)
        evidence["created"] = created
        meal_id = created["body"]["analysis"]["id"]
        job_id = created["body"]["job"]["id"]
        path = "/analyses/" + meal_id
        evidence["before_worker"] = database(job_id)
        require(evidence["before_worker"]["analysis_status"] == "queued",
                "Analysis was not persisted as queued while the worker was stopped.")
        require(evidence["before_worker"]["job_status"] == "pending",
                "Job was not persisted as pending while the worker was stopped.")
        require(evidence["before_worker"]["attempts"] == 0,
                "The stopped worker must not claim the new pending job.")
        require(all(evidence["before_worker"][name] is None
                    for name in ("calories", "protein_g", "fat_g", "carbs_g")),
                "Queued meal must not contain nutrition results before worker execution.")
        run(COMPOSE + ["start", "worker"])
        restore_worker = False
        stage = "initial completion"
        evidence["initial_result"] = completed(path)
        verify_totals(evidence["initial_result"], 1)
        evidence["initial_job"] = database(job_id)
        verify_job(evidence["initial_job"])
        verify_database_result(evidence["initial_job"], evidence["initial_result"])
        stage = "review correction"
        corrected = request("PATCH", path, {
            "food_text": "200g egg", "revision": evidence["initial_result"]["body"]["revision"],
        })
        evidence["correction"] = corrected
        correction_job_id = corrected["body"]["job"]["id"]
        require(correction_job_id != job_id, "Correction did not create a new durable job.")
        evidence["corrected_result"] = completed(path)
        verify_totals(evidence["corrected_result"], 2)
        evidence["correction_job"] = database(correction_job_id)
        verify_job(evidence["correction_job"])
        verify_database_result(evidence["correction_job"], evidence["corrected_result"])
        stage = "confirmation and reload"
        confirmed = request("POST", path + "/confirm", {
            "revision": evidence["corrected_result"]["body"]["revision"],
        })
        evidence["confirmed"] = confirmed
        require(confirmed["body"]["status"] == "confirmed", "Meal confirmation did not persist.")
        require(confirmed["body"]["confirmed_at"], "Confirmation timestamp is missing.")
        evidence["reloaded"] = request("GET", path)
        require(evidence["reloaded"] == confirmed, "Reloaded meal differs from saved confirmation.")
        evidence["after_confirmation"] = database(correction_job_id)
        require(evidence["after_confirmation"]["analysis_status"] == "confirmed",
                "Database row is not confirmed.")
        verify_database_result(evidence["after_confirmation"], confirmed)
        stage = "locked edit"
        evidence["locked_edit"] = request("PATCH", path, {
            "food_text": "300g egg", "revision": confirmed["body"]["revision"],
        }, status=409)
        require(request("GET", path) == confirmed, "A locked edit changed the confirmed meal.")
        stage = "worker logs"
        evidence["worker_events"] = worker_events([job_id, correction_job_id], started_at)
        stage = "AI HTTP counter"
        evidence["ai_requests_after"] = ai_requests()
        evidence["ai_requests_delta"] = (
            evidence["ai_requests_after"] - evidence["ai_requests_before"]
        )
        require(evidence["ai_requests_delta"] >= 2,
                "Expected at least two successful nutrition requests to the internal AI service.")
        evidence["passed"] = True
    except (DemoError, ValueError, KeyError, TypeError) as error:
        failure = f"{stage}: {error}"
        evidence["failure"] = failure
    except KeyboardInterrupt:
        failure = f"{stage}: interrupted by the user"
        evidence["failure"] = failure
    finally:
        if restore_worker:
            try:
                run(COMPOSE + ["start", "worker"])
                evidence["worker_restored"] = True
            except DemoError as error:
                evidence["worker_restored"] = False
                evidence["restore_error"] = str(error)
                failure = failure or str(error)
        evidence["passed"] = failure is None and evidence["passed"]
        evidence["finished_at"] = datetime.now(timezone.utc).isoformat()
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"Evidence: {OUTPUT}")
    if failure:
        raise DemoError(failure)
    print("PASS: queued DB state, worker completion, 155 -> 310 kcal correction, "
          "confirmation, reload, locked edit, and matching worker logs.")
    print(f"Synthetic meal ID: {meal_id}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["start", "check", "status", "stop"])
    args = parser.parse_args(argv)
    try:
        port = demo_port()
        if args.command == "start":
            guard_source(source_metadata())
            run(COMPOSE + ["up", "--build", "--detach", "--wait", "--wait-timeout", "180"]
                + SERVICES, timeout=900, stream=True)
            verify_stack()
            print(f"Ready: http://localhost:{port}/app (no login or API key required)")
        elif args.command == "check":
            check()
        elif args.command == "status":
            run(COMPOSE + ["ps", "--all"] + SERVICES, stream=True)
            print(f"Demo URL: http://localhost:{port}/app")
        else:
            run(COMPOSE + ["stop"] + SERVICES, stream=True)
            print("Dedicated demo stopped. Database records are retained; run start to resume.")
    except (DemoError, OSError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
