# NutriChat operations

Current instructions: 2026-11-23 follow-up; `w13-final` remains the historical course package. The app separates
Meals, Daily diary, Trends and My goals while retaining meal estimation, daily
balance, intake review and the Chinese-meal evaluator. Existing deployments remain
separate snapshots. See [integration setup](integration.md) and the
[14 November recipe-usability follow-up](qa/reports/2026-11-14-recipe-usability.md).
The [earlier 14 November workspace review](qa/reports/2026-11-14-fresh-review.md)
remains separate dated evidence.

## Startup and isolation

Use Docker and a recent Docker Compose. From this checkout:

```sh
test -f .env || cp .env.example .env
docker compose -p nutrichat-merged-qwen --env-file .env \
  -f compose.yaml -f compose.integrated.yaml up -d --build
docker compose -p nutrichat-merged-qwen --env-file .env \
  -f compose.yaml -f compose.integrated.yaml ps
```

Open <http://localhost:8005/app>. Register/sign in to use private meals, profiles and
tracking. Use `localhost` consistently; browser origins must match
`AUTH_PUBLIC_ORIGIN`. The preview enables registration and HTTP cookies only for
loopback development. Public deployments require HTTPS, Secure cookies and an
explicit public origin.

The merged preview has its own project/volume, hides AI/PostgreSQL ports and gives
private provider configuration only to AI. Preserve `.env`; configure Qwen or HKUST
as described in [integration](integration.md). `LLM_PROVIDER`, when nonempty,
overrides `NUTRITION_PROVIDER`. Provider selection must agree across API/AI/worker.
The worker HTTP timeout must exceed the model timeout. The integrated overlay
defaults to 210 seconds for the worker; a model timeout of 180 seconds fits inside it.

Do not reuse an existing Docker project name from a different checkout. A port
change alone does not isolate services or database volumes. Stop/resume with the
same project and Compose files. This merge does not change the older applications
on ports 8001–8004 or deploy ECS.

## Key-free verification

```sh
python3 demo/run.py start
python3 demo/run.py check
python3 demo/run.py status
python3 demo/run.py stop
```

This defaults to project `nutrichat-integrated-demo`, port 8006 and a separate
PostgreSQL volume. The check authenticates a synthetic account, briefly pauses only
that project's worker, and verifies persisted input, processing, correction,
confirmation and operational signals. Let it finish before submitting other meals
there. For concurrent checkouts set both `NUTRICHAT_DEMO_PROJECT` and
`NUTRICHAT_DEMO_PORT` consistently for all four commands. See [demo setup](../demo/README.md).

The offline provider accepts six legacy English food names with explicit grams.
It does not interpret Chinese or conversational corrections. In the UI use
**Replace full description**; API free-text `/reply` returns 422 without changing
the estimate. `PATCH /analyses/{id}` with a complete supported description enqueues
recalculation. This path demonstrates engineering integration, not model accuracy.

## Health, logs and metrics

| Check | Meaning |
| --- | --- |
| API `/health/live` | API process responds |
| API `/health/ready` | API can query PostgreSQL |
| AI `/health/live`, `/health/ready` | AI process responds; no provider authentication/quota test |
| API/AI `/metrics` | Request/job operational signals; public proxy blocks metrics |

```sh
docker compose -p nutrichat-merged-qwen --env-file .env \
  -f compose.yaml -f compose.integrated.yaml logs --tail=100 api worker ai
```

Inspect logs locally and redact private data before sharing. A healthy container
can still have invalid model credentials. `/jobs/{id}` is restricted to the owning
account and contains bounded operational errors; it is not a substitute for
reviewing sanitized logs.

## Automated and live checks

Build the current source first. Unit/integration tests use isolated test databases
and controlled model responses, with no private model credentials required:

```sh
docker compose -p nutrichat-merged-qwen --env-file .env \
  -f compose.yaml -f compose.integrated.yaml run --rm --no-deps \
  -e LLM_PROVIDER=heuristic -e NUTRITION_PROVIDER=demo api pytest -q -m 'not smoke'
docker compose -p nutrichat-merged-qwen --env-file .env \
  -f compose.yaml -f compose.integrated.yaml run --rm --no-deps api ruff check .
npm ci --prefix tests/frontend
npm test --prefix tests/frontend
```

