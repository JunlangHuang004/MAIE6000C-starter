# NutriChat — Final technical brief and postmortem

**Team:** NutriChat · **Updated:** 2026-11-27 · **Release:** `w13-final`

Application source baseline: `1d17a66ffa445a5dc6a4d699e408c6772929ea79`.
Resolve `w13-final^{commit}` for the release including these final documents.
The earlier package at `6b87aef772f7cfde139a383c866e5576ea955cb3` is preserved
under `archive-w13-final-6b87aef`; its evidence retains its original scope.

## 1. System and audience

NutriChat helps students and everyday home-food eaters estimate meal nutrients,
especially for Chinese dishes, then review confirmed meals across days. The
implemented workflow is **sign in → describe → persist/enqueue → interpret and
calculate → clarify or correct → confirm/reload → private diary/trends**. Users
can inspect quantities, calculation choices and sources behind an estimate.
Unknown dishes have optional, explicitly reviewed reference-recipe recovery.
The product supports awareness; it does not measure the user's meal or prescribe
a clinical diet.

## 2. Architecture and implemented features

The plain JavaScript browser calls a FastAPI API. The API commits an account-owned
analysis and pending job together in PostgreSQL, then returns without waiting for
model work. A separate worker claims the job and calls the internal AI service
over HTTP. The configured Qwen/HKUST model extracts structured meal facts; strict
identity checks and deterministic Python calculation produce results or questions.
The worker saves the outcome, and browser polling reads saved state. The API owns
review revisions and confirmation. Confirmed meals and consumption dates are locked.

PostgreSQL also stores users, hashed sessions, profiles and daily records. Alembic
migrations run through **`20261121_0011`**, which adds nullable training and reference
scope answers without inventing answers for old profiles. The current profile
formula is **`mifflin-evidence-2026-v2`**. It uses explicit adult inputs, activity,
goal and training, with eligibility checks that withhold all targets when the
inputs fall outside the automatic-output policy. Missing answers are not false
answers, and successful arithmetic is not evidence of individual suitability.
Profile calculations run locally in Python; profile measurements are not sent to
the model. See [personalization](../../docs/personalization.md).

The bilingual interface has four panels: **Meals, Daily diary, Trends and My goals**.
Diary calories come from confirmed meals or a manual total that replaces the meal
sum. Weight, exercise and five-category intake coverage are separately recorded;
blank exercise is unknown, while zero records none. Approximate balance needs an
applicable profile, intake and explicit exercise. Completeness is self-reported.
Dates use **Asia/Hong_Kong**. Trends covers 30 consecutive dates, averages only
recorded calorie dates and compares the first and last recorded weights. Lines
connect observations at their date positions without filling missing values;
missing dates remain null, while explicit zero remains a record. Daily weight
does not update the profile. Current-profile changes can alter historical displayed
balances; historical target snapshots are not stored. See
[tracking](../../docs/tracking.md), [architecture](../../docs/architecture.md)
and [ADRs](../../docs/adrs/).

## 3. Nutrition provenance and AI boundaries

Catalogue **`2026-11-24.2`** contains **202 USDA ingredient records and 384
editable reference recipes**. All records have English names and all recipes have
English methods. USDA ingredient records retain source IDs and CC0 provenance.
The reference recipes are project-authored assumptions about composition, amounts
and cooked yield. The white-cut chicken correction uses an explicitly labelled
cooked-chicken proxy rather than the earlier raw-meat/yield assumption.

**Sixteen existing dishes** also carry attributed Hong Kong Centre for Food Safety
(CFS) prepared-food vectors. Basic uses the complete source vector scaled by cooked
edible weight for an ordinary matched dish. Advanced exposes a source-reference
versus editable-ingredient choice. Explicit ingredient/oil/yield facts, including
zero oil, use ingredient arithmetic; the app does not subtract oil from a CFS
average or mix its calories with recipe macros. The other 368 dishes have no CFS
vector in this catalogue and retain illustrative formulas. Saved basis/source
snapshots preserve historical results across catalogue changes. CFS averages are
not measurements of the user's dish, and the combined catalogue is not wholly CC0.

