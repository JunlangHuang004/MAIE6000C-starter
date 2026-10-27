# Week 7 verification record

Date: **2026-10-27 (Asia/Hong_Kong)**. Checks were executed by the coding assistant.
This is not an assertion of independent testing by every team member.

Source base: `7754ef41e51a3de61c09c78a7cbb7bed6a3870fe`, plus the milestone
configuration, documentation and host rehearsal script in this commit. Application
service files did not change. SHA-256 checks of all service `.py`, `.json` and
`.html` files matched the checkout, local Qwen API image and freshly built isolated
API image. The aggregate digest is included in the lifecycle JSON.

## CI failure reproduced and repaired

The previous GitHub run failed during collection with
`ModuleNotFoundError: No module named 'scripts'` in `test_expanded_catalogue.py`.
The same failure was reproduced locally with the `pytest` console entry point.
Adding `pythonpath = ["."]` to pytest configuration makes repository script imports
consistent with `python -m pytest`. The existing workflow runs on `main` pushes
and pull requests. The fork mirrors the same commit on `nutrichat`, which does not
trigger a push workflow; use the original repository's CI for this shared commit.
An optional workflow-trigger edit was withdrawn because the existing Git token
does not permit workflow modifications. No extra credential permissions were requested.

After the fix, the console-entry suite passed: **359 passed, 2 warnings in 2.71s**.
Ruff across the entire checkout, including the new rehearsal script: **All checks passed**.

Commands (from the repository root; image contains development dependencies):

```sh
docker run --rm --network none -e NUTRITION_PROVIDER=demo -e DASHSCOPE_API_KEY= --mount "type=bind,source=$PWD,target=/app,readonly" --entrypoint pytest maie-6000c-starter-junlang-huang-ai -q -p no:cacheprovider tests/unit tests/integration
docker run --rm --network none --mount "type=bind,source=$PWD,target=/app,readonly" --entrypoint ruff nutrichat-week07-api check --no-cache .
```

CI itself installs dependencies, runs Ruff, migrates PostgreSQL and runs
`pytest -q tests/unit tests/integration`. Its final status is available in GitHub
Actions for the tagged commit; local success alone is not a claim of remote success.

## Fresh PostgreSQL and worker rehearsal

Built all three application images from the current checkout, then used project
`nutrichat-week07` with the existing offline/no-host-port overlay. The new database
migrated through `20261017_0005` (head). See the [demo guide](../../submissions/week07/DEMO.md)
for setup and a step-by-step live sequence.

```sh
python3 scripts/rehearse_midterm.py --output docs/evidence/week07-worker-lifecycle.json
docker compose -p nutrichat-week07 --env-file .env.example -f compose.yaml -f compose.week06.yaml exec -T -e SMOKE_BASE_URL=http://api:8000 api pytest tests/smoke -q
```

Recorded outcomes:

- HTTP 201 created a synthetic `100g egg` analysis and pending job while the worker
  was stopped. Direct PostgreSQL reads showed queued/pending state and null totals.
- Starting the worker produced matching `job_claimed` and `job_completed` events,
  attempt count 1, and saved claim/completion timestamps.
- HTTP and PostgreSQL agreed on 155 kcal, 13 g protein, 11 g fat and 1.1 g carbs
  using the **legacy demo catalogue**, not a Qwen/USDA result.
- Confirmation persisted; GET returned the confirmed record; a subsequent PATCH
  returned HTTP 409. API readiness returned HTTP 200.
- Both smoke tests passed: **2 passed, 2 warnings in 5.87s**, covering the legacy
  case path and nutrition correction/recalculation/confirmation path.

[Machine-readable lifecycle evidence](week07-worker-lifecycle.json) contains only
synthetic data. The isolated stack was stopped after validation without deleting
its volume. The normal local stack and public ECS were not redeployed.

## Real Qwen check — separate observation

The existing local Qwen stack ran the complete opt-in expanded dialogue check:

```sh
docker compose exec -T api python scripts/check_expanded_dialogue.py --base-url http://api:8000 --live
```

It exited successfully with both messages:

```text
PASS: new dishes, piece weights, mode switch, recipe edits, natural-language correction, save, reload and confirmation lock
PASS: basic gross-weight estimate stays labelled; advanced asks for net grams
```

This run exercised Chinese dumplings/beef, count-to-weight assumptions, advanced
recipe approval, natural-language corrections and persistence. It also retained
200 g gross rib weight while using a labelled 120 g edible-weight approximation
in basic mode, then requested net grams in advanced mode with no totals.

This is one successful synthetic run, not a measured reliability rate. Earlier
intermittent provider failures remain documented in the change log. This check
uses model quota and creates saved synthetic meals; it is not an offline test.

## Limits

- Unit/integration tests use SQLite and fake provider boundaries; they do not
  establish real-model correctness or PostgreSQL concurrency behavior.
- The live rehearsal uses a single worker. No crash injection, automatic retry,
  idempotency or claimed-job recovery was added.
- Catalogue coverage tests do not establish ground-truth calorie accuracy.
- Two dependency deprecation warnings concern Starlette/AnyIO and python-json-logger.
- No public ECS upgrade or independent team rehearsal is claimed in this record.
- Canvas submission remains pending the user's confirmation.