The fixed synthetic Chinese meal corpus can be validated without model calls:
`python scripts/evaluate_chinese_meals.py`. Optional live Qwen extraction checks
are described in [the evaluation guide](evaluation.md).

Frontend tests use Node.js 22 in CI and synthetic responses. They check bilingual
UI behavior, form preservation and account/diary integration; the application
requires no npm runtime/build step. Validate browser workflows separately.

For workspace acceptance, switch all four panels with unsaved meal, recipe,
profile and diary values, then switch languages. Values must remain intact and
navigation must not submit requests or interrupt meal processing. Check keyboard
navigation and a narrow viewport. Expand per-food evidence, search the catalogue
and use **Show 20 more**; all matching records must remain reachable.

In **Daily diary**, exercise and weight are visible directly; manual calorie totals
and the five-category intake review are disclosures. A manual total replaces meal
aggregation, including when it is zero. Blank exercise is unknown; zero explicitly
records no exercise. Save changes before checking the balance and separate
**Trends** panel. A profile reload after a conflict refreshes dependent saved diary
and trend data while preserving unsaved diary changes.

The smoke tests expect the offline provider's six-food arithmetic and require an
authenticated session. Use the isolated offline project, not a live-model stack:

```sh
docker compose -p nutrichat-integrated-demo --env-file .env.example \
  -f compose.yaml -f demo/compose.demo.yaml exec -T \
  -e SMOKE_BASE_URL=http://api:8000 api pytest tests/smoke -q
```

Smoke tests create synthetic accounts and records when registration is enabled.
For closed registration, provide dedicated smoke-account credentials through the
supported environment variables; never put credentials in tracked files.

Provider checks require the selected provider's valid endpoint, model access and
quota. For Qwen, run `python scripts/check_qwen.py` in the AI container (configuration
only), adding `--live` for a provider request. API and worker containers deliberately
do not receive the private key in the merged preview.

Run `scripts/check_dialogue.py` or `scripts/check_expanded_dialogue.py` against the
API only with Qwen configured and a dedicated registered check account. Set
`NUTRICHAT_CHECK_USERNAME`; the tool prompts securely for the password in a terminal,
or accepts `NUTRICHAT_CHECK_PASSWORD` from the environment for noninteractive use.
The checks authenticate and revoke their session afterwards. They consume quota
and create saved synthetic meals. Do not assume Qwen-specific scripts validate
HKUST or Ollama; use the merged workflow checks described in [integration](integration.md).

## Diagnose problems

- **Connection refused / Docker commands hang:** check Docker Desktop and free disk
  space before restarting the existing project. A local review encountered virtual
  disk write errors when host storage was almost full. Preserve named volumes;
  deleting the database is not a recovery step. Verify readiness and saved records
  after recovery.
- **Login loops / 401:** sign in again after expiry; keep the same host/port and
  check cookie/origin settings. HTTP localhost requires `AUTH_COOKIE_SECURE=false`.
  An old shared public password is not an automatically migrated personal account.
- **403 on writes:** check `X-NutriChat-Request: 1` and exact `Origin` matching.
  Do not remove these checks to make a cross-origin client work.
- **No corresponding food record:** coverage is limited to 202 ingredients and
  384 reference recipes with reviewed names/aliases. Correct the name or select
  actual supported ingredients. Keep all totals empty while any item is unresolved.
- **`needs_input`:** normal clarification, with a successfully completed job.
  Answer the issued questions or use the ingredient builder for an unknown item.
- **`failed`:** inspect the owned job and logs; check provider region/model/key,
  quota, output format and timeouts. Correct or submit anew after resolving the cause.
- **Long-lived `queued`:** inspect whether its job is pending or claimed. A stopped
  worker can process pending work after restart; interrupted claimed jobs have no
  automatic recovery. Duplicate submissions create additional records/jobs.
- **409 on an edit:** reload the current revision/state. Confirmed meals and meal
  dates are locked. Profile/daily edits also use revisions to prevent lost updates.
