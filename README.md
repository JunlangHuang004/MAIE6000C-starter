# NutriChat

NutriChat estimates calories, protein, fat and carbohydrates from meal descriptions,
including Chinese ingredients, dish names, cooking methods and follow-up details.
Users review and correct the estimate before confirming it. Confirmed records are locked.

The Qwen workflow includes **116 USDA ingredient records and 50 editable Chinese
reference recipes**. Qwen interprets descriptions; Python calculates nutrients from
source-backed data. This project does not train or fine-tune a model.

## Estimation modes

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
docker compose run --rm --no-deps api ruff check services tests alembic scripts/import_usda.py scripts/check_qwen.py scripts/check_dialogue.py
```

After configuring Qwen and starting the stack, run the live checks below. These
consume model quota; the dialogue check creates synthetic saved meal records.

```sh
docker compose run --rm --no-deps api python scripts/check_qwen.py --live
docker compose exec -T api python scripts/check_dialogue.py --base-url http://api:8000
```

The 2026-10-17 feature release passed 59 unit/integration tests, Ruff, a JavaScript
syntax check, and real-Qwen workflows locally and on ECS. See the
[change log](docs/change-log.md) for scope and recorded validation.

## Architecture and documentation

FastAPI API → PostgreSQL job queue → worker → internal AI service → Qwen extraction /
Python calculation → persisted result. Qwen runs in the cloud; the VM needs no GPU.

| Document | Contents |
| --- | --- |
| [API contract](docs/api-contract.md) | Routes, payloads, states, revision conflicts and errors |
| [Architecture](docs/architecture.md) | Service responsibilities, data flow, persistence and boundaries |
| [Nutrition data](docs/nutrition-data.md) | USDA import, recipes, clarification and calculation assumptions |
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
