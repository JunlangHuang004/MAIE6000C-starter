# NutriChat operations

## Local startup and configuration

Run from the repository root with Docker and Docker Compose installed:

```sh
test -f .env || cp .env.example .env
docker compose up -d --build
docker compose ps
```

Open [the local application](http://localhost:8000/app). Demo provider accepts supported English food names and explicit grams. Configure Qwen for Chinese descriptions, recipes and the full two-mode workflow; see [cloud deployment](cloud-deployment.md). Keep the existing `.env` when upgrading.

`.env.example` uses Qwen timeout 12 seconds and worker HTTP timeout 20 seconds. For local multi-turn Qwen testing, 30 and 45 seconds respectively match the cloud configuration. The worker timeout must exceed the Qwen timeout. `compose.cloud.yaml` explicitly sets 30/45; changing `.env` alone does not override these cloud values.

## Health, logs and metrics

| Check | What it establishes |
| --- | --- |
| API `/health/live` | API process responds |
| API `/health/ready` | API can execute a PostgreSQL query |
| AI `/health/live`, `/health/ready` | AI process responds; neither verifies Qwen credentials |
| API / AI `/metrics` | Internal service metrics; public proxy blocks `/metrics` |

```sh
docker compose logs --tail=100 api worker ai
docker compose --profile observability up -d prometheus
```

Inspect logs locally; redact secrets and private meal descriptions before sharing. Prometheus is available on development port 9090 when its profile is enabled.

## Verification

After building the current source:

```sh
docker compose run --rm --no-deps -e NUTRITION_PROVIDER=demo api pytest -q -m 'not smoke'
docker compose run --rm --no-deps api ruff check services tests alembic scripts/import_usda.py scripts/check_qwen.py scripts/check_dialogue.py
```

The legacy smoke tests assert demo-catalogue values. Run them only against a stack
started with `NUTRITION_PROVIDER=demo` consistently for API and AI. They create saved
records. With that stack running, they can reach the API from inside Compose:

```sh
docker compose exec -T -e SMOKE_BASE_URL=http://api:8000 api pytest tests/smoke -q
```

Configuration and live-provider checks:

```sh
docker compose run --rm --no-deps api python scripts/check_qwen.py
docker compose run --rm --no-deps api python scripts/check_qwen.py --live
docker compose exec -T api python scripts/check_dialogue.py --base-url http://api:8000
```

The first command checks configuration only. Live checks consume model quota; the dialogue script creates synthetic saved records. Mocked tests cannot establish model account access. Recorded results are in the [change log](change-log.md).

## Diagnose processing

- `needs_input`: normal clarification. Answer the issued questions; the worker job has completed successfully.
- `failed`: inspect the bounded operational `Job.error`, service logs and user-facing `Analysis.error_message`. Check endpoint region/workspace, model access, structured response and timeouts. Correct or resubmit the meal after resolving the cause.
- Long-lived `queued`: check worker health, database access and whether the job is `pending` or `claimed`. Interrupted claimed jobs have no automatic recovery. Inspect before resubmitting as a new analysis; repeated submissions create separate records.
- 409 on edit/confirm: reload the latest revision and state. Queued or confirmed records cannot be edited.
- Login redirects: verify the HTTPS origin, signed session cookie and gateway configuration; sessions last eight hours. Local Compose does not use the public login gateway.

## Updates, data and recovery

API startup runs `alembic upgrade head`. Before upgrading, back up the database and preserve previous code/images. Stop accepting new work and allow active jobs to finish before stopping the worker. Do not delete volumes as part of routine deployment. For cloud upgrades use the matching standalone Compose files throughout, as described in [cloud deployment](cloud-deployment.md).

Stop the local stack while retaining data:

```sh
docker compose down
```

`docker compose down -v` deletes the local database volume and is only for an intentional data reset. Cloud and local Compose use different database volumes. Restoring an older image alone does not revert a migration; recovery requires compatible code/schema or a tested database backup.

## Week 6 isolated worker lab

Use [the asynchronous workflow guide](async-workflow.md) for the stopped-worker
observation, state ownership, reproduction commands and saved evidence. The
`compose.week06.yaml` overlay is for a dedicated `nutrichat-week06` Compose project:
it uses the demo provider, `.env.example`, no model credentials and no published
host ports. It does not replace the running local or public configuration.

Run the lab smoke tests only against this demo stack. Shut it down with the same
project name and both Compose files; omit `-v` to keep the lab database. Current
results and verification limits are in [the Week 6 verification record](evidence/week06-verification.md).
