# NutriChat — Final technical brief and postmortem

**Team:** NutriChat · **Prepared:** 2026-11-15 · **Checkpoint:** `w13-final` on `test`

## 1. System and audience

NutriChat helps students and everyday home-food eaters estimate meal nutrients,
especially for Chinese dishes, then review confirmed meals across days. The final
slice is **sign in → describe → persist/enqueue → interpret/calculate → clarify or
correct → confirm/reload → private diary/trends**. Users can inspect the quantities,
reference recipes and sources behind an estimate. The product supports awareness;
it does not measure a meal's nutrients or prescribe a clinical diet.

## 2. Final architecture

The browser calls a FastAPI API. The API commits an account-owned analysis and
pending job together in PostgreSQL, then returns without waiting for model work.
A separate worker claims the pending job and calls the internal AI service over
HTTP. Qwen/HKUST extracts structured food facts; strict identity checks and Python
arithmetic determine results or missing-information questions. The worker saves
the outcome; browser polling reads saved state. The API owns review revisions and
confirmation. Confirmed meals and their consumption dates are locked.

PostgreSQL also holds users, hashed sessions, profiles and daily records. Alembic
migrations through `20261030_0010` support exercise and intake coverage alongside
accounts/profile/tracking. Profile references and diary/balance aggregation are
synchronous deterministic API work; profile measurements are not sent to the model.
The plain JavaScript interface separates Meals, Daily diary, Trends and My goals.
See [architecture](../../docs/architecture.md) and [ADRs](../../docs/adrs/).

## 3. AI's bounded role

The model interprets text, quantities, preparation and corrections using bounded
catalogue context. It is not the nutrition database, cannot approve a recipe and
does not write user records directly. Supported identities resolve through exact
names/reviewed aliases; an unverified item blocks all meal totals. Users can supply
actual known ingredients through a structured editor instead of trusting an
invented decomposition.

The catalogue has 200 USDA ingredient records and 350 reference recipes. Nutrient
values and identities are retained from `nutrichat`; explicit 50 g peeled-egg
portion/source metadata was added later. Basic mode labels defaults; Advanced
requires missing facts and recipe acceptance. Updating data/prompts does not train
model weights. The six-food offline fixture demonstrates the service path without
cloud access; it does not demonstrate real AI interpretation.

## 4. Evidence-based evaluation

| Dimension | Evidence and practical conclusion |
| --- | --- |
| Final verification | 1,230 backend, 56 frontend and 2 service smoke tests passed, plus fresh startup, migrations, durable lifecycle and restart checks. Independent live replay: 105 passed, 0 failed, 1 unmet assertion; 14 provider requests across both phases. See [final verification](../../docs/evidence/week13-verification.md) for source identity and limits. |
| Functionality | [14 November recipe follow-up](../../docs/qa/reports/2026-11-14-recipe-usability.md) records 1,208 backend tests, 56 frontend tests, eight successful exact replays after fixes, and a completed correction/confirmation journey. These are dated earlier checks. |
| Reliability | Controlled tests cover validation, ownership, revisions and arithmetic; live review retains failed extractions and unresolved wording. No overall model success rate or all-350-recipe accuracy sweep is claimed. |
| Performance | Async enqueue keeps model latency outside the immediate submission request. Finite provider/worker timeouts bound waits, but no throughput, load-capacity or latency service-level claim has been established. |
| Reproducibility | Docker Compose, migrations, versioned data and a no-key durable harness allow local reproduction. The required tag identifies the submitted source; logs identify their tested version. |
| Operations | Health probes, structured job-ID logs and an internal AI request counter make processing observable. Readiness alone does not validate model credentials/quota or end-to-end interpretation. |
| Privacy baseline | API ownership checks, opaque hashed sessions, private responses and server-side provider credentials separate accounts. Old ownerless meals remain inaccessible. This is not a production security audit. |

The [earlier 14 November workspace review](../../docs/qa/reports/2026-11-14-fresh-review.md)
and [3 November integration verification](../../docs/evidence/integration-verification.md)
retain different test scopes. Counts are never added across checkpoints. Saved
reference arithmetic is distinct from measured nutritional ground truth.

## 5. Engineering trade-offs

**Language flexibility versus verifiable arithmetic.** Models are useful for meal
interpretation, while recorded food identities and Python calculation provide a
reviewable boundary. Exact matching can reject valid but unlisted synonyms; that
cost is preferable to silently substituting a different dish.

**Convenience versus uncertainty.** Basic mode supplies labelled reference portions.
Advanced review allows explicit weights and recipe edits, but does not make
uncertain inputs accurate. Unsupported count units now ask for edible grams rather
than treating every piece as a full default serving.

**Durability versus operational completeness.** PostgreSQL jobs survive API request
completion and expose lifecycle evidence. The small prototype attempts a job once;
it lacks retry policy, lease recovery and idempotency. A worker crash after claim
can leave a job stuck. These gaps remain explicit rather than being hidden by reruns.

**Personalization versus overclaiming.** Private profiles support approximate adult
references. Manual daily calories replace meal totals; missing days stay gaps.
Exercise must be explicit, and self-reported intake coverage cannot verify omissions.
Current profiles can change historical displayed balances; historical target
snapshots and measured expenditure are out of scope.

## 6. Postmortem

The starter's case/API/database/worker structure became a meal-review product, then
an account-private diary with four focused panels. The main correction to the
initial design was to make uncertainty and food identity visible: a model-selected
catalogue ID was insufficient evidence that it matched the user's food.

Dated reviews found false extra foods from explanatory phrases, unsupported count
units becoming oversized portions, stale dependent balance displays and lost or
hidden correction state. Fixes narrowed interpretation rules, required explicit
unit references, refreshed dependent saved state and kept unsubmitted changes
visible. Recipe previews now precede optional edits; editing a batch clears its
acceptance. Evidence distinguishes repaired exact cases from unreplayed failures.

The team cut image-based estimation. Reusable personal recipes, password recovery,
account deletion, automatic retries/claim recovery and a new public deployment
remain outside this release. Broth-only consumption, household wording and model
response validity remain imperfect. Final review also retains a cold-cucumber
cooked-weight prompt and unverified millilitre conversion as explicit limitations. A successful retry or a large controlled test
suite does not prove those issues generally solved.

The practical lesson is to evaluate each boundary separately: input identity,
model extraction, calculation, persistence, visible review and operations. Tests
are most useful when they preserve an observed failure and its expected outcome;
a smooth demo alone would conceal the remaining uncertainty.

## 7. Next work with limited additional time

1. Add bounded error categories, idempotency and claimed-job recovery with
   interruption/duplicate/concurrent PostgreSQL tests before enabling retries.
2. Expand a fixed live evaluation set for unresolved household wording, selective
   consumption and count units; report every attempt without success-only reruns.
3. Rehearse backup/restore and review security/ownership/session controls before a
   separately authorized public deployment.
4. Have the team manually rehearse the seven-point demo and review the final
   evidence/tag before submitting Canvas; this package does not claim that occurred.

See the [final demo](DEMO.md), [operations](../../docs/operations.md) and
[AI Use Statement](AI_USE_STATEMENT.md).
