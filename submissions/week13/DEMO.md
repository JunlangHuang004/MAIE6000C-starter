# Week 13 — Seven-point TA demo

This walkthrough demonstrates the seven final engineering-contract points on
`w13-final`. It combines a reproducible **offline engineering check** with a
separately labelled **real Qwen/HKUST meal workflow**. Expected outcomes below are
acceptance checks, not a claim that a new TA run has already passed. Actual release
results are in [final verification](../../docs/evidence/week13-verification.md).

## Prepare the tagged checkout and two isolated local projects

Use a clean checkout of the submitted repository, Docker running, Docker Compose
2.24.4+ and host Python 3.10+. From the repository root:

```sh
git fetch origin --tags
git checkout --detach w13-final
git rev-parse 'w13-final^{commit}'
python3 demo/run.py start
python3 demo/run.py check
```

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
timeout longer than the model timeout. Then run:

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
番茄炒蛋200克，熟米饭150克
```

Wait for saved completion or questions. Expand the food evidence and review the
interpreted identities/weights. **Expected semantic check:** tomato-and-egg stir-fry
200 g and cooked rice 150 g, with visible reference-recipe assumptions. With the
unmodified reference recipe, the project's arithmetic yields **405.2 kcal**
(210.2 + 195.0). A question may legitimately require clarification; a provider
failure is not a successful estimate and must not show fabricated totals.

While unconfirmed, switch to **Advanced**. Supply any required cooked/edible weight,
preparation or oil information. Inspect the whole-batch preview, then expand
**Review or adjust batch quantities**. Change the cooking oil from **15 g to 5 g**
in the reference batch and check that acceptance clears and the preview changes.
Switch to Chinese and back; the unsaved quantity and unchecked acceptance should
remain. Explicitly accept the reviewed recipe and submit the answers. With the
remaining batch unchanged, the expected saved total is **361.0 kcal** (166.0 for
the dish + 195.0 for rice). Review any provider interpretation or extra question
before accepting; a different result must be investigated, not silently relabelled.

Qwen/HKUST interprets natural language; Python supplies the nutrient calculation.
Structured answers use saved facts without another model call. Health probes or
a metric from the offline project alone cannot demonstrate this real AI step.
For dated examples and retained failures, see the
[14 November recipe review](../../docs/qa/reports/2026-11-14-recipe-usability.md).

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

- **My goals:** save synthetic adult inputs: age **30**, height **175 cm**,
  weight **75 kg**, male formula coefficient, light activity, muscle-gain goal.
  Expected daily energy reference: **2450 kcal**, with approximate assumptions
  shown. Profile entry is optional; these are test values, not dietary advice.
- **Daily diary:** today's confirmed meal should contribute to the automatic sum.
  Save weight **74.8 kg** and exercise **0**. Expand the manual-total control, save
  **2100 kcal**, and check that it replaces the **361 kcal** meal sum. Clear it and save to restore
  aggregation. Review the five-category intake checklist; mark categories only as
  a synthetic demonstration of self-reporting. A blank exercise value is unknown,
  while zero explicitly records none. Balance requires applicable profile/intake/
  exercise inputs and remains approximate.
- **Trends:** to make a two-date chart, first save yesterday's diary with weight
  **75.2 kg**, manual calories **2100**, and exercise **150**. Select today as the
  trend end date. With no other records in this fresh account, expect **2/30**
  calorie days, average **1230.5 kcal**, and weight change **−0.4 kg**. The other
  dates remain gaps. Daily weight does not update the profile automatically.
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
200 ingredients and 350 reference recipes. The user can use **Build from actual
ingredients** only when the ingredients and amounts are known; the app does not
invent the composition of the unknown dish.

Also state the operational limit plainly: jobs have finite timeouts and no automatic
retry, idempotency key or interrupted-claim recovery. A stopped worker can resume
pending work; a crash after claim can leave that job stuck. Do not demonstrate
recovery by deleting data or manually resetting states. Model output can fail
validation even after a successful upstream HTTP response. Reference recipes,
portions and daily balance remain approximate, and this local release does not
update the older public ECS deployment.

## Captured synthetic browser examples

These captures were made during final-package preparation on **15 November 2026**
using synthetic account/profile/meal records. They illustrate the observed local
system behavior, not measured food intake, a nutrition study or manual rehearsal
by every team member. The final verification record identifies the tested source
and any later regression fix separately.

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
Use the [Week 13 README](README.md) for the artifact index and full tagged commit
for Canvas. Fresh observations, failed attempts and any missing provider access
must remain separate from earlier recorded results. This runbook does not claim
that every team member has independently rehearsed it.
