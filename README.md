# NutriChat

**TA demo (`nutrichat` branch):** start with [the self-guided demo folder](demo/README.md).
The main demo shows Chinese meals, Basic/Advanced modes and follow-up correction.
With Qwen configured on the server, users open `/app` directly without registration
or login. The guide also includes a separate no-key integration check with exact
HTTP/database/worker evidence. No recording or in-person presentation is needed
to inspect it. This guide covers the meal-estimation workflow on `nutrichat`.

NutriChat estimates calories, protein, fat and carbohydrates from meal descriptions,
including Chinese ingredients, dish names, cooking methods and follow-up details.
Users review and correct the estimate before confirming it. Confirmed records are locked.

The Qwen workflow includes **138 USDA ingredient records and 250 editable Chinese
reference recipes**. Qwen interprets descriptions; Python calculates nutrients from
source-backed data. This project does not train or fine-tune a model.

Each dish has one home-style reference recipe. Alternative names share an entry;
regional variants are not separate catalogue items. See the [250-dish index](docs/recipe-catalogue.md).

## Estimation modes

Use **中文 / English** in the page header to switch the interface language. The
browser remembers the selection. Controls, clarification forms, nutrition labels,
catalogue display names and reference-method descriptions are available in both
languages. Switching preserves the current meal and unsent form values; it does
not submit a request to Qwen or change saved nutrition values. User-entered text
and free-form model notes retain their original wording. English display names
do not guarantee that Qwen will correctly recognize every English meal name.

| Mode | Use case | Handling missing information |
| --- | --- | --- |
| Basic | Quickly estimate a description such as “一份番茄炒蛋，两个水煮鸡蛋” | Apply and display reference portions, recipes and oil assumptions; ask about unmatched foods or contradictory facts |
| Advanced | Supply weights, preparation and recipe details | Ask for edible grams, raw/cooked state, preparation and consumed oil; require review of batch ingredients and finished recipe weight |

The UI defaults to basic mode; the API defaults to advanced when `mode` is omitted.
Unconfirmed records can switch modes. Basic-mode assumptions never become facts
supplied by the user. Pending clarification leaves all nutrient totals null.
Dialogue, calculation evidence and results are stored in PostgreSQL and restored on reload.

Advanced mode makes inputs more specific, but does not guarantee measured accuracy.
Reference recipes are project-authored examples, not standardized recipes. Brands,
cooking losses and actual portion sizes affect results. See [data provenance and
limitations](docs/nutrition-data.md).

## Run locally

Install Docker and Docker Compose, then run from the repository root:

```sh
# Create .env only on first setup; preserve existing settings and secrets.
test -f .env || cp .env.example .env
docker compose up -d --build
```

