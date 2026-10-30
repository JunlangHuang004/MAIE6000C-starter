# NutriChat

The experimental `test` branch uses **HKUST GenAI for the recommended local
application on port 8001**. See [local HKUST setup](docs/local-hkust.md) to keep
existing preview accounts and records while enabling Chinese meal extraction.
The original Qwen deployment remains separate. The [model lab](docs/models-local-lab.md)
on port 8004 is for provider experiments; the tested Ollama models failed full
application acceptance and are not a reliable replacement for the cloud model.

This `test` branch adds independent accounts, personal profiles, daily nutrition
references, daily calorie/weight records and 30-day trends. See [the calculation assumptions and profile workflow](docs/personalization.md).
See [account setup and the isolated preview](docs/accounts.md). The Week 7 tag and
existing public deployment remain separate snapshots.

NutriChat estimates calories, protein, fat and carbohydrates from meal descriptions,
including Chinese ingredients, dish names, cooking methods and follow-up details.
Users review and correct the estimate before confirming it. Confirmed records are locked.

The cloud-model workflow includes **138 USDA ingredient records and 250 editable
Chinese reference recipes**. HKUST GenAI or Qwen interprets descriptions; Python
calculates nutrients from source-backed data. This project does not train or
fine-tune a model.

Each dish has one home-style reference recipe. Alternative names share an entry;
regional variants are not separate catalogue items. See the [250-dish index](docs/recipe-catalogue.md).

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

Use the `test` checkout with Docker and a recent Docker Compose. Create the private
configuration only if it does not exist:

```sh
# Create .env only on first setup; preserve existing settings and secrets.
test -f .env || cp .env.example .env
```

Add or update these five values in the private `.env`, preserving its other
settings. Use your own HKUST key, and never commit it:

```dotenv
LLM_PROVIDER=hkust
LLM_BASE_URL=https://hkust.azure-api.net/hkust-genai/v1
LLM_MODEL=gemini-2.5-flash-lite
LLM_API_KEY=replace_with_your_own_hkust_key
LLM_API_KEY_HEADER=api-key
```

Start the existing account-preview project with the HKUST override last:

```sh
docker compose -p nutrichat-accounts --env-file .env.example \
  -f compose.yaml -f compose.accounts.yaml -f compose.accounts.hkust.yaml \
  up -d --build
```

