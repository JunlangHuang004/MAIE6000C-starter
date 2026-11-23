# Integrated NutriChat

This checkout merges `nutrichat` at `7c9525d` and `test` at `5af1780` on
`integrate/nutrichat-test` as merge commit `cdd4c9c`. After validation, the merged
implementation is published on **`test`**. The original `test` commits remain in
its history; `nutrichat` and the `w07-midterm` tag are unchanged. The public ECS
deployment is not updated by this publication.

The current `test` final package is [Week 13](../submissions/week13/README.md),
with checkpoint tag `w13-final`. The merge identifiers above describe the original
3 November integration; subsequent changes and checks have their own dated evidence.

## What is combined

| Area | Integrated behavior |
| --- | --- |
| Food data | Catalogue 2026-11-23.1: 200 USDA ingredients and 384 reference recipes; existing nutrients/formulations retained |
| Estimation | Basic/Advanced, Chinese descriptions, strict supported-name matching, clarification and correction |
| Unknown food | No substitute dish or partial meal total; explicit actual-ingredient recipe editor |
| Languages | Chinese/English controls; English names for all 584 records and English methods for all 384 recipes |
| Accounts | Register, sign in/out, revocable sessions, private meal history and ownership checks |
| Personal reference | Age, height, weight, formula sex coefficient, activity and goal; deterministic daily energy/macronutrient reference |
| Diary | Dated confirmed meals, optional manual calorie total, weight, exercise and intake coverage; manual total replaces the meal sum |
| Trends | 30-day calorie/weight charts; missing dates stay blank |
| Models | Qwen and HKUST adapters share exact identity checks; Ollama remains experimental |

The current catalogue preserves the `nutrichat` ingredient nutrients and existing
350 recipe formulations, including the later egg-portion metadata. The
[23 November follow-up](home-recipe-expansion.md) adds 34 reference recipes,
reviewed aliases and the 162 missing English translations. Meishichina supplies
only dish-name/style evidence; quantities and finished yields are project-authored
assumptions, with nutrients calculated from USDA ingredients. This
follow-up does not deploy the app and does not change `nutrichat`,
`w13-final` or saved historical estimates. It does not train a model or claim
measured nutrition for every Chinese dish.

## Start an isolated preview

Requirements: Docker running, Compose 2.24.4+; run from this checkout.

```sh
test -f .env || cp .env.example .env
docker compose -p nutrichat-merged-qwen --env-file .env \
  -f compose.yaml -f compose.integrated.yaml up -d --build --wait db ai api worker
```

Open <http://localhost:8005/app>. Register a new account with a username of
3–32 ASCII letters/digits/underscores and a password of 10–128 characters.
The page redirects to sign-in when the session expires. Only the API is exposed,
on loopback; the database and AI ports remain internal.

Use a different `-p` name **and** `NUTRICHAT_PORT` for a second independent copy.
The project name determines the database volume; changing only the port does not
isolate data or services. Keep the same project name when restarting to retain
accounts, profiles and records. Do not reuse the original preview projects when
trying this merge.

### Select a model

The default `.env.example` uses the offline six-food English parser. It verifies
accounts, persistence and charts but cannot interpret Chinese meals. Use explicit
grams such as `100g egg`; use **Edit this meal** then **Replace full description**
to change it to `200g egg`. Free-text follow-up is disabled for this parser rather than pretending
to interpret replies.

For Qwen, set the following in private `.env`:

```dotenv
NUTRITION_PROVIDER=qwen
LLM_PROVIDER=qwen
DASHSCOPE_API_KEY=your_private_key
QWEN_BASE_URL=your_matching_region_openai_compatible_base_url
QWEN_MODEL=qwen-plus
QWEN_TIMEOUT_SECONDS=60
WORKER_REQUEST_TIMEOUT_SECONDS=90
```

For HKUST, use the endpoint/model your subscription supports:

```dotenv
LLM_PROVIDER=hkust
LLM_BASE_URL=https://hkust.azure-api.net/hkust-genai/v1
LLM_MODEL=gemini-2.5-flash-lite
LLM_API_KEY=your_private_key
LLM_API_KEY_HEADER=api-key
LLM_TIMEOUT_SECONDS=180
WORKER_REQUEST_TIMEOUT_SECONDS=210
```