- **422 on an edit:** supply the required bounded integer revision from the latest
  record; strings, booleans, fractional values and out-of-range revisions are not
  accepted. Validation must not change the saved meal or enqueue work.
- **Correction still shows an old food:** an explicit complete replacement must
  remove the superseded meal; quantity-only edits and additions retain other foods.
  Removed-shell and no-extra-oil details must not appear as unsupported foods.
  If reproducing this issue, record the exact wording and runtime version, and
  rebuild the AI service after changes to food matching.
- **Unexpected diary total:** only confirmed meals for the selected Hong Kong date
  count. A manual total replaces the meal sum; clear it to restore aggregation.
  Unrecorded days remain blank, not zero. Daily weight does not update the profile.
- **Missing UI updates:** rebuild the API and reload. Public asset routes allow only
  `catalogue-en.js`, `i18n.js`, `account-i18n.js` and `app.js`; private HTML uses
  `no-store`, JavaScript uses `no-cache`. Do not expose a general filesystem route.

## Data, migrations and recovery

Food catalogue `2026-11-23.2` is versioned JSON: 202 ingredients and 384 reference
recipes. All 586 records have English names, and all recipe methods are bilingual.
The [home-recipe follow-up](home-recipe-expansion.md) adds 34 project-authored
reference formulas while preserving earlier ingredient nutrients and 350 recipe
formulations, with the existing egg-portion metadata retained. Recipe-site URLs
are discovery evidence, not nutrient measurements. Do not use byte-for-byte
equality with the earlier catalogue as a release check. Git publication is separate from deployment; historical tags and deployments
remain unchanged.
The application database is PostgreSQL. The merged preview starts a separate volume;
it does not automatically combine records from existing deployments.

API startup runs `alembic upgrade head` before the worker starts. Migrations 0006–0008
add users/sessions/ownership, profiles, daily records and meal dates; 0009 adds
exercise calories and 0010 adds intake coverage. The expected head is
`20261030_0010`. Old ownerless meals/cases are preserved but inaccessible through account APIs; they are not
assigned to the first registrant. Existing confirmed meals receive a Hong Kong date
from their confirmation timestamp, with creation time as fallback. Saved meal
nutrients are not recalculated against newer catalogue data.

Before a real database upgrade, back up data, retain compatible images/code, stop
accepting new work and let active jobs finish. Backups now contain password hashes
and private records; restrict access and keep them outside Git. A code rollback
does not reverse schema migrations. Use a tested backup/compatible code path.

Stop while retaining the preview database:

```sh
docker compose -p nutrichat-merged-qwen --env-file .env \
  -f compose.yaml -f compose.integrated.yaml down
```

Do not add `-v` during ordinary updates: it deletes the database volume. No public
cloud deployment is performed by a Git push or this local merge. Follow the separate
[cloud procedure](cloud-deployment.md) for any later deployment.

## Evidence and submission snapshots

Final checks and their exact scope are recorded in
[Week 13 verification](evidence/week13-verification.md). The latest earlier meal
review is the [14 November recipe-usability follow-up](qa/reports/2026-11-14-recipe-usability.md);
the [earlier 14 November workspace review](qa/reports/2026-11-14-fresh-review.md)
and [3 November integration verification](evidence/integration-verification.md)
retain their own runtime versions and results.
The [Week 6 workflow](async-workflow.md), [Week 7 artifact](../submissions/week07/README.md),
[original screenshot guide](../demo/SCREENSHOT_GUIDE.md) and dated reports describe
their labelled versions. Reproduce historical course scripts from their original
commit/tag; do not silently reinterpret them as authenticated merged workflows.

CI includes `main`, `nutrichat`, `test` and `integrate/**` pushes plus pull requests.
It checks Python/Ruff, PostgreSQL migrations and frontend tests. Inspect the run for
the actual pushed SHA; local results do not establish remote CI success.
The final hand-in uses `w13-final` on `test`; see the
[Week 13 package](../submissions/week13/README.md) and its seven-point
[TA demo](../submissions/week13/DEMO.md). `w07-midterm` remains the historical
submission snapshot. Publishing Git branches/tags does not submit Canvas or deploy
the public server. Test counts from separate versions must not be added together.
