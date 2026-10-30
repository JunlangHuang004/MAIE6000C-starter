# Local HKUST setup (`test` branch)

Use the HKUST overlay to enable cloud meal extraction in the existing account
preview on [http://localhost:8001/app](http://localhost:8001/app). Accounts,
personal profiles, daily records and trends continue using the same application
and database; those features do not require a language model. HKUST supplies the
meal-extraction step, while Python still calculates nutrients from the catalogue.

The original Qwen application on port 8000, public ECS deployment and `nutrichat`
branch are unchanged by this local setup. The separate
[port-8004 model lab](models-local-lab.md) remains available for experiments.
Ollama's tested models did not pass complete application acceptance.

## Feature coverage and verification scope

HKUST uses the same catalogue, calculation engine and saved-meal workflow as the
existing cloud adapter. The isolated lab passed nine core and seven extended
checkpoints covering Basic/Advanced estimation, multiple foods, missing weights,
unknown foods, free-text additions and corrections, ingredient edits, whole-pot
oil/yield, recipe reconfirmation, bone-weight clarification and confirm/reload.
These are 16 workflow checkpoints, not 16 independent model calls.

Accounts, profiles, daily records and trends remain provider-independent; a
provider switch does not migrate or replace their data. This coverage supports
using HKUST for the application's existing features, but it does not guarantee
the model will interpret every meal correctly. Review food identities, weights,
recipe assumptions and omitted items before confirming. The
[verification record](evidence/local-model-verification.md) distinguishes the
isolated lab results from validation of the port-8001 runtime switch.

The port-8001 switch was verified on 2026-10-30: services were healthy and selected
`hkust` / `gemini-2.5-flash-lite`. A synthetic profile was saved; a 200 g tomato-and-egg
meal returned 210.2 kcal, was confirmed and reloaded, and appeared in the daily
meal total. A weight record was saved and the trend response covered 30 days.
The existing preview database was retained and backed up privately before switching.
Separately, 235 account/profile/tracking regression tests passed with HKUST selected,
empty model keys and networking disabled. Those checks verify that these features
remain independent of model calls; they do not measure model extraction accuracy
or visually inspect the charts.

## Private configuration

Work from the `test` checkout with Docker and a recent Docker Compose. Preserve
any existing `.env`; create it only when absent:

```sh
test -f .env || cp .env.example .env
```

Add or update these five settings in that private file, leaving unrelated values
and existing credentials intact:

```dotenv
LLM_PROVIDER=hkust
LLM_BASE_URL=https://hkust.azure-api.net/hkust-genai/v1
LLM_MODEL=gemini-2.5-flash-lite
LLM_API_KEY=replace_with_your_own_hkust_key
LLM_API_KEY_HEADER=api-key
```

Use your own HKUST key. Restrict access to the private file and keep it out of Git,
screenshots, logs and submissions. The checked-in `.env.example` contains only
examples. To keep the private configuration elsewhere, set `HKUST_ENV_FILE` to
its absolute path before the startup command; the default is `.env`.

## Start or update the existing preview

Keep the project name and apply all three Compose files in this order:

```sh
docker compose -p nutrichat-accounts --env-file .env.example \
  -f compose.yaml -f compose.accounts.yaml -f compose.accounts.hkust.yaml \
  up -d --build
```

This retains the `nutrichat-accounts` database volume and its existing accounts,
profiles, meals and daily records. Sign in with the same local preview account;
register only if you do not already have one. Use `localhost` consistently in the
browser. Switching the model does not recompute previously saved estimates.

The last overlay sets `LLM_PROVIDER=hkust` consistently for the API, AI service and
worker. Only the AI service loads the private file and receives the key. The API
and worker retain `.env.example` as their file configuration, with the provider
selected by the overlay. Model timeout is 180 seconds; worker timeout is 210
seconds. The API binds only to loopback on port 8001; database and AI ports remain
internal. The overlay builds a separate `nutrichat-accounts-hkust:latest` image.

If another private file is needed, for example:

```sh
HKUST_ENV_FILE=/absolute/path/hkust/.env \
docker compose -p nutrichat-accounts --env-file .env.example \
  -f compose.yaml -f compose.accounts.yaml -f compose.accounts.hkust.yaml \
  up -d --build
```

## Verify with synthetic meals

1. Sign in and submit `白米饭100克，去壳水煮鸡蛋50克，均为熟重` in Basic mode.
   Inspect both retained foods, weights, assumptions and sources.
2. In Advanced mode, submit `去壳水煮鸡蛋，熟重，没有额外用油`. Answer the weight
   question with 125 g, review the result, then correct the meal to 150 g.
3. Confirm and reload the meal. Check that its saved values and confirmation
   persist. An existing account's profile and tracking data should remain present.
4. Try `一碗米饭` in both modes: Basic can use a labelled reference portion;
   Advanced should request grams. Try a known food with an unsupported food and
   check that the unsupported item remains visible rather than being dropped.
5. In Advanced mode, enter `番茄炒蛋200克，熟重`, review the recipe question and
   change whole-pot oil to 5 g and cooked yield to 400 g. Confirm the recipe, then
   request a 150 g portion while keeping those recipe facts. Check that they are
   retained when the application asks for recipe reconfirmation.

Use only synthetic or public data. Live requests consume HKUST quota and create
saved records. These instructions are not claims that every description works;
see the [dated model verification](evidence/local-model-verification.md) for
observed cases and scope. Changing provider does not remove the need to review
model extraction or turn reference recipes into measured nutrition.

## Return to the original offline preview

Let active jobs finish, then omit only the third Compose file and rebuild:

```sh
docker compose -p nutrichat-accounts --env-file .env.example \
  -f compose.yaml -f compose.accounts.yaml up -d --build
```

The original preview selects `NUTRITION_PROVIDER=demo`, uses no model key and
preserves the same database. It supports six legacy English foods with explicit
grams, such as `100g egg`; it does not provide the full Chinese model workflow.
The private HKUST file remains on disk but is not loaded by this offline overlay.
To re-enable HKUST, run the three-file command again.

Keep `-p nutrichat-accounts` unchanged for both directions. Do not use `down -v`
as a switch or normal stop: it deletes the database volume. For a normal stop,
use the currently selected Compose files with `down` and omit `-v`.