Restart with the same Compose command. Only the AI service receives the private
model configuration; all services receive the same provider selector. Health
checks do not prove model access or quota. Provider credentials are never included
in Git. See [provider setup](local-hkust.md) and [data limits](nutrition-data.md).

## Use the integrated features

1. Register/sign in; optionally save your profile and review its assumptions.
2. Choose Basic or Advanced and describe a supported meal. Review interpreted
   foods, portions and assumptions. Answer missing-detail questions when needed.
3. If a food has no record, correct its name or explicitly select its actual
   ingredients and weights. The app must not invent a similar dish.
4. Correct the result while unconfirmed. Choose the consumption date, then
   confirm. Confirmed meals are locked and contribute to that date's calorie sum.
5. In **Daily diary**, choose a date and save weight and exercise; zero means no
   exercise, while blank is unknown. Review the optional five-category intake
   checklist. A manual calorie total replaces the meal sum; clearing it restores
   the sum. An applicable profile plus intake/exercise enables approximate balance.
6. In **Trends**, select the end date of the 30-day window. Missing days are not
   zero-calorie days.
   Sign out and sign back in to check private history and persistence.

The four panels are Meals, Daily diary, Trends and My goals. Switching panels or
languages preserves unsaved values without submitting them; save before reloading.
Profile references are approximate adult references, not clinical prescriptions.
Daily weight entries do not automatically alter the current profile or target.
See [personalization](personalization.md) and [tracking](tracking.md).

## Data upgrades and existing records

Food catalogue data and user records are different: the former is versioned JSON;
the latter lives in PostgreSQL. Migrations 0006–0008 add users/sessions, profiles,
daily records and meal dates; 0009 adds exercise and 0010 adds intake coverage.
The head is `20261030_0010`. These schema upgrades do not replace food data or
delete old meals.

Old shared meals have no verifiable owner. They remain in the database with null
ownership and are not assigned to the first registered user or exposed to every
new account. Existing `test` accounts/records are not automatically copied into
this separate preview. A deliberate production data transfer requires a backup
and an explicit ownership policy; this merge does not perform one.

For an upgrade of an existing deployment, back up its database, drain pending work,
then start the merged code against that database. Do not combine rows from two
application databases by matching usernames. Never use `down -v` for an upgrade.
The older shared-password gateway is superseded by app accounts in this checkout;
use the current [cloud deployment guide](cloud-deployment.md) before deployment.

## Verification

Use [Week 13 verification](evidence/week13-verification.md) for final release
checks. The [14 November recipe-usability follow-up](qa/reports/2026-11-14-recipe-usability.md)
is the most recent earlier meal-flow review; it records 1,208 backend and 56
frontend tests plus separate bounded live/browser checks and unresolved cases.
The [earlier 14 November workspace review](qa/reports/2026-11-14-fresh-review.md)
covers the preceding four-panel/account/tracking pass.

The [3 November integration verification record](evidence/integration-verification.md)
records 1,049 Python tests, 35 frontend tests, two service smoke tests, a PostgreSQL
upgrade and live/browser checks for that earlier merged build. These are historical
checkpoints, not final-tag test counts. Do not add counts across versions or treat
a key-free workflow check as live-model accuracy evidence.

For a repeatable, credential-free durable check:

```sh
python3 demo/run.py start
python3 demo/run.py check
python3 demo/run.py stop
```

This uses `nutrichat-integrated-demo` on port 8006, creates a disposable account,
checks 155 → 310 kcal correction, confirmation/reload, profile, daily totals,
weight and 30-day data, and revokes its session. It briefly stops only that
project's worker. Set `NUTRICHAT_DEMO_PROJECT` and `NUTRICHAT_DEMO_PORT` together
when running another isolated copy. See [the demo guide](../demo/README.md).

## Remaining limits

Coverage remains finite, and model interpretation can fail. Unknown matches stay
blocked. Recipe quantities and portions are editable assumptions. There is no
password recovery, Google login, reusable personal recipe library, historical
target snapshot, idempotency key, automatic retry or interrupted-job recovery.
The existing public deployment and frozen course submission are separate releases.