CFS available carbohydrate differs from USDA total carbohydrate. Mixed-definition
meals show separate labelled subtotals instead of a misleading combined number;
energy, protein and fat can still be reviewed and the meal confirmed. See
[nutrition data](../../docs/nutrition-data.md),
[CFS references](../../docs/cfs-prepared-food-references.md) and the
[20-dish source pilot](../../docs/evidence/cfs-pilot20-review.md).

The model interprets language; it is not the nutrition database, cannot approve
a recipe and cannot write user records directly. Exact supported names/reviewed
aliases establish identity. An unresolved food blocks all meal totals, including
known items' contributions. Basic defaults remain labelled assumptions; Advanced
requires missing facts and explicit ingredient-recipe review.

For an unknown name, the user can separately request optional name inference,
review/edit the guessed ingredients and method, and then request similar recipes.
Candidates must have **exactly the same main-ingredient IDs** and a compatible
method; species, cuts and raw/cooked states are not interchangeable. Seasonings
may differ. A valid response may contain no candidates. Selection requires an
approximation acknowledgement, then opens an **unaccepted ingredient draft**.
Ingredient acceptance, Python calculation and final meal confirmation are separate
steps; original names and reference provenance remain visible. Users can instead
enter known actual ingredients directly.

On this reference path, the model returns compact facts/IDs only. The server
generates display explanations, questions and ingredient differences from the
catalogue and reviewed facts. It rejects malformed/incomplete output without
repairing it into an accepted answer. Name inference and candidate ranking use
synchronous API-to-AI requests; the meal calculation still uses the durable worker
path. The latest recorded live provider is
**HKUST `gemini-2.5-flash-lite`**; Qwen and experimental Ollama alternatives are
separately configured. Updating prompts/data does not train model weights.
The six-food offline fixture proves the service path, not Chinese interpretation.
See [reference workflow](../../docs/similar-recipe-references.md).

## 4. Evidence-based evaluation