Open the [application](http://localhost:8001/app) or
[API documentation](http://localhost:8001/docs). Sign in with an existing local
preview account or register a new one. Keeping the same project name preserves
the preview database, including accounts, profiles, meals and daily records.
Only the AI service receives the private model key; the API binds to loopback,
and the AI/database ports are not published.

The no-key offline preview remains available by omitting the HKUST override, as
shown in [the local setup guide](docs/local-hkust.md). It accepts six legacy
English food names and explicit grams, such as `100g egg`; it does not provide
the full Chinese dialogue workflow. The older Qwen application on port 8000 and
public ECS deployment are not changed by this startup command. See
[Qwen configuration and cloud deployment](docs/cloud-deployment.md) for their
separate configuration.

## Personal daily reference

After signing in, fill in age, height, current weight, the formula sex coefficient,
activity level and a muscle-gain or fat-loss goal. Save to calculate an approximate
daily energy and macronutrient reference. The backend uses a versioned formula
without model calls. Saved inputs are private to the account; editing them recalculates
the reference. A profile is optional for meal estimation. See
[inputs, assumptions, safeguards and limitations](docs/personalization.md).

## Daily records and trends

Choose a date to save a weight measurement and, optionally, a total calorie intake.
Without a manual total, NutriChat sums that date's confirmed meals. A manual total
**replaces** that sum; clearing it restores automatic aggregation. Select the meal
date before confirming an estimate, including meals entered later for a past date.

Two charts show calories and weight over a selected 30-day window. Unrecorded dates
stay blank; the average uses recorded calorie days only. Dates use Hong Kong time.
Daily weights do not change the current profile or its reference automatically.
See [the tracking workflow, date policy and limitations](docs/tracking.md).

## Meal workflow

1. Sign in, select basic or advanced mode and describe the meal.
2. Wait for background processing. Answer questions or provide natural-language corrections.
3. Review each food, portion, recipe, default assumption and nutrition source. Switch modes to recalculate if needed.
4. Choose the meal date and confirm the saved estimate. Start a new meal to revise an already-confirmed record.
5. Open your recent meals from your account history; sign out on a shared device.

## Verification

Build the current local images first. Unit/integration tests do not require a
real model key; force the offline selector for this test process:

```sh
docker compose -p nutrichat-accounts --env-file .env.example \
  -f compose.yaml -f compose.accounts.yaml -f compose.accounts.hkust.yaml \
  run --rm --no-deps -e LLM_PROVIDER=heuristic -e NUTRITION_PROVIDER=demo \
  api pytest -q -m 'not smoke'
docker compose -p nutrichat-accounts --env-file .env.example \
  -f compose.yaml -f compose.accounts.yaml -f compose.accounts.hkust.yaml \
  run --rm --no-deps api ruff check services tests
```

Use synthetic or public descriptions for live model checks. They consume the
selected provider's quota and create saved records. See [local HKUST checks](docs/local-hkust.md)
and [recorded provider results](docs/evidence/local-model-verification.md).
The existing Qwen-only live scripts remain documented in
[operations](docs/operations.md); run those against the separately configured Qwen stack.

On 2026-10-30, HKUST passed 16 isolated-lab workflow checkpoints, followed by a
successful port-8001 smoke check covering profile save, a 210.2-kcal Chinese meal,
confirmation/reload, daily aggregation, a weight record and a 30-day trend response.
Separately, 235 account/profile/tracking regression tests passed with HKUST selected,
empty model keys and networking disabled.
The checkpoints are not independent model calls or a general accuracy score. See
[provider and runtime verification](docs/evidence/local-model-verification.md),
which also records the unsuccessful local Ollama acceptance checks.

The 2026-10-27 milestone passed 359 unit/integration tests using the CI pytest
entry point. See the [Week 7 verification record](docs/evidence/week07-verification.md)
for static checks, fresh PostgreSQL/worker evidence, smoke tests and separately
reported provider results. Earlier checks remain in the [change log](docs/change-log.md).
The public ECS deployment has not been updated to this 250-dish milestone.
The `test` profile increment passed 513 unit/integration tests, isolated PostgreSQL
migration/concurrency checks and browser workflow checks; see
[personalization verification](docs/evidence/personalization-verification.md).
The daily tracking increment passed 594 unit/integration tests, two authenticated
smoke tests, PostgreSQL migration/concurrency checks and browser diary/chart checks;
see [tracking verification](docs/evidence/tracking-verification.md).

## Architecture and documentation

FastAPI API → PostgreSQL job queue → worker → internal AI service → configured
model extraction / Python calculation → persisted result. HKUST GenAI and Qwen
run in the cloud; those providers do not require a local GPU. Ollama is a separate
experimental local provider with the limitations recorded above.

| Document | Contents |
| --- | --- |
| [Week 7 milestone](submissions/week07/README.md) | Team, current status, demo sequence, evidence, risks and next priorities |
| [Independent accounts](docs/accounts.md) | Registration, sessions, data isolation, preview and limits |
| [Local HKUST setup](docs/local-hkust.md) | Recommended port-8001 configuration, private key handling and offline rollback |
| [Model lab](docs/models-local-lab.md) | Isolated port-8004 experiments and provider limitations |
| [Personalization](docs/personalization.md) | Saved profiles, formula references, assumptions and scope |
| [Daily tracking](docs/tracking.md) | Calorie and weight records, meal dates and 30-day trends |
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

This is a learning prototype with independent accounts and per-user meal ownership.
Personal profiles, daily energy/macronutrient references and 30-day calorie/weight
trends are available. Password recovery, Google login and historical target
snapshots are not implemented.
Idempotency keys, automatic retries and recovery of interrupted
claimed jobs remain future work.
Never commit API keys, login passwords, certificates or database backups.

## Week 6 lab verification

Historical evidence and rehearsal commands describe the frozen `w07-midterm` tag.
For current account-aware checks, use [the account guide](docs/accounts.md).

See [the asynchronous workflow guide](docs/async-workflow.md) for the isolated
Compose observation and the evidence map. Run the additional lifecycle tests with:

```sh
docker compose -p nutrichat-accounts --env-file .env.example \
  -f compose.yaml -f compose.accounts.yaml -f compose.accounts.hkust.yaml \
  run --rm --no-deps -e LLM_PROVIDER=heuristic -e NUTRITION_PROVIDER=demo \
  api pytest tests/integration/test_worker_lifecycle.py -q
```

Build the current image first. Tests cover claim metadata, terminal processor
failures, success persistence and duplicate-POST behavior. Current team assignments
and the [AI Use Statement](submissions/week07/AI_USE_STATEMENT.md) are included in
the [Week 7 milestone](submissions/week07/README.md).
