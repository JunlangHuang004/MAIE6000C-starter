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

The Qwen workflow includes **200 USDA ingredient records and 350 editable Chinese
reference recipes**. Qwen interprets descriptions; Python calculates nutrients from
source-backed data. This project does not train or fine-tune a model.

Each dish has one home-style reference recipe. Alternative names share an entry;
regional variants are not separate catalogue items. See the [350-dish index](docs/recipe-catalogue.md).

**Food coverage is limited:** 200 ingredient records and 350 reference dishes do
not cover every meal, regional name, brand or preparation. Matching is restricted
to recorded names and reviewed aliases. An unsupported food must produce a
“No corresponding food record” message with no meal nutrition totals; it must
not be estimated using a similar dish. Check the catalogue or select the actual
supported ingredients and their gram weights in **Build from actual ingredients**.
Unlisted synonyms and spelling
variants may need rephrasing even when the intended dish is familiar.

## Estimation modes

Use **中文 / English** in the page header to switch the interface language. The
browser remembers the selection. Controls, clarification forms, nutrition labels,
catalogue display names and reference-method descriptions use the selected
language where a translation is available. The original 388 records retain their
English display mappings; the 162 new records prioritize Chinese and fall back to
their Chinese names or methods in English mode. Switching preserves the current
meal and unsent form values; it does
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

See the [current expansion verification](docs/evidence/chinese-expansion-verification.md)
for the final validation scope and recorded outcomes. The edible-state matching
follow-up `dae0b94` passed 664 Python tests and Ruff; the unchanged frontend suite
passed 26 DOM tests on the initial expanded source. Live checks retain their
executed source versions. Earlier evidence stays
versioned: the [interface-language verification](docs/evidence/ui-language-verification.md)
records 417 Python tests and 15 frontend tests, and the
[ingredient-builder verification](docs/evidence/ingredient-recipe-verification.md)
records 545 Python tests and 26 frontend tests on `7c841b1`. These counts are not
added together. The [English-input evaluation](docs/evidence/qwen-english-verification.md)
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
The public ECS deployment is older and has not been updated to this catalogue
and ingredient-builder release.

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
| [Actual ingredient recipes](docs/ingredient-recipes.md) | Recover an unsupported meal item with explicit ingredients and consumed/batch portions |
| [Dish index](docs/recipe-catalogue.md) | All 350 reference dishes, alternative names and cooking methods |
| [Week 6 worker workflow](docs/async-workflow.md) | Lifecycle evidence, failure decisions, ownership and Week 7 test/demo plan |
| [Operations](docs/operations.md) | Local checks, logs, failure handling and migrations |
| [Cloud deployment](docs/cloud-deployment.md) | Qwen, ECS, login, HTTPS and backups |
| [Design decision](docs/adrs/0002-source-backed-dual-mode.md) | Two modes and the model/calculation responsibility split |
| [Change log](docs/change-log.md) | Feature, documentation and validation records |
| [OpenNutriTracker comparison](docs/research/opennutritracker-comparison.md) | Source-linked design lessons and proposed recovery/recipe improvements |

The project retains the course engineering contract: relational persistence, an API,
an asynchronous worker, a separate AI service, migrations, tests, structured logs,
health checks and metrics. The original `/cases` workflow remains available.
[Starter notes](docs/history/starter-readme.md) and [early API course evidence](docs/history/week05-api-contract.md)
are archived for context and do not define the current feature scope.

## Current limitations

The local application has no individual account registration, login or per-user
record ownership. Its visible **Log out** button has no local authentication
function. The optional public deployment does implement a shared-password login
and signed-session gateway; it protects access to the demo but does not provide
separate user accounts or private meal histories.

Food coverage is limited to the catalogue above. Reference recipes and portion
defaults are estimates, and supported names do not establish measured nutrition
accuracy. Model extraction, quantities and cooking details can still be wrong;
review the interpreted foods and evidence before confirmation. The prototype
also lacks idempotency keys, automatic retries and recovery of interrupted
claimed jobs. Never commit credentials, certificates or database backups.

See [matching verification](docs/evidence/food-matching-verification.md) for the
unsupported-food fix and [independent QA](docs/qa/README.md) for the reviewer,
persistent issue ledger and browser acceptance reports.

An unsupported item also offers **Build from actual ingredients**. Select actual
catalogue ingredients and grams, then specify either the amounts consumed or a
whole batch plus the eaten portion. This creates a labelled user-defined recipe
for that item, preserving other meal items. Calculation uses the reviewed form
without another model call. Custom recipes can be edited before confirmation;
free-text replies are disabled for meals containing them to preserve their facts.
This is not a reusable personal recipe library or a new catalogue dish record.

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
