# Week 13 — NutriChat final project package

- **Team:** NutriChat
- **Repository:** [MAIE6000C-starter](https://github.com/JunlangHuang004/MAIE6000C-starter)
- **Mirror:** [Maie-6000c-starter-Junlang-Huang](https://github.com/JunlangHuang004/Maie-6000c-starter-Junlang-Huang)
- **Current default/release branch:** `nutrichat`; `test` remains a development branch.
- **Documentation revised:** 2026-11-27
- **Application baseline:** `1d17a66ffa445a5dc6a4d699e408c6772929ea79`
- **Assessment release tag:** `w13-final` — application and refreshed final documents.

## 1. Version and hand-in status

This updated final package includes the implemented accounts, tracking, expanded
food data, personal references and similar-recipe features on `nutrichat`.
It supersedes the earlier final-document scope on this branch.

The 27 November release aligns `w13-final` in both repositories with this expanded
package on `nutrichat`. The earlier checkpoint is preserved at
**`archive-w13-final-6b87aef`**, resolving to
`6b87aef772f7cfde139a383c866e5576ea955cb3`. Its dated evidence keeps that older scope.

Because the assessment tag was updated, an existing clone may still hold its old
value. Refresh this specific tag, check out the release and record its full commit
SHA. The annotated tag object's ID is not the commit SHA:

```sh
git fetch origin +refs/tags/w13-final:refs/tags/w13-final
git checkout --detach 'w13-final^{commit}'
git rev-parse HEAD
git rev-parse 'w13-final^{commit}'
```

The application baseline above identifies the code reviewed for this revision;
the release commit also includes the refreshed documentation. Use the same resolved
release commit in the team hand-in and inspect hosted CI for that SHA. A later
branch HEAD may differ from the assessment tag. Git publication does not deploy ECS
or submit or change a Canvas hand-in.

## 2. Team responsibilities

| Member | Agreed responsibility |
| --- | --- |
| Junlang Huang | Lead development and feature integration |
| Jiacheng Cao | Supporting development |
| Zhou Ran | Documentation and deployment |
| Yixing Huang | Testing and validation |

These are the agreed project responsibilities. The evidence below distinguishes
assistant-run checks from individual human-team validation.

## 3. Implemented final scope

| Area | Current behavior |
| --- | --- |
| Estimation | Chinese/English descriptions; Basic uses labelled supported-food reference portions/recipes, Advanced requests missing facts and explicit recipe review |
| Data | Catalogue `2026-11-24.2`: **202 USDA ingredients and 384 editable reference recipes**, English names for all 586 records; **16 existing dishes** also have attributed CFS prepared-food references |
| Calculation | Python computes from versioned source vectors or accepted ingredient recipes; the model does not invent nutrient totals |
| Unknown foods | Remain unresolved with no whole-meal total; users can correct names, enter actual ingredients or explicitly request similar-recipe assistance |
| Similar references | Name inference, ingredient/method checks, clarification, exact main-ingredient-set filtering, reference acknowledgement and separate ingredient/meal acceptance |
| Accounts | Registration, sign-in/out, expiring revocable sessions and account-owned meal/profile/diary records |
| Personal references | Age, height, weight, formula sex coefficient, activity and gain/loss goal; versioned eligibility/training checks may withhold a target; calculation is deterministic |
| Diary | Consumption-date aggregation of confirmed meals, optional manual calorie replacement, weight, exercise and self-reported intake coverage |
| Trends | 30-day window; lines connect recorded observations, missing values remain null and are excluded from recorded-day averages; explicit zero remains a recorded value |
| Interface | Four bilingual panels: Meals, Daily diary, Trends and My goals; panel/language changes preserve unsaved values |

The 16 CFS references overlap the 384 dishes; they are not additional food records.
CFS source vectors and editable recipe calculations retain separate provenance and
carbohydrate semantics. Most recipes remain illustrative estimates, not measured
dishes. Catalogue updates do not recalculate saved historical meals. See
[data sources](../../docs/nutrition-data.md), [CFS references](../../docs/cfs-prepared-food-references.md)
and [reference boundaries](../../docs/similar-recipe-references.md).

## 4. Workflow and architecture

1. A signed-in user submits a meal. FastAPI commits an account-owned analysis and
   pending job together in PostgreSQL, then returns their IDs.
2. A separate worker claims the job, calls the internal AI service and saves the
   outcome. Qwen/HKUST interprets language; identity checks and Python arithmetic
   produce a reviewable result or questions.
3. Browser polling reads saved state. Users clarify or correct the estimate.
   A completed job can still leave its analysis needing user input.
4. Users confirm a completed revision and consumption date. The locked record
   survives reload and contributes to that account's dated intake.
5. Profiles and tracking are synchronous deterministic API work. Name inference
   and reference ranking synchronously call the internal AI service without worker
   jobs. Selection saves only an unaccepted template; accepting actual ingredients
   enters the existing recalculation path. Meal confirmation is still separate.

The queue is the PostgreSQL `jobs` table, not Redis/Celery. Nutrition records are
versioned JSON; PostgreSQL holds user/application state. Alembic head is
**`20261121_0011`**. Compose separates API, worker, AI and database; only AI receives
private provider credentials. See [architecture](../../docs/architecture.md).

## 5. Verification and limits

| Evidence | What it establishes |
| --- | --- |
| Latest automated checks | **2,670 backend unit/integration tests and 108 frontend tests passed**, plus Ruff and whitespace checks; see the [hardening report](../../docs/evidence/name-reference-inference-verification.md#2026-11-24-name-grounding-and-preparation-safeguards) |
| Hosted CI at baseline | Both repositories passed at `1d17a66`: [primary](https://github.com/JunlangHuang004/MAIE6000C-starter/actions/runs/45432657799), [mirror](https://github.com/JunlangHuang004/Maie-6000c-starter-Junlang-Huang/actions/runs/45432571920) |
| Bounded live audit | 20 names, two manual follow-ups, diagnostics and three post-fix AI checks: **49 provider calls**, no automatic retries; first failures retained |
| Final targeted checks | Eggplant returned references; Three Cup Chicken requested clarification; thigh ranking returned valid empty candidates, so its nonempty-recovery expectation remained unmet |
| Historical checkpoint | [15 November verification](../../docs/evidence/week13-verification.md): 1,230 backend, 56 frontend and two smoke tests, plus durable/restart checks, for its earlier source; not rerun by this documentation update |

The whole 20-name batch was not replayed after the last compact-output change.
All 20 audit analyses remained unconfirmed with zero diary intake. These are
assistant-run checks, not proof of individual human-team rehearsal. Counts across
versions are not additive. Controlled responses, offline fixtures, real model calls
and measured nutritional ground truth are distinct forms of evidence.

Remaining limits include finite coverage, imperfect interpretation, conservative
no-match results, uncertain portions/oil/yields, unsupported volume-to-mass
assumptions and incomplete intake. There is no image analysis, model training,
Google login, password-reset flow, account-deletion UI, reusable personal recipe
library or historical target snapshot. Jobs have no automatic retry, interrupted-
claim recovery or idempotency key; use one worker. Health checks do not prove
provider access/quota. New public ECS deployment and production load/security
validation are not established by these checks.

## 6. Artifact index and release preparation

| Artifact | Purpose |
| --- | --- |
| [Root README](../../README.md) | Current features and quick start |
| [Seven-point demo](DEMO.md) | Input, persistence, worker, AI, saved output, signals and limitations |
| [Architecture](../../docs/architecture.md) / [ADRs](../../docs/adrs/) | Components, boundaries and trade-offs |
| [Operations](../../docs/operations.md) / [integration setup](../../docs/integration.md) | Configure, migrate, run, inspect and retain data |
| [Technical brief](final-technical-brief.md) | Design decisions, evaluation and postmortem |
| [Name/reference verification](../../docs/evidence/name-reference-inference-verification.md) | Dated audit, fixes, failures and targeted checks |
| [Historical verification](../../docs/evidence/week13-verification.md) | Earlier checkpoint evidence |
| [AI Use Statement](AI_USE_STATEMENT.md) | Development assistance, runtime AI, verification and responsibility |

Follow the guides for an isolated offline project on port 8006 and real-model
preview on port 8005. A second copy requires a distinct project name and free port.
Preserve private `.env` files and database volumes. Verify the final submitted
SHA/tag and its hosted CI before hand-in. Expected demo outcomes
and historical screenshots must remain separate from newly observed results.
