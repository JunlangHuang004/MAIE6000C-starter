# Week 13 — Seven-point TA demo

This final-release walkthrough covers the seven engineering-contract points
and the implemented features at source baseline
`1d17a66ffa445a5dc6a4d699e408c6772929ea79` (documentation updated 27 November 2026).
It combines a reproducible **offline engineering check** with a separately labelled
**real-provider meal workflow**. Expected outcomes are rehearsal checks, not a
claim that this revised walkthrough has been run.

The refreshed package uses `w13-final`. Its earlier checkpoint is preserved at
`archive-w13-final-6b87aef`, resolving to
`6b87aef772f7cfde139a383c866e5576ea955cb3`.
The [24 November checks](../../docs/evidence/name-reference-inference-verification.md#2026-11-24-name-grounding-and-preparation-safeguards)
and [15 November verification](../../docs/evidence/week13-verification.md) have
different scopes and must remain separately dated.

## Prepare the exact source and two isolated local projects

Use a clean checkout of the submitted repository, Docker running, Docker Compose
2.24.4+ and host Python 3.10+. From the repository root:

```sh
git fetch origin +refs/tags/w13-final:refs/tags/w13-final
git checkout --detach 'w13-final^{commit}'
git rev-parse HEAD
python3 demo/run.py start
python3 demo/run.py check
```

These commands refresh the previously moved assessment tag and reproduce the
application with its final documentation. Record the printed `HEAD` and compare it
with the full SHA submitted for assessment; use that submitted SHA if checking a
different historical hand-in. A later branch HEAD may differ from the tagged release.

The harness uses project `nutrichat-integrated-demo`, loopback port **8006**, a
separate PostgreSQL volume and **no private `.env` or model key**. It creates a
synthetic account, briefly stops only its own worker, checks the durable workflow
and revokes its session. Let it finish before manually submitting work in that
project. A successful run prints `PASS` and writes `demo/output/check.json`.
A failure remains recorded with its stage; do not present it as a pass.

For a second independent copy, set both `NUTRICHAT_DEMO_PROJECT` and
`NUTRICHAT_DEMO_PORT` consistently for start/check/stop. Port changes alone do not
isolate a database. Keep the generated check report separate from historical
committed evidence; running the check again creates another synthetic account/meal.

For the actual Chinese/AI demonstration, preserve existing private configuration:

```sh
test -f .env || cp .env.example .env
```

Set up **one** real Qwen or HKUST provider using the exact variables in the
[integration guide](../../docs/integration.md#select-a-model), including a worker
timeout longer than the model timeout. The latest recorded live review used
**HKUST `gemini-2.5-flash-lite`**; changing provider creates a different observation.
Then run:

```sh
docker compose -p nutrichat-merged-qwen --env-file .env \
  -f compose.yaml -f compose.integrated.yaml up -d --build --wait db ai api worker
```

Open [the integrated app](http://localhost:8005/app), use the same `localhost`
hostname throughout, select **English**, and register a dedicated synthetic account
(username: 3–32 ASCII letters/digits/underscores; password: 10–128 characters).
Keep credentials private. This project name is a local isolation convention;
check the selected provider rather than inferring it from the word `qwen`.

If provider access is unavailable, complete the fixture checks and inspect the
dated live evidence, explicitly identifying point 4 as **not freshly demonstrated**.
The fixture's six English foods and fixed arithmetic do not prove Chinese
interpretation. Do not switch to a different provider silently or replay failures
until one succeeds without retaining the failed attempts.

## 1. Input entering the system

Inspect the harness's real HTTP submission:

```sh
python3 - <<'PY'
import json
r = json.load(open('demo/output/check.json'))
assert r['passed'], r.get('failure', 'Check did not pass')
print(json.dumps({'passed': r['passed'], 'created': r['created']}, indent=2))
PY
```

**Expected:** `POST /analyses` returned HTTP **201** for `100g egg`, with an
analysis ID and a job ID. The request was authenticated as the harness's synthetic
account. This is an actual API call in the offline project, not a mocked HTTP test.
Use those same IDs when comparing later records.

In the integrated browser, open **Meals** and locate Basic/Advanced, the description
field and the estimate action. Explain that the same API accepts the browser input;
point 4 supplies its real Chinese model-backed example.

## 2. Persistence of state

```sh
python3 - <<'PY'
import json
r = json.load(open('demo/output/check.json'))
assert r['passed'], r.get('failure', 'Check did not pass')
print(json.dumps(r['before_worker'], indent=2))
PY
```

**Expected:** the PostgreSQL query made while the harness worker was stopped shows
analysis `queued`, job `pending`, `attempts: 0`, and all nutrient totals null. The
analysis/job IDs match point 1. The request has returned while state is already
stored; the worker has not yet calculated anything. The harness reads PostgreSQL,
not only the API response. Stopping this worker never stops the separate AI preview.

## 3. Background/worker processing

```sh
python3 - <<'PY'
import json
r = json.load(open('demo/output/check.json'))
assert r['passed'], r.get('failure', 'Check did not pass')
for key in ('initial_job', 'correction_job', 'worker_events'):
    print(key, json.dumps(r[key], indent=2))
PY
```

**Expected:** after the harness restarted its worker, each job completed with one
claim (`attempts: 1`), `claimed_at` and `completed_at`. Structured worker events
include `job_claimed` and `job_completed` for those IDs. The correction has a new
job ID. The API enqueues work; the separate worker performs it outside the request
cycle and calls the internal AI service over HTTP.

The fixture shows this service boundary, but its parser is deterministic. It is
not evidence of an external language-model call; that is the next point.

## 4. AI-enabled workflow step

In the real-provider app at **8005**, select **Meals → Basic** and submit exactly:

```text
虾仁炒蛋200克，熟米饭150克
```

Wait for saved completion or questions. Expand the food evidence and review the
interpreted identities/weights. **Expected semantic check:** scrambled egg with
shrimp (`dish_012`), 200 g cooked edible portion, and cooked rice, 150 g. The dish
uses its attributed **CFS prepared-food reference** in Basic mode; rice uses its
USDA record. Check that the dish's energy, protein and fat each equal its saved
per-100-g source value multiplied by two, with rice scaled by 1.5 before the meal
sum. Do not substitute a remembered screenshot total for this source check.
CFS available carbohydrate and USDA total carbohydrate are different definitions:
expect separately labelled subtotals, not one combined carbohydrate number. This
does not block the otherwise complete meal from review/confirmation. A question
may legitimately require clarification; a provider failure is not a successful
estimate and must not show fabricated totals.

While unconfirmed, switch to **Advanced**. Inspect the explicit choice between
the CFS prepared-food reference and the editable ingredient calculation. For the
editing demonstration choose the **ingredient** route, supply any required
cooked/edible weight or preparation information, and inspect the whole-batch
preview. Expand **Review or adjust batch quantities**. Change the reference batch
oil from **15 g to 5 g** and check that acceptance clears and the preview changes.
Switch to Chinese and back; the unsaved quantity and unchecked acceptance should
remain. Explicitly accept the reviewed recipe and submit the answers. Check the
saved basis and quantities against the reviewed preview: ingredient nutrients
are summed for the batch and scaled by consumed cooked weight / finished batch
weight. The rice stays unchanged. This is a new ingredient calculation; the app
must not subtract oil from a CFS average or keep CFS calories with ingredient
macros. Review any provider interpretation or extra question before accepting.

Qwen/HKUST interprets natural language; Python supplies the nutrient calculation.
Structured clarification/quantity answers use saved facts without another model
call. Optional name inference and reference ranking are separate explicit model
requests, covered in point 7. Health probes or a metric from the offline project
alone cannot demonstrate a real AI step. See the
[CFS source guide](../../docs/cfs-prepared-food-references.md) and its dated evidence.

## 5. Output surfaced or stored

In the same real-provider meal, select **Edit this meal**, type an unsent correction
and close the editor. **Expected:** the draft persists and confirmation is blocked
until the correction is submitted or cleared. Reopen it and clear the unsent
text. Review the current estimate, choose today's Hong Kong consumption date,
confirm and reload. **Expected:** the same saved ID, confirmed state, date and
nutrients remain; editing that meal/date is unavailable.

Inspect the fixture's repeatable saved-output comparison as well:

```sh
python3 - <<'PY'
import json
r = json.load(open('demo/output/check.json'))
assert r['passed'], r.get('failure', 'Check did not pass')
for key in ('initial_result', 'corrected_result', 'confirmed', 'reloaded',
            'after_confirmation', 'locked_edit'):
    print(key, json.dumps(r[key], indent=2))
PY
```

**Expected fixture checks:** 100 g egg is **155 kcal**, a full-description correction
to 200 g is **310 kcal**, confirmed HTTP output equals the reload, PostgreSQL agrees,
and a later edit returns **409** without changing the meal. These are legacy
six-food fixture values; do not present them as validation of live model extraction.

In the real app, verify the four panels and private tracking:

- **My goals:** save synthetic adult inputs: age **25**, height **175 cm**,
  weight **70 kg**, male formula coefficient, moderate activity, muscle-gain goal,
  strength training **Yes**, and the **general adult** reference scope. Expected
  v2 energy reference: **2720 kcal**, with the calculation basis, sources and assumptions
  shown. Select and save the professional-guidance/uncertain scope to demonstrate
  that targets are withheld, then restore the general-adult answer. The browser
  requires both selections; older saved profiles with missing answers need these
  confirmations too; blank is not a negative training answer. Profile entry is
  optional; these are test inputs, not dietary advice.
- **Daily diary:** today's confirmed meal should contribute to the automatic sum.
  Save weight **74.8 kg** and exercise **0**. Expand the manual-total control, save
  **2100 kcal**, and check that it replaces the current meal sum. Clear it and save
  to restore aggregation, then save **2100 kcal** again for the fixed trend check
  below. Review the five-category intake checklist; mark categories only as
  a synthetic demonstration of self-reporting. A blank exercise value is unknown,
  while zero explicitly records none. Balance requires applicable profile/intake/
  exercise inputs and remains approximate.
- **Trends:** to make a two-date chart with a missing day between observations,
  save the diary for **two days before today** with weight **75.2 kg**, manual
  calories **2300**, and exercise **150**. Leave yesterday empty. Select today as the
  trend end date. With no other records in this fresh account, expect **2/30**
  calorie days, average **2200 kcal**, and weight change **−0.4 kg**. The average
  divides by the two recorded calorie dates, not 30. Lines connect the recorded
  points at their actual date positions; yesterday stays null in the detail table,
  not zero or an interpolated value. Explicit zero would count as a recorded value.
  Dates use Asia/Hong_Kong, and the window is 30 days rather than a calendar month.
  Daily weight does not update the profile automatically.
- Before signing out, expand the confirmed meal's record details and copy its ID.
  Sign out and register a second synthetic account. Its meals, profile and tracking
  start independently. In a new tab, open
  `http://localhost:8005/analyses/ANALYSIS_ID`, replacing `ANALYSIS_ID` with that
  copied ID. **Expected:** the second account receives **404**. Sign back into the
  first account to restore its saved history.

## 6. Operational signals

```sh
python3 demo/run.py status
python3 - <<'PY'
import json
r = json.load(open('demo/output/check.json'))
assert r['passed'], r.get('failure', 'Check did not pass')
print(json.dumps({
    'health': r['stack']['health'],
    'ai_requests_before': r['ai_requests_before'],
    'ai_requests_after': r['ai_requests_after'],
    'ai_requests_delta': r['ai_requests_delta'],
    'session_revoked': r['session_revoked'],
}, indent=2))
PY
```

**Expected:** API/PostgreSQL readiness is HTTP **200**, the internal AI request
counter increased by at least **2** for the initial calculation and correction,
and the harness revoked its synthetic session. Point 3's logs correlate the
same job IDs. These measures describe service activity, not correctness of every
model answer or model-account access.

For the real-provider project, inspect recent logs locally:

```sh
docker compose -p nutrichat-merged-qwen --env-file .env \
  -f compose.yaml -f compose.integrated.yaml logs --tail=60 api worker ai
```

Do not share credentials or private meal/account data in copied logs. API readiness
checks PostgreSQL; AI readiness checks the service, without testing provider quota.

## 7. One honest limitation, failure or trade-off

Start a new **Basic** meal in the real-provider app:

```text
100克白米饭，200克月球紫晶兽肉
```

**Expected:** the unknown item is unresolved and **all** meal nutrient totals are
withheld, including the known rice's contribution to the total. No similar dish
may replace the invented food. If the provider fails instead, report that outcome
as a provider failure rather than claiming the intended unsupported-food check
passed. Retain the exact wording, state and runtime version.

Explain the trade-off: exact supported-name matching can reject unlisted valid
synonyms, but it avoids an unsupported substitute estimate. Coverage is finite at
**202 USDA ingredients and 384 reference recipes**, with attributed CFS vectors
on **16** of those recipes. Source averages do not measure this user's meal.
The user can use **Build from actual ingredients** when ingredients and amounts
are known; the app does not invent the composition of the unknown dish.

To demonstrate the optional recovery path, create a separate unconfirmed meal
`香煎豆腐200g` and expand **Find a similar recipe**. Explicitly request name
inference, inspect the editable guessed ingredients/method, then separately
request candidates after reviewing them. A clarification or no-match result is
valid. Any offered recipe must have exactly the same main-ingredient IDs and a
compatible cooking method; seasonings may differ. The model returns facts/IDs;
the server creates the displayed explanations from catalogue evidence.

If a candidate is offered, selection requires an approximation acknowledgement.
It opens an **unaccepted ingredient draft**, still without meal totals. Review
ingredients, grams, batch yield and consumed portion, then accept that recipe.
Only Python calculation produces nutrients; confirming the meal is a later,
separate action. Keep this example unconfirmed so it does not alter the diary
check. The original unknown name and approximate-reference provenance remain.
Do not force a candidate or turn a failed provider request into a successful
demonstration. The [latest name review](../../docs/evidence/name-reference-inference-verification.md#2026-11-24-name-grounding-and-preparation-safeguards)
retains a thigh example whose final request succeeded but returned no candidates.

Also state the operational limit plainly: jobs have finite timeouts and no automatic
retry, idempotency key or interrupted-claim recovery. A stopped worker can resume
pending work; a crash after claim can leave that job stuck. Do not demonstrate
recovery by deleting data or manually resetting states. Model output can fail
validation even after a successful upstream HTTP response. Reference recipes,
portions and daily balance remain approximate, and this local release does not
update the older public ECS deployment.

## Captured synthetic browser examples

These **historical** captures were made during the earlier package preparation on
**15 November 2026** using synthetic account/profile/meal records. They illustrate the observed local
system behavior, not measured food intake, a nutrition study or manual rehearsal
by every team member. They predate the v2 profile, catalogue expansion, CFS choices,
reference workflow and later trend changes. Their numbers describe that old run;
they are not current acceptance expectations or new screenshots of this candidate.

| View | Captured check |
| --- | --- |
| [Basic meal](images/01-basic-estimate.png) | Tomato/egg 200 g + cooked rice 150 g, 405.2 kcal reference estimate |
| [Advanced review](images/02-advanced-review.png) | Editable whole-batch recipe and explicit acceptance |
| [Confirmed meal](images/03-confirmed-meal.png) | Reviewed 361 kcal meal after batch oil changed from 15 g to 5 g |
| [Daily diary](images/04-diary.png) | Dated synthetic intake, weight, exercise and approximate balance |
| [Trends](images/05-trends.png) | Two recorded dates, 1230.5 kcal recorded-day average and −0.4 kg measurement difference |
| [My goals](images/06-profile.png) | Synthetic profile and 2450 kcal approximate daily reference |
| [Narrow-screen meal](images/07-mobile-meal.png) | Responsive browser layout; not a physical-device study |

## Finish and hand-in

```sh
python3 demo/run.py stop
docker compose -p nutrichat-merged-qwen --env-file .env \
  -f compose.yaml -f compose.integrated.yaml stop
```

Both commands retain database volumes. Do not use `down -v` as routine cleanup.
Use the [Week 13 README](README.md) for the artifact index and release status.
Record the exact submitted commit for Canvas. Fresh observations, failed attempts and any missing provider access
must remain separate from earlier recorded results. This runbook does not claim
that every team member has independently rehearsed it.
