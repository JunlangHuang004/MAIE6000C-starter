# Integrated NutriChat

The current integrated implementation baseline is **`nutrichat` at
`1d17a66ffa445a5dc6a4d699e408c6772929ea79`**. It is the default branch in both
repositories; `test` remains for development. The original integration combined
`nutrichat` at `7c9525d` and `test` at `5af1780` in merge commit `cdd4c9c` on
3 November. Those identifiers describe the historical integration, not the final
release's current features.

Remote `main` branches were removed after preservation under archive tags:

| Archive | Preserved commit |
| --- | --- |
| `archive-nutrichat-7c9525d` in both repositories | `7c9525dc3a6af5ae63bc9dcfc5be19534b856bf1` |
| `archive-main-c5946d6` in `MAIE6000C-starter` | `c5946d6c7801986ea4d9340fd81b83fc6b1f86ef` |
| `archive-main-93ad207` in `Maie-6000c-starter-Junlang-Huang` | `93ad2074226e8e7c7dcd3df058605f8a233dca35` |
| `archive-w13-final-6b87aef` in both repositories | `6b87aef772f7cfde139a383c866e5576ea955cb3` |

The [Week 13 package](../submissions/week13/README.md) uses the refreshed
`w13-final` tag, including the implementation above and its final documents.
The previous annotated tag is preserved under `archive-w13-final-6b87aef`;
the Week 7 tags also retain their historical scope. Follow the package's
tag-refresh commands in an existing clone and resolve `w13-final^{commit}`
for the full release SHA. Use that SHA consistently for assessment and CI checks.
Git publication does not resubmit Canvas or deploy the current release to ECS.

## What is combined

| Area | Integrated behavior |
| --- | --- |
| Food data | Catalogue 2026-11-24.2: 202 USDA ingredients and 384 reference recipes; 16 dishes also have attributed CFS prepared-food references |
| Estimation | Basic/Advanced, Chinese descriptions, strict supported-name matching, clarification/correction, CFS source vectors or accepted ingredient arithmetic with saved provenance |
| Unknown food | Exact identity stays unresolved; optional grounded name inference, user-reviewed facts, same-main-ingredient candidate filtering, explicit approximate-reference acknowledgement and ingredient acceptance |
| Languages | Chinese/English controls; English names for all 586 records and English methods for all 384 recipes |
| Accounts | Register, sign in/out, revocable sessions, private meal history and ownership checks |
| Personal reference | Profile v2: age, height, weight, formula sex coefficient, activity, goal, explicit training/scope answers, deterministic targets or explained withholding |
| Diary | Dated confirmed meals, optional manual calorie total, weight, exercise and intake coverage; manual total replaces the meal sum |
| Trends | 30-day calorie/weight charts and table; missing dates stay blank; approximate balance requires eligible profile, intake and exercise |
| Models | Qwen and HKUST adapters share exact identity checks; Ollama remains experimental |

The [23 November follow-up](home-recipe-expansion.md) added 34 reference recipes,
reviewed aliases and missing English translations. Meishichina supplies only
dish-name/style evidence; editable recipe quantities and finished yields are
project-authored assumptions, with nutrients calculated from USDA ingredients.
The [white-cut chicken correction](white-chicken-reference.md) and
[CFS prepared-food references](cfs-prepared-food-references.md) document subsequent
nutrition updates. Saved historical estimates remain unchanged; the earlier
assessment snapshot is preserved under `archive-w13-final-6b87aef`.
The app does not train a model or claim measured nutrition for every Chinese dish.
CFS source vectors remain separate from ingredient recipes; explicit ingredient,
yield or oil details use ingredient calculation. CFS available carbohydrate and
USDA total carbohydrate keep different definitions, so a mixed meal shows labelled
subtotals with no combined carbohydrate figure. Saved historical results retain
their original nutrients, source basis and caveats.

Main meal submissions, corrections and accepted ingredient recipes use durable
PostgreSQL jobs and the separate worker. Profile/tracking calculations are
synchronous API operations without model calls. Optional name inference and
candidate requests are synchronous API-to-AI calls, with no worker job; reference
selection only saves an unaccepted template. See [architecture](architecture.md).

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

1. Register/sign in; optionally save your profile and explicitly answer its adult
   scope and strength-training questions. Review the assumptions or withholding
   reasons; older profiles need these new answers before targets can return.
2. Choose Basic or Advanced and describe a supported meal. Review interpreted
   foods, portions and assumptions. Answer missing-detail questions when needed.
3. If a food has no record, correct its name or select its actual ingredients and
   weights. Alternatively, ask for editable ingredient/method guesses from its
   name, review those facts and separately request similar-recipe candidates.
   Candidates require the same complete main-ingredient set and compatible method.
   An empty candidate list is a valid result. Acknowledge a chosen approximate reference, then
   review and explicitly accept its ingredient amounts, finished yield and consumed
   portion. Selection alone creates no calculation. Ambiguous names require manual
   clarification; the original unknown identity and other meal items are preserved.
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
Profile references use `mifflin-evidence-2026-v2`. Missing confirmations,
professional-guidance scope, muscle gain without strength training, BMI/energy
eligibility guards or incompatible macro allocation retain valid inputs but
withhold all targets and daily balance. These are approximate adult references
with product scope limits, not clinical prescriptions. Daily weight entries do
not automatically alter the current profile or target.
See [personalization](personalization.md) and [tracking](tracking.md).

## Data upgrades and existing records

Food catalogue data and user records are different: the former is versioned JSON;
the latter lives in PostgreSQL. Migrations 0006–0008 add users/sessions, profiles,
daily records and meal dates; 0009 adds exercise, 0010 adds intake coverage and
0011 adds nullable profile scope/training fields. The head is `20261121_0011`.
The new profile fields have no defaults or consent backfills: existing answers
start null and targets require explicit confirmation. These schema upgrades do
not replace food data, delete old meals or recalculate historical nutrition.

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

The latest recorded application validation is the
[24 November name-reference report](evidence/name-reference-inference-verification.md):
**2,670 backend** and **108 frontend** tests, with Ruff/whitespace checks and
**49 live model calls** across batch/manual checks, diagnostics and three final
targeted requests. The model wire contract now returns only the three inference
facts (`status`, `ingredient_ids`, `preparation`) or ranked candidate IDs; the
server creates displayed questions and explanations. Both API and AI enforce name
grounding and schema/catalogue checks.

The report retains errors and clarifications. Its three final checks did not
rerun the entire earlier 20-name batch, and the final thigh case returned no
candidates. No ingredient equality rule was relaxed to force recovery. These
checks demonstrate bounded observed software/model behavior, not nutritional
accuracy or a reliability rate. [CFS pilot evidence](evidence/cfs-pilot20-review.md)
separately records the source-reference work.

[Week 13 verification](evidence/week13-verification.md), the
[14 November meal-flow review](qa/reports/2026-11-14-recipe-usability.md),
[earlier workspace review](qa/reports/2026-11-14-fresh-review.md) and
[3 November integration verification](evidence/integration-verification.md) remain
historical checkpoints for their own source versions. Earlier smoke passes are
not fresh results for this release. This documentation refresh adds no local
runtime checks, live model requests or deployment checks; inspect hosted CI for
the published release SHA. Do not add counts across versions or
treat a key-free workflow check as live-model accuracy evidence.

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
The existing public deployment, archived checkpoints and refreshed final package
are separate release records. The deliberate `w13-final` update is documented
above; it does not establish a current deployment or Canvas resubmission.
