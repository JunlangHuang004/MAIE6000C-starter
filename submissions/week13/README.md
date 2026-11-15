# Week 13 — NutriChat final team project

- **Team:** NutriChat
- **Repository:** [MAIE6000C-starter](https://github.com/JunlangHuang004/MAIE6000C-starter)
- **Repository mirror:** [Maie-6000c-starter-Junlang-Huang](https://github.com/JunlangHuang004/Maie-6000c-starter-Junlang-Huang)
- **Release branch:** `test`
- **Required checkpoint tag:** `w13-final`
- **Prepared:** 2026-11-15
- **Release verification:** [final check record](../../docs/evidence/week13-verification.md)

Use the required tag for assessment; branch HEAD may advance later. Resolve the
commit referenced by the tag, not the annotated tag object's SHA:

```sh
git fetch origin --tags
git rev-parse 'w13-final^{commit}'
```

Use that full commit SHA, the repository URL and `w13-final` in the Canvas hand-in.
The primary artifacts are this README, the root README, architecture, operations
and ADRs. Publishing Git branches/tags does not submit Canvas. The existing
`nutrichat` branch, `w07-midterm` tag and public ECS deployment remain separate
snapshots; the final package is a local reproducible application, not a new
public deployment.

| Member | Agreed responsibility |
| --- | --- |
| Junlang Huang | Lead development and feature integration |
| Jiacheng Cao | Supporting development |
| Zhou Ran | Documentation and deployment |
| Yixing Huang | Testing and validation |

These are the team representative's assigned responsibilities. Recorded
assistant-run checks do not establish that each member personally ran them.

## 1. Final supported workflow

NutriChat helps users estimate calories, protein, fat and carbohydrates from meal
descriptions, especially Chinese meals. A signed-in user describes a meal; the
API persists its input and job; a separate worker calls the internal AI service;
Qwen or HKUST interprets the text; deterministic Python validates identities and
calculates from versioned food data. The user reviews assumptions, answers
questions, corrects the estimate and confirms a meal/date that is then locked.

Basic mode uses labelled reference portions/recipes for supported foods. Advanced
mode requests missing weights, preparation/oil details and explicit recipe review.
Unknown food identity or required unanswered questions withhold all meal totals.
A structured actual-ingredient editor can replace an unknown item when the user
knows its ingredients and weights. It is not a reusable personal recipe library.

The catalogue has **200 USDA ingredient records and 350 reference recipes**. Food
identities and nutrient values are retained from `nutrichat`; later metadata adds
an explicit 50 g reference for one large peeled hard-boiled egg. This is not a
byte-for-byte catalogue preservation claim or a measurement of a user's portion.

Four panels separate Meals, Daily diary, Trends and My goals. Accounts have private
meal history, profiles and dated records. Optional deterministic profile formulas
provide approximate daily references. Diary supports confirmed-meal sums, manual
totals that replace those sums, weight, exercise, intake coverage and approximate
energy balance. Trends shows 30 days with gaps for absent records. Panel/language
switches preserve unsaved entries without submitting them; save before reloading.

## 2. Exact final demo order

Follow [DEMO.md](DEMO.md) for commands, browser inputs and expected checks:

1. Input entering the system: register/sign in and submit a meal through the API/UI.
2. Persistence of state: inspect queued analysis and pending job rows in PostgreSQL.
3. Background processing: observe the separate worker's claim/completion evidence.
4. AI-enabled workflow: run a real Qwen/HKUST interpretation, clearly separated
   from the deterministic six-food offline fixture.
5. Output surfaced or stored: review, correct, confirm and reload saved results;
   inspect account-private diary/trends.
6. Operational signals: inspect readiness, matching structured logs and the internal
   AI request counter.
7. Honest limitation/failure/trade-off: demonstrate unsupported-food blocking and
   explain catalogue uncertainty, provider failures and absent automatic recovery.

## 3. System components

| Component | Responsibility |
| --- | --- |
| Browser, plain JavaScript | Bilingual four-panel workspace, polling, reviewed edits and charts |
| FastAPI API | Authentication/ownership, validation, durable enqueue, revision checks, confirmation, deterministic profile/tracking work |
| PostgreSQL / Alembic | Users/sessions, profiles/daily records, analyses and durable jobs; migration head `20261030_0010` |
| Worker | Claims pending jobs, calls internal AI HTTP endpoint, persists results/questions/errors |
| Internal AI service | Qwen/HKUST extraction, strict catalogue identity checks and Python calculation; key-free fixture or experimental Ollama alternatives |
| Docker Compose | Isolated reproducible local deployment with internal database/AI network boundaries |

## 4. Testing and verification

Final local checks passed: **1,230 backend tests, 56 frontend tests, 2 service
smoke tests**, Ruff, clean-start migrations, the durable lifecycle harness and
retained-volume restart checks. The independent live review made 14 provider
requests across initial attempts and deliberate post-fix replays, with no automatic
retries. Post-fix assertions: **105 passed, 0 failed, 1 unmet** (cold-cucumber
completed arithmetic). Mixed-volume input remains outside verified support.

The implementing reviewer separately verified the visible browser workflow and
captured seven screenshots. These are assistant-run checks, not a claim of team
rehearsal or measured nutrition accuracy. See the
[Week 13 verification record](../../docs/evidence/week13-verification.md) and
[evidence directory](../../docs/evidence/week13/) for source fingerprints, failures,
repairs and practical limits. Hosted CI must be checked for the submitted SHA.

The strongest earlier evidence is separately dated:

| Evidence | Scope and limitation |
| --- | --- |
| [14 November recipe-usability follow-up](../../docs/qa/reports/2026-11-14-recipe-usability.md) | 1,208 backend and 56 frontend tests; eight exact post-fix recipe replays; real browser review/correction/confirmation; unresolved model/language cases retained |
| [Earlier 14 November workspace review](../../docs/qa/reports/2026-11-14-fresh-review.md) | Four panels, account/profile/tracking checks, 117 final HTTP assertions and separate browser observations on its labelled runtime |
| [3 November integration verification](../../docs/evidence/integration-verification.md) | Earlier merge tests, PostgreSQL upgrade, account ownership and live provider/restart evidence |

Counts from different versions are not additive. Controlled tests validate code
and arithmetic; offline checks validate durable boundaries; live samples test
specific model interactions. None establishes all-food accuracy, measured
nutrition, load capacity, a security audit or successful hosted CI for a later SHA.

## 5. Reproducibility and operations

Start with the [root README](../../README.md) and [operations](../../docs/operations.md).
Docker Compose 2.24.4+ runs API, worker, AI and PostgreSQL. The ordinary integrated
preview is project `nutrichat-merged-qwen` on loopback port **8005**; the separate
key-free check defaults to `nutrichat-integrated-demo` on **8006**. A second copy
needs both a distinct project and a free port. Preserve `.env` and database volumes.

Real Chinese interpretation requires private valid Qwen/HKUST configuration,
network access and quota. No credentials are distributed. The six-food offline
fixture accepts explicit English gram inputs and does not interpret Chinese or
free-text corrections. Health checks do not prove model access.

## 6. Known limitations

- Coverage is finite; unlisted foods/synonyms cannot receive a substitute dish's
  totals. Portion defaults, recipe composition and energy formulas are assumptions.
- Model extraction can fail or misread quantities/preparation. Provider timeout,
  invalid output, access and quota errors can produce failed jobs without totals.
- Mixed millilitre/gram wording was not accepted or repaired in the final review;
  supply edible grams rather than assuming a liquid's millilitres equal grams.
  Some cold reference dishes still require weight-state clarification.
- Jobs have no automatic retry, interrupted-claim recovery or idempotency key.
  A repeated submission creates a separate record/job. Use one worker.
- No password recovery, Google login, account deletion, personal recipe library or
  historical target snapshot. Old shared meals retain null ownership.
- Profile references and daily balance are approximate. Incomplete intake can
  exaggerate a deficit; exercise zero differs from unknown. Daily weight does not
  update the profile automatically.
- Final source publication does not update the older public ECS service. New public
  deployment, broad security/load review and independent human-team rehearsal are
  not claimed by this package.

## 7. Final artifact index

| Artifact | Purpose |
| --- | --- |
| [Root README](../../README.md) | Product scope, setup and current workflow |
| [Architecture](../../docs/architecture.md) | Components, state ownership, privacy and failure boundaries |
| [Operations](../../docs/operations.md) | Run, verify, diagnose, migrate and retain data |
| [ADRs](../../docs/adrs/) | Starter stack, source-backed nutrition and private-tracking/release decisions |
| [Seven-point demo](DEMO.md) | Exact TA workflow and expected checks |
| [Final technical brief and postmortem](final-technical-brief.md) | Evaluation, trade-offs, changes and remaining work |
| [Final verification](../../docs/evidence/week13-verification.md) | Release checks and linked raw evidence |
| [Final browser examples](DEMO.md#captured-synthetic-browser-examples) | 15 November synthetic local meal, diary, trends, profile and responsive captures |
| [Earlier illustrated walkthrough](../../demo/INTEGRATED_GUIDE.md) | Dated earlier browser captures, with their original scope |
| [AI Use Statement](AI_USE_STATEMENT.md) | Tools, material influence, verification and responsibility |

## 8. AI use and responsibility

OpenAI Codex assisted implementation, tests, debugging, documentation and evidence
collection. Qwen/HKUST provide runtime meal interpretation; nutrient calculation is
versioned Python arithmetic. The team specified scope and responsibilities and
remains responsible for understanding and submitting the work. See the concise
[AI Use Statement](AI_USE_STATEMENT.md); it does not claim unrecorded manual team
verification or rehearsal.