| Evidence | Observed result and practical limit |
| --- | --- |
| [24 November final automated checks](../../docs/evidence/name-reference-inference-verification.md#2026-11-24-name-grounding-and-preparation-safeguards) | **2,670 backend and 108 frontend tests passed**; Ruff and whitespace checks passed. The backend used the explicit offline configuration. These controlled checks do not measure live-provider or nutritional accuracy. |
| Hosted CI for application baseline | Checks passed for `1d17a66ffa445a5dc6a4d699e408c6772929ea79` in the [primary repository](https://github.com/JunlangHuang004/MAIE6000C-starter/actions?query=sha%3A1d17a66ffa445a5dc6a4d699e408c6772929ea79) and [mirror](https://github.com/JunlangHuang004/Maie-6000c-starter-Junlang-Huang/actions?query=sha%3A1d17a66ffa445a5dc6a4d699e408c6772929ea79). This does not establish CI for a later documentation/submission SHA. |
| 24 November live name/reference review | **49 model calls total**: 43 batch/manual calls, three diagnostics and three targeted post-fix calls. The initial 20 names produced three exact matches, three candidate successes, twelve clarifications and two errors. Manual shrimp clarification reached an acknowledged template; the thigh path initially errored. |
| After the final compact-output change | Three direct AI HTTP checks returned 200: eggplant ranking offered `dish_024`/`dish_154`; Three Cup Chicken inference clarified; thigh ranking returned no candidates. The expected nonempty thigh recovery was **not met**. These three checks are not a full rerun of the 20-name batch or of the browser workflow after the last change. |
| Source/reference checks | [CFS verification](../../docs/evidence/cfs-prepared-reference-verification.md), the [20-dish pilot](../../docs/evidence/cfs-pilot20-review.md) and [strict-reference audit](../../docs/evidence/strict-reference-verification.md) document different dated scopes. The strict audit's ingredient arithmetic predates the CFS default and must not be presented as current source-vector results. |
| [15 November historical package](../../docs/evidence/week13-verification.md) | 1,230 backend, 56 frontend and two service smoke tests, fresh migrations to the then-current `0010`, durable lifecycle and retained-volume restart checks. Independent live assertions: 105 passed, 0 failed, 1 unmet; 14 provider requests, plus a separate browser request. These are historical evidence, not reruns of this candidate. |

The latest 20 synthetic name-review meals remained unconfirmed, with no confirmed
dates or daily records, and the session was revoked. Failed attempts were retained;
there were no automatic retries. Counts across dates/subsets are not additive.
Account-specific 24 November transcripts remain outside Git; the repository holds
the sanitized report. The [15 November screenshots](DEMO.md#captured-synthetic-browser-examples)
are historical and predate the new features. No current full walkthrough or
independent human-team rehearsal is claimed by this documentation refresh.

Durable enqueue keeps model latency outside the immediate submission request.
Health probes, job-ID logs and an internal AI request counter expose processing;
readiness does not prove provider quota or interpretation quality. Ownership,
opaque hashed sessions and server-side credentials provide an application privacy
baseline, not a production security audit. No load-capacity, laboratory-nutrition
or all-384-recipe recognition result is established.

## 5. Engineering trade-offs and postmortem

**Language flexibility and identity.** Earlier reviews showed that a valid
model-selected catalogue ID could still misidentify a food. Exact name grounding,
preserved unknown names and explicit reference acceptance make that boundary
reviewable. Conservative ingredient/method checks also reject valid but ambiguous
names and can leave a reasonable reference unavailable.

**Reference convenience and source quality.** A consistent recipe calculation can
be far from a prepared-food sample. External source review prompted the cooked
chicken correction and CFS vectors rather than treating arithmetic tests as food
validation. CFS source selection, explicit ingredient edits and carbohydrate
definitions now remain separate and visible. Reference averages and assumed
portions still do not establish actual-meal accuracy.

**Model output and application text.** Live checks exposed invented ingredients,
wrong cuts/methods, an English dish title misread as a quantity and incomplete
ranking JSON. Name checks now preserve ambiguity; the reference model returns
facts/IDs while the server creates explanations. Targeted checks repaired the
observed response-format failures, but the final thigh no-match demonstrates that
a valid response need not be a useful recommendation.

**Durability and operational completeness.** Stored jobs survive request completion,
but the prototype attempts a job once. It has finite timeouts and no automatic
retry, idempotency key or interrupted-claim recovery. A stopped worker can process
pending work later; a crash after claim can leave that job stuck. Use one worker.

**Personalization and uncertainty.** v2 requires explicit scope/training answers
and withholds targets outside its policy. Diary overrides, unknown-versus-zero
values and recorded-day averages avoid fabricated observations. Self-reported
coverage and approximate expenditure still cannot establish a complete day or
predict weight change.

The team cut image-based estimation. Password recovery, account deletion, reusable
personal recipe libraries, automatic job recovery, historical target snapshots
and a new public deployment remain outside this candidate. Broth-only consumption,
household wording and model response validity remain imperfect. Historical review
also retains a cold-cucumber weight-state question and unverified millilitre
conversion; no later comprehensive resolution is claimed. A large controlled test
suite or a successful targeted replay does not remove those limits.

## 6. Release verification and next work

The [Week 13 README](README.md) records the agreed responsibilities, release
identity and artifact index. Resolve the refreshed `w13-final` tag, record its
full commit SHA and inspect hosted checks for that SHA. Use the
[seven-point demo](DEMO.md) from the same release. Earlier checks remain attributed
to their application baseline; the revised walkthrough is not a new runtime
observation. Canvas hand-in remains a separate team action.

With additional engineering time, prioritize bounded error categories, idempotency
and claimed-job recovery with interruption/concurrency checks; a fixed live set
that retains every attempt; and backup/restore plus security review before a new
public deployment. See [operations](../../docs/operations.md) and the
[AI Use Statement](AI_USE_STATEMENT.md).
