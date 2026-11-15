# NutriChat

NutriChat combines the meal-estimation features from `nutrichat` with independent
accounts, personal daily references and 30-day tracking on `test`. It keeps
**the `nutrichat` catalogue's 200 USDA ingredient records and 350 editable
Chinese reference recipes**, with their nutrient values unchanged. The current
follow-up adds an explicit 50 g reference for one large shelled hard-boiled egg.
The `nutrichat` branch, `w07-midterm` submission tag and existing deployments remain
separate snapshots.

NutriChat estimates calories, protein, fat and carbohydrates from meal descriptions.
Qwen or HKUST GenAI interprets foods and quantities; Python calculates from the
versioned food data. Users review, correct and confirm the saved estimate, then
track confirmed meals and weight measurements privately. No model training is required.

The final course package is [Week 13 — `w13-final`](submissions/week13/README.md),
with a [seven-point TA demo](submissions/week13/DEMO.md),
[technical brief](submissions/week13/final-technical-brief.md) and
[AI Use Statement](submissions/week13/AI_USE_STATEMENT.md). The
[Week 13 verification record](docs/evidence/week13-verification.md) separates final
checks from earlier dated evidence.

Start with [the integration guide](docs/integration.md) for the merged preview and
verification. [The demo folder](demo/README.md) provides a self-guided workflow and
a separate key-free integration check. Earlier screenshots and reports retain their
original source/date; they are not evidence of this merged build.
See the [current workspace walkthrough](demo/INTEGRATED_GUIDE.md) and
[14 November recipe-usability follow-up](docs/qa/reports/2026-11-14-recipe-usability.md)
for the updated meal flow and dated verification scope. The
[earlier 14 November fresh review](docs/qa/reports/2026-11-14-fresh-review.md)
retains evidence for the preceding workspace pass.

## Run the merged application

Use Docker and a recent Docker Compose. From this checkout, preserve existing
private configuration:

```sh
test -f .env || cp .env.example .env
docker compose -p nutrichat-merged-qwen --env-file .env \
  -f compose.yaml -f compose.integrated.yaml up -d --build
```

