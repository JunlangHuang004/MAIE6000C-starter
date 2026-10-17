# Week 6 verification record

Date: 2026-10-17 (Asia/Hong_Kong). Source base: `5a95caf` plus the Week 6 changes
in this commit. No production service code was changed. Tests executed by the
coding assistant; this record does not assert that each team member ran them.

## Unit/integration and static checks

The current checkout was mounted into the existing development API image so the
new tests were included without changing the running application. Commands below
use `$PWD` for the repository path:

```sh
docker compose run --rm --no-deps -e NUTRITION_PROVIDER=demo -v "$PWD:/app" api pytest tests/integration/test_worker_lifecycle.py -q
docker compose run --rm --no-deps -e NUTRITION_PROVIDER=demo -v "$PWD:/app" api pytest -q -m 'not smoke'
docker compose run --rm --no-deps -v "$PWD:/app" api ruff check services tests alembic scripts/import_usda.py scripts/check_qwen.py scripts/check_dialogue.py
```

Recorded results:

```text
New lifecycle tests: 6 passed, 2 warnings in 0.38s
Full non-smoke suite: 65 passed, 2 deselected, 2 warnings in 1.59s
Ruff: All checks passed!
```

The six new cases cover claim metadata/no reclaim, successful processing, timeout,
HTTP 503, malformed result and repeated POST without idempotency. The failure
cases execute the actual worker loop with a fake HTTP processor boundary and stop
at the next polling sleep. They assert durable state and API-visible results.
SQLite does not validate PostgreSQL row-lock behavior under concurrent workers.

## Live local stack

The observation used a separate Compose project with the demo provider, no host
ports and no model credentials. API/AI images were freshly built from the checkout.
The worker reused the built API image under the worker image tag; all three services
use the same Dockerfile and different startup commands. A clean reproduction can
build all three images with the command in the [workflow guide](../async-workflow.md).

[Lifecycle evidence](week06-worker-lifecycle.json) preserves HTTP responses,
selected PostgreSQL columns and worker log events. Provider inference was local
and deterministic; no claim of real-Qwen validation is made for this Week 6 run.

```sh
docker compose -p nutrichat-week06 --env-file .env.example -f compose.yaml -f compose.week06.yaml exec -T -e SMOKE_BASE_URL=http://api:8000 api pytest tests/smoke -q
```

Result: **2 passed, 2 warnings in 5.77s**. Both starter-case and nutrition
review/correction/confirmation smoke paths completed. These tests added synthetic
records beyond the two initial observation jobs.

The warnings concern deprecated Starlette/AnyIO and python-json-logger interfaces;
they did not fail the tests. The isolated stack is stopped after verification and
its database volume is retained. Existing local and cloud application stacks were
not stopped or redeployed.

## Scope limits

No concurrent-worker exclusion test, live crash/recovery test, model training,
production deployment or user-account isolation was added. Claimed-job recovery,
idempotency and a stable public failure-code taxonomy remain documented gaps.
Team role assignments and the AI Use Statement remain pending before submission.
