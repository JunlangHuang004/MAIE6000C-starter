# NutriChat operations

Current instructions reviewed: 2026-10-31, `nutrichat` branch.

## Self-guided TA demo on the nutrichat branch

Use [the demo setup guide](../demo/README.md) and
[six-step screenshot guide](../demo/SCREENSHOT_GUIDE.md) for the Chinese workflow
and English-interface example. The Qwen project uses port 8003 and a private
server configuration:

```sh
docker compose -p nutrichat-qwen-demo --env-file .env -f compose.yaml -f demo/compose.qwen.yaml up -d --build --wait db ai api worker
```

Open `http://localhost:8003/app` directly. Individual registration/login and
per-user record isolation are not implemented in this local application. Its
visible **Log out** button has no local authentication function. The optional
public shared-password gateway is implemented separately and is not started by
this demo command.
Choose **中文 / English** in the header. The browser remembers the selection;
switching preserves unsent form values and does not call Qwen or alter nutrients.
User descriptions and free-form model notes retain their original language.
For an optional integration check without Qwen credentials:

```sh
python3 demo/run.py start
python3 demo/run.py check
python3 demo/run.py status
python3 demo/run.py stop
```

The offline project uses port 8002, its own database and six English food keys.
Its check briefly pauses only its worker; let it finish before submitting other
meals there. Both demo projects bind only to loopback, keep their own database
volumes and do not publish database/AI ports. Stopping retains data. Use the same
project and overlays when resuming; see the setup guide for Qwen stop commands.

[The 28 October verification](../demo/VERIFICATION.md) records 408 passing automated
tests, 14 of 17 passing live food/weight checks, three generic invalid-weight
failures and a transient dialogue failure followed by a successful rerun. These
are observations from 28 October 2026, not a claim of universal provider success.

[The 31 October language verification](evidence/ui-language-verification.md)
records **417 passing Python tests, 15 passing frontend tests and Ruff**, plus a
live Qwen browser flow that preserved edited recipe answers across both languages
and restored the confirmed meal after reload. These counts belong to that
language-update checkpoint, not the current expanded catalogue. A fresh offline
Docker rebuild at that point also
passed the durable workflow check and both smoke tests. Neither run proves that every live
model interpretation or reference-recipe estimate is correct.

The subsequent [ingredient-builder verification](evidence/ingredient-recipe-verification.md)
records 545 Python tests and 26 DOM tests on `7c841b1`, plus an HTTP/worker/database
calculation check. For the 200-ingredient/350-recipe release, use the
[expansion verification](evidence/chinese-expansion-verification.md) and inspect
the GitHub Actions run for the exact pushed commit. Test totals from successive
versions are not added together. The public ECS deployment remains separate.

The edible-state matching follow-up `dae0b94` passes 664 Python tests and Ruff;
it changes no frontend assets or catalogue data. The 26 DOM checks and rebuilt
offline workflow were executed on the initial expanded source `71a0ecd`. Keep
those source attributions when reviewing a later live matching retest; readiness
alone does not establish that the previously rejected input now works.

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
docker compose run --rm --no-deps api ruff check .
```

The interface tests need Node.js (CI uses version 22). From the repository root:

```sh
npm ci --prefix tests/frontend
npm test --prefix tests/frontend
```

These are development-only dependencies; the running application serves plain
JavaScript and does not need Node or an npm build. The tests check translations,
catalogue coverage, safe rendering, draft preservation and absence of new requests
when changing language. For a browser check, enter a synthetic meal, edit an
issued recipe question, switch languages, and verify the entries remain before
submitting. After confirmation/reload, verify the same record and totals return.
This live path uses Qwen quota; the DOM tests do not.

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
docker compose exec -T api python scripts/check_expanded_dialogue.py --base-url http://api:8000 --live
```

The first command checks configuration only. Live checks consume model quota; the dialogue script creates synthetic saved records. Mocked tests cannot establish model account access. Recorded results are in the [change log](change-log.md).

## Diagnose processing

- “No corresponding food record”: this is an unsupported or unverified identity,
  not permission to use the nearest dish. Coverage is limited to 200 ingredients,
  350 reference recipes and recorded names/aliases. Check the catalogue, correct
  the food name, or use the structured form to select actual supported ingredients
  and gram weights. Keep
  nutrient totals empty while any food is unresolved; do not describe this as a
  provider outage unless there is separate failure evidence.

- `needs_input`: normal clarification. Answer the issued questions; the worker job has completed successfully.
- `failed`: inspect the bounded operational `Job.error`, service logs and user-facing `Analysis.error_message`. Check endpoint region/workspace, model access, structured response and timeouts. Correct or resubmit the meal after resolving the cause.
- The **Build from actual ingredients** form is an explicit repair path for one
  unresolved food. It requires catalogue ingredient selections and reviewed grams;
  it does not infer a recipe or use Qwen. Check consumed versus whole-batch basis
  and follow the [ingredient guide](ingredient-recipes.md). If a meal contains a
  custom recipe, edit that form rather than using free-text replies. A 409 keeps
  unsent values visible but requires reloading the latest record before resubmission.
- Long-lived `queued`: check worker health, database access and whether the job is `pending` or `claimed`. Interrupted claimed jobs have no automatic recovery. Inspect before resubmitting as a new analysis; repeated submissions create separate records.
- 409 on edit/confirm: reload the latest revision and state. Queued or confirmed records cannot be edited.
- Public login redirects: verify the HTTPS origin, signed session cookie and gateway configuration; sessions last eight hours. The implemented gateway uses a shared credential, not individual accounts. Local Compose does not use this gateway and has no working `/login` or `/logout` authentication routes.
- Missing language buttons or untranslated static controls after an update: rebuild/restart the API from the intended checkout and reload `/app`. Confirm `/app-assets/catalogue-en.js`, `/app-assets/i18n.js` and `/app-assets/app.js` return JavaScript successfully. These routes allow only the named assets; do not replace them with a general filesystem-serving route.
- Language resets after reload: the preference uses browser localStorage. Blocked/unavailable storage permits switching for the current page only. A language selection is not an account preference and does not translate original meal text or free-form model notes.

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

## Week 7 milestone rehearsal

Use the [demo guide](../submissions/week07/DEMO.md) and
`scripts/rehearse_midterm.py` with the dedicated `nutrichat-week07` project. The
existing Week 6 overlay is reusable; its project name determines isolation. The
script creates synthetic records and stops/starts only that project's worker.
Build the checkout first and keep the regular Qwen stack separate. Recorded
results and limits are in [Week 7 verification](evidence/week07-verification.md).

CI runs on `main` and `nutrichat` pushes and on pull requests. Its Python job runs
Ruff, PostgreSQL migrations and `pytest -q tests/unit tests/integration`; its
separate Node job installs the locked frontend dependencies and runs the frontend
DOM suite. Local passing checks do not imply a successful GitHub Actions run: inspect
the run for the actual pushed commit. Pytest includes the repository root so
script imports work with both the console and module entry points.

The required submission tag is `w07-midterm`. Before reporting its SHA, resolve
the tag's commit (`git rev-parse 'w07-midterm^{commit}'`) and compare it with the
remote tag and the intended submission files. Branch HEAD and a published tag can
refer to different versions; do not present later branch evidence as a check of
an older tagged checkout. The [midterm artifact](../submissions/week07/README.md)
identifies the submission scope and supporting evidence.

The public ECS is not updated by a Git push; deployment and rollback require the
separate cloud workflow. The current local Qwen demo uses port 8003. Do not present
the older public build as the current branch or Week 7 tag.