Open [NutriChat](http://localhost:8005/app), register an account, and sign in.
The preview exposes only the API on loopback; AI and PostgreSQL stay internal.
Only the AI service receives the private model configuration. Its own Compose
project/database avoids replacing the existing applications on other ports.

The default `demo` provider requires no key and accepts six legacy English food
names with explicit grams, such as `100g egg`. It does not interpret Chinese meals
or conversational corrections. Open **Edit this meal**, then use **Replace full
description** to change an offline meal, for example to `200g egg`; the server
rejects unsupported chat replies.

For the full Chinese workflow, select one provider in the private `.env`:

| Provider | Configuration |
| --- | --- |
| Qwen | `LLM_PROVIDER=qwen`, `DASHSCOPE_API_KEY`, matching `QWEN_BASE_URL`, `QWEN_MODEL=qwen-plus` |
| HKUST GenAI | `LLM_PROVIDER=hkust`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_KEY_HEADER=api-key` |

Use the endpoint/model allowed by your provider account. Keep the worker timeout
longer than the selected model timeout and restart with the same command after
changing configuration. A successful health check does not prove valid provider
credentials or quota. The Ollama adapter is retained for experiments; earlier tested
models did not pass full application acceptance. See [provider setup](docs/integration.md).

A separate, key-free check uses port 8006 and project `nutrichat-integrated-demo`:

```sh
python3 demo/run.py start
python3 demo/run.py check
python3 demo/run.py stop
```

For multiple checkouts, choose both a unique `NUTRICHAT_DEMO_PROJECT` and a free
`NUTRICHAT_DEMO_PORT`, using the same values for start/check/stop. Changing a port
alone does not isolate Docker resources. Stopping retains the database.

## Four workspace panels

| Panel | What to do here |
| --- | --- |
| **Meals** | Describe, review, correct and confirm a meal; use Basic or Advanced mode and the ingredient builder |
| **Daily diary** | Check confirmed-meal totals, save weight and exercise, review intake coverage, and reopen recent meals |
| **Trends** | View 30 days of calorie and weight charts, summary statistics and daily details |
| **My goals** | Optionally save a personal profile and view approximate daily nutrition references |

Meals opens first. Switching panels or interface language preserves unsaved form
values; it does not submit them. Saving is still required before reloading or
leaving the page. After submission, the description becomes compact and the result
and its actions take priority. Reference-portion and reference-recipe badges remain
visible while food evidence is collapsed; a banner explains any unverified
references. Expand a food for its quantities, assumptions and sources. The searchable
catalogue shows 20 matching entries at a time; **Show 20 more** reveals the next set
without limiting coverage.

## Meal estimation

| Mode | Use case | Missing information |
| --- | --- | --- |
| Basic | A quick estimate, such as “一份番茄炒蛋，两个水煮鸡蛋” | Display reference portions, recipes and oil assumptions for supported foods |
| Advanced | User-supplied weights and preparation details | Ask for edible grams, raw/cooked state, preparation and oil; require recipe review |

1. Sign in, select a mode and describe the meal.
2. Wait for background processing, then review the totals, food weights and any
   reference badges. Expand each food for assumptions and sources.
3. Answer required questions. Recipe questions show a batch preview; expand
   **Review or adjust batch quantities** only when needed. Explicitly accept the
   reviewed recipe; changing any ingredient quantity or finished weight clears
   acceptance and updates the preview.
4. Choose **Edit this meal** to open corrections for a completed estimate.
   Closing the editor, switching panels or changing language preserves an unsent
   reply. Pending corrections block confirmation until submitted or cleared;
   discard an offline replacement by restoring its original full description.
   A visible notice explains this even when the editor is closed.
   Unconfirmed records can switch modes.
5. If a food has no matching record, correct its name or use **Build from actual
   ingredients** to select actual catalogue ingredients and their gram weights.
6. Choose the meal date and confirm. The saved record and date are locked; start a
   new meal to revise a confirmed entry. Conversation history remains available
   below the result, without an empty correction card.

**Food coverage is limited.** The catalogue does not cover every dish, synonym,
brand or preparation. Matching requires recorded names or reviewed aliases.
Unsupported foods produce “No corresponding food record” and withhold all meal
nutrient totals; another dish is never used as a substitute. Basic assumptions
fill missing portions, not missing food identities.

Counts need a reference for the stated unit. Without a recorded piece, bowl or cup
weight, Basic asks for edible grams and withholds meal totals until answered. The
hard-boiled egg record explicitly uses 50 g for one large egg with its shell removed;
this is a labelled reference, not a measurement of the user's egg. An explicit
no-oil instruction removes all cooking oils from a reference recipe, including
sesame oil, while preserving other ingredients and their naturally occurring fat.

The ingredient builder creates a labelled user-defined recipe for one item. Choose
consumed ingredient amounts, or a whole batch with finished weight and eaten portion.
The accepted form is calculated without another model call and preserves other meal
items. Custom recipes use structured edits before confirmation; free-text replies
are disabled to avoid losing their facts. This is not a personal recipe library.

Use **中文 / English** to switch the interface without changing saved nutrients or
submitting a model request. Original user text and free-form model notes keep their
wording. The original 388 records have English display mappings; the 162 newer
records prioritize Chinese and fall back to Chinese where translations are absent.
English display names do not guarantee recognition of every English food name.

## Personal references and tracking

A profile in **My goals** is optional for meal estimation. Save age, height, current
weight, the formula sex coefficient, activity level and a muscle-gain or fat-loss goal to obtain
approximate daily energy and macronutrient references. The versioned Python formula
uses explicit assumptions; profile inputs are not sent to the model. Some inputs
are saved without generating a target when the automatic-output guards apply.
See [calculation assumptions and scope](docs/personalization.md).

In **Daily diary**, choose a date to save weight and exercise energy. Expand the
manual-total control only when replacing the confirmed-meal sum, and expand the
coverage checklist to review breakfast, lunch, dinner, snacks and drinks/oils/sauces.
Enter zero exercise when none was performed; a blank value remains unknown. With an
applicable profile and explicit exercise value, the daily card estimates a positive
surplus or deficit from recorded intake versus baseline expenditure plus exercise.
This is approximate and should not alone set cardio intensity. Without a manual
total, the diary sums that date's confirmed meals. A manual total **replaces** the
sum; clearing it and saving restores automatic aggregation. **Trends** keeps two
charts and a detail table in a separate panel for 30 consecutive days. Missing dates
remain gaps, and averages use recorded calorie days only. Dates use Hong Kong time.
Daily weights do not automatically change the
profile or its reference. See [the tracking guide](docs/tracking.md).

The meal estimate card appears directly after the meal input. A fixed synthetic
Chinese meal regression corpus and optional live Qwen evaluator are described in
[the evaluation guide](docs/evaluation.md).

## Verification

Build this checkout first. Unit/integration tests use controlled model boundaries
and need no private credentials:

```sh
docker compose -p nutrichat-merged-qwen --env-file .env \
  -f compose.yaml -f compose.integrated.yaml run --rm --no-deps \
  -e LLM_PROVIDER=heuristic -e NUTRITION_PROVIDER=demo api pytest -q -m 'not smoke'
docker compose -p nutrichat-merged-qwen --env-file .env \
  -f compose.yaml -f compose.integrated.yaml run --rm --no-deps api ruff check .
npm ci --prefix tests/frontend
npm test --prefix tests/frontend
```

Frontend checks use Node.js 22 in CI and synthetic responses. npm is test-only;
the application serves plain JavaScript. CI includes `integrate/**`, `test`,
`nutrichat` and `main` pushes, plus pull requests. Local passing tests do not imply
that a pushed commit has passed GitHub Actions.

[Week 13 verification](docs/evidence/week13-verification.md) is the release-check
record. [Integration verification](docs/evidence/integration-verification.md)
records the earlier 3 November merged build.
The [recipe-usability follow-up](docs/qa/reports/2026-11-14-recipe-usability.md)
records the current meal-flow changes and their verification scope. The
[earlier fresh review](docs/qa/reports/2026-11-14-fresh-review.md) retains the
preceding workspace pass and its separate automated, browser and provider evidence.
Earlier [catalogue verification](docs/evidence/chinese-expansion-verification.md),
[account](docs/evidence/accounts-verification.md),
[profile](docs/evidence/personalization-verification.md),
[tracking](docs/evidence/tracking-verification.md) and
[provider reports](docs/evidence/local-model-verification.md) retain their original
versions. Do not add counts from different checkpoints or treat old live checks as
new model-accuracy evidence. Live checks consume provider quota and create records;
see [operations](docs/operations.md) for authenticated checks.

## Architecture and documentation

FastAPI API → PostgreSQL job queue → worker → internal AI service → model extraction
and Python catalogue arithmetic → saved results. Account authorization is enforced
by the API. Profile references and diary aggregation are deterministic API work
and do not use the model. Qwen/HKUST run in the cloud and need no local GPU.

| Document | Contents |
| --- | --- |
| [Integration guide](docs/integration.md) | Merged preview, source/data policy and current verification |
| [Self-guided demo](demo/README.md) | Setup, checks and walkthrough |
| [Accounts](docs/accounts.md) | Sessions, registration, ownership and recovery limits |
| [Personalization](docs/personalization.md) | Inputs, formula assumptions and safeguards |
| [Daily tracking](docs/tracking.md) | Confirmed meal dates, manual totals, weight and trends |
| [API contract](docs/api-contract.md) | Routes, payloads, states and conflicts |
| [Architecture](docs/architecture.md) | Components, persistence and boundaries |
| [Nutrition data](docs/nutrition-data.md) | USDA provenance and reference-recipe assumptions |
| [Actual ingredient recipes](docs/ingredient-recipes.md) | Explicit ingredients and batch/portion arithmetic |
| [Dish index](docs/recipe-catalogue.md) | All 350 reference dishes |
| [Operations](docs/operations.md) | Startup, tests, migrations and troubleshooting |
| [Cloud deployment](docs/cloud-deployment.md) | Separate future deployment procedure |
| [Change log](docs/change-log.md) | Changes and dated evidence |
| [Week 13 final package](submissions/week13/README.md) | Final workflow, demo, evidence, responsibilities and `w13-final` hand-in |
| [Week 7 milestone](submissions/week07/README.md) | Historical submission scope at `w07-midterm` |

## Current limitations

This is a learning prototype. Catalogue coverage is finite; reference recipes,
portions, energy formulas and macro splits are approximate assumptions. Model
interpretation can still get weights or preparation wrong. Review the evidence
before confirmation; more detail does not guarantee measured nutritional accuracy.

Independent accounts are implemented, but password recovery, Google login, email
verification, account deletion and historical target snapshots are not. Old
ownerless meals are retained by migrations but are not assigned to newly registered
users. The merged preview starts a separate database; it does not import existing
private account/meal data automatically.

There are no idempotency keys, automatic retries or recovery of interrupted claimed
jobs. The public ECS deployment has not been updated by this merge. Credentials,
certificates and database backups must stay outside Git. Earlier TA reports and
milestone screenshots describe their labelled snapshots, not all current features.