Open the [application](http://localhost:8000/app) or [API documentation](http://localhost:8000/docs).

- The default `NUTRITION_PROVIDER=demo` needs no API key. It supports only the legacy
  six English catalogue names and explicit gram weights, for example
  `200g chicken breast and 230g cooked white rice`. It does not provide the full Chinese dialogue workflow.
- For Chinese descriptions and both estimation modes, configure `NUTRITION_PROVIDER=qwen`,
  `DASHSCOPE_API_KEY`, `QWEN_BASE_URL` and `QWEN_MODEL` in the private `.env`, then rerun
  the startup command. The key, workspace and endpoint region must match. See
  [Qwen configuration and cloud deployment](docs/cloud-deployment.md).
- Local Compose publishes API, AI and database development ports. Public deployment
  uses the separate cloud configuration and HTTPS session gateway.

## Meal workflow

1. Select basic or advanced mode and describe the meal.
2. Wait for background processing. Answer questions or provide natural-language corrections.
3. Review each food, portion, recipe, default assumption and nutrition source. Switch modes to recalculate if needed.
4. Confirm the saved estimate. Start a new meal to revise an already-confirmed record.

## Verification

Build the current images first. Unit/integration tests do not require Qwen credentials:

```sh
docker compose run --rm --no-deps -e NUTRITION_PROVIDER=demo api pytest -q -m 'not smoke'
docker compose run --rm --no-deps api ruff check .
```

The language-switch regression tests run separately with Node.js 22 and jsdom.
They use synthetic responses and never contact a model or the running database:

```sh
npm ci --prefix tests/frontend
npm test --prefix tests/frontend
```

The same UI checks run in GitHub Actions on pushes to `nutrichat` and `main`, and
on pull requests. npm packages are test-only; the application serves plain
JavaScript with no runtime npm installation.

See the [dated interface-language verification](docs/evidence/ui-language-verification.md)
for 417 passing Python tests, 15 passing frontend tests and the browser
recipe-edit/confirmation check. The [English-input evaluation](docs/evidence/qwen-english-verification.md)
separately records recognition successes and failures; changing display language
does not improve model matching.

After configuring Qwen and starting the stack, run the live checks below. These
consume model quota; the dialogue check creates synthetic saved meal records.

```sh
docker compose run --rm --no-deps api python scripts/check_qwen.py --live
docker compose exec -T api python scripts/check_dialogue.py --base-url http://api:8000
```

The 2026-10-27 milestone passed 359 unit/integration tests using the CI pytest
entry point. See the [Week 7 verification record](docs/evidence/week07-verification.md)
for static checks, fresh PostgreSQL/worker evidence, smoke tests and separately
reported provider results. Earlier checks remain in the [change log](docs/change-log.md).
The public ECS deployment has not been updated to this 250-dish milestone.

## Architecture and documentation

FastAPI API → PostgreSQL job queue → worker → internal AI service → Qwen extraction /
Python calculation → persisted result. Qwen runs in the cloud; the VM needs no GPU.

| Document | Contents |
| --- | --- |
| [Self-guided TA demo](demo/README.md) | Run this branch, follow the UI, inspect fresh evidence and troubleshoot |
| [Week 7 milestone](submissions/week07/README.md) | Team, current status, demo sequence, evidence, risks and next priorities |
| [API contract](docs/api-contract.md) | Routes, payloads, states, revision conflicts and errors |
| [Architecture](docs/architecture.md) | Service responsibilities, data flow, persistence and boundaries |
| [Nutrition data](docs/nutrition-data.md) | USDA import, recipes, clarification and calculation assumptions |
| [Dish index](docs/recipe-catalogue.md) | All 250 reference dishes, alternative names and cooking methods |
| [Week 6 worker workflow](docs/async-workflow.md) | Lifecycle evidence, failure decisions, ownership and Week 7 test/demo plan |
| [Operations](docs/operations.md) | Local checks, logs, failure handling and migrations |
| [Cloud deployment](docs/cloud-deployment.md) | Qwen, ECS, login, HTTPS and backups |
| [Design decision](docs/adrs/0002-source-backed-dual-mode.md) | Two modes and the model/calculation responsibility split |
| [Change log](docs/change-log.md) | Feature, documentation and validation records |

The project retains the course engineering contract: relational persistence, an API,
an asynchronous worker, a separate AI service, migrations, tests, structured logs,
health checks and metrics. The original `/cases` workflow remains available.
[Starter notes](docs/history/starter-readme.md) and [early API course evidence](docs/history/week05-api-contract.md)
are archived for context and do not define the current feature scope.

This is a shared-account learning prototype without per-user data isolation,
idempotency keys, automatic retries or recovery of interrupted claimed jobs.
Never commit API keys, login passwords, certificates or database backups.

## Week 6 lab verification

See [the asynchronous workflow guide](docs/async-workflow.md) for the isolated
Compose observation and the evidence map. Run the additional lifecycle tests with:

```sh
docker compose run --rm --no-deps -e NUTRITION_PROVIDER=demo api pytest tests/integration/test_worker_lifecycle.py -q
```

Build the current image first. Tests cover claim metadata, terminal processor
failures, success persistence and duplicate-POST behavior. Current team assignments
and the [AI Use Statement](submissions/week07/AI_USE_STATEMENT.md) are included in
the [Week 7 milestone](submissions/week07/README.md).
