# Week 7 — Midterm Milestone Demo

## Team and checkpoint

- **Team:** NutriChat
- **Repository:** https://github.com/JunlangHuang004/Maie-6000c-starter-Junlang-Huang
- **Checkpoint tag:** `w07-midterm`
- **Primary artifact:** `submissions/week07/README.md`
- **Updated:** 2026-10-28
- **Checkpoint commit:** `93ad2074226e8e7c7dcd3df058605f8a233dca35`
- **Current demo branch:** https://github.com/JunlangHuang004/MAIE6000C-starter/tree/nutrichat

The pushed `w07-midterm` tag preserves the original checkpoint. The demo folder,
screenshots and extra verification tools were added later on `nutrichat`; they
are not present when checking out that older tag. Use the branch link above for
the supplementary guide, and keep the original checkpoint SHA identifiable.

| Member | Agreed responsibility |
| --- | --- |
| Junlang Huang | Lead development and feature integration |
| Jiacheng Cao | Supporting development |
| Zhou Ran | Documentation and deployment |
| Yixing Huang | Testing and validation |

These assignments were supplied by the team representative. They are responsibilities,
not a claim that each member personally performed every recorded check.

## 1. Direction and current working slice

People increasingly care about their health but often do not know the nutrition
of familiar meals. NutriChat helps students and busy home-food eaters estimate
calories, protein, fat and carbohydrates from descriptions, especially Chinese food.
It supports everyday awareness; recipe and portion assumptions prevent us from
claiming measured or medical accuracy.

The working slice is **describe → persist a queued meal/job → process asynchronously
→ save nutrition or questions → review/correct → confirm and reload**. Basic mode
uses visible reference portions and recipes when details are missing. Advanced mode
asks for edible weight, preparation, oil and editable recipe details. Questions
leave totals empty until resolved. Confirmed records cannot be edited.

The Qwen path has 138 USDA ingredient records and 250 project-authored reference
dishes. The model interprets language; validated Python arithmetic computes
nutrition. No model training is required. The no-key demo provider supports six
legacy English foods with explicit grams and is used for the reproducible worker demo.

## 2. Live demo sequence

For self-guided assessment, use [the dedicated TA demo](../../demo/README.md),
including its launcher, browser walkthrough and automated evidence check. The demo
is a runnable system documented on GitHub; no screen recording or in-person
presentation is required. The [earlier rehearsal guide](DEMO.md) remains available
for terminal-based inspection. The original `w07-midterm` tag remains unchanged;
the dedicated folder is a follow-up on `nutrichat`.

1. Start the configured Qwen demo and open `http://localhost:8003/app` directly;
   no account registration or login is required.
2. Enter a Chinese meal in Basic mode and review the interpreted foods, portions,
   recipe assumptions and nutrients.
3. Switch to Advanced and answer edible-weight, preparation and recipe questions.
   Required unanswered questions leave totals empty.
4. Correct a consumed portion in conversation, approve any remaining recipe
   questions and inspect the recalculated values.
5. Confirm, reload and compare the same record ID, confirmed status and totals.
   Follow the [illustrated sequence](../../demo/SCREENSHOT_GUIDE.md).
6. For supporting engineering evidence, run `python3 demo/run.py check` on the
   separate offline stack. It observes queued input in PostgreSQL with the worker
   paused, matching completion logs, a 155 → 310 kcal correction, confirmation
   and locked edits. The offline check does not prove Chinese-language extraction.

The Qwen route needs an authorized server-side model key. If none is available,
use the offline check and inspect the recorded Chinese walkthrough separately;
label that limitation and any live provider failures honestly.

## 3. Implementation status

| Status | Scope |
| --- | --- |
| Implemented | Durable API/job/worker/AI service integration; revision checks; dialogue, correction and confirmation; source-backed arithmetic; two modes; versioned food data; health/logs/metrics; optional HTTPS login deployment |
| Partially implemented | Chinese extraction depends on Qwen output quality; detailed inputs improve specificity but do not establish ground-truth accuracy; deployment exists but the public ECS has not been updated to this 250-dish milestone |
| Not implemented | Automatic job retries, recovery after worker crash, idempotency, individual account ownership, image recognition, monthly calorie-intake trends, personalized energy/macronutrient targets, clinical validation and measured cooking losses |

## 4. Architecture and change from the starter plan

We retained the course starter's API, PostgreSQL, durable job table, separate worker,
HTTP AI service, migrations and operational signals. The original case-triage path
remains available. The product-specific path now uses `analyses` and nutrition jobs,
with saved conversation/drafts/evidence, revision-based updates and confirmation.
The design evolved toward a bounded food catalogue and deterministic calculation
instead of accepting model-generated nutrient numbers. The latest expansion adds
reference dishes without changing the database schema.

See [architecture](../../docs/architecture.md), [the design decision](../../docs/adrs/0002-source-backed-dual-mode.md)
and [API contract](../../docs/api-contract.md).

## 5. Evidence of integration

| Boundary | Implementation and evidence |
| --- | --- |
| API → database | `services/api/app/main.py` commits analysis/job records; rehearsal captures both HTTP and PostgreSQL reads |
| Database → worker | `services/worker/app/main.py` claims pending jobs and records attempts/timestamps |
| Worker → AI service | Internal HTTP request to `services/ai/app/main.py`; the same worker path supports demo or Qwen |
| AI → calculated result | `services/common/` validates food mappings and calculates totals from versioned data |
| Result → review | GET restores persisted values; confirmation persists a timestamp; subsequent correction returns 409 |
| Operational signal | Readiness HTTP 200 and log events correlated by job ID |

Original checkpoint evidence and exact checks are linked in the
[Week 7 verification record](../../docs/evidence/week07-verification.md).
The [28 October demo verification](../../demo/VERIFICATION.md) separately records
the follow-up browser walkthrough, food/weight matrix and durable-storage checks.

## 6. Validation and its limits

- At the original tagged checkpoint, 359 unit/integration tests passed using the
  `pytest` console entry point used in CI; this fixes the previous
  `scripts.import_usda` collection failure.
- The 28 October demo follow-up passed 408 unit/integration tests and whole-repository
  Ruff locally. These include the demo verifier tests; application services were unchanged.
- The original repository runs CI on `main`; later `nutrichat` commits do not
  trigger push CI. The checkpoint CI result does not certify the newer demo commits.
- Fresh isolated PostgreSQL/HTTP rehearsal and smoke tests validate the durable workflow;
  see the verification record for exact outcomes and commands.
- Catalogue tests exercise every reference recipe in both modes. They verify the
  calculation contract, not Qwen extraction accuracy or real-world nutrition accuracy.
- Failure-path tests cover timeouts, HTTP errors, malformed results and state conflicts.
  SQLite unit/integration tests do not prove concurrent PostgreSQL locking.
- Provider results are recorded separately from deterministic checks. Historical
  successful subflows do not imply that every live-Qwen run passed.
- The live food/weight matrix passed 14 of 17 checks. Inputs of 0 g, -100 g and
  10001 g produced generic failures with no totals rather than useful input-specific
  guidance. A separate expanded dialogue failed once, then passed on one deliberate
  rerun. Both outcomes are retained in the follow-up verification record.

The coding assistant executed the recorded automated checks. Team rehearsal and
review before presentation remain a team responsibility; see the [AI Use Statement](AI_USE_STATEMENT.md).

## 7. Risks and revised scope

The main risk is inconsistent model extraction, compounded by uncertain recipes
and portions. We validate structured facts, show assumptions and ask questions;
we do not invent unsupported nutrition totals. Basic mode intentionally trades
precision for speed, while advanced mode requires more user input.

The latest live checks also expose generic error messages for invalid weights;
those cases need clearer validation/clarification. Successful normal examples do
not resolve that remaining issue or the lack of automatic retry and crash recovery.

The main scope cut is a fixed catalogue of mainstream reference dishes rather than
all regional variants or unconstrained recipes. If time becomes tight, we will
freeze catalogue growth and prioritize reliable correction, failure handling and
clear evidence. The shared-account deployment is a teaching prototype.

The team rejected image-based nutrition estimation and kept the current scope
focused on meal descriptions and clarification questions.

## 8. Week 7–13 priorities

| Period | Deliverable and acceptance condition | Responsible members |
| --- | --- | --- |
| Week 7–8 | Team rehearses both modes, reviews milestone evidence and records failures; verify final tag before submission | Yixing (testing), Junlang/Jiacheng (fixes), Zhou Ran (docs) |
| Week 8–9 | Expand the existing 17-case live probe into a fixed Chinese-meal evaluation set covering ambiguous weights, oil and recipe corrections; report extraction successes/failures separately from arithmetic | Yixing with Junlang/Jiacheng |
| Week 9–10 | Improve provider failure messages and bounded recovery design; test duplicate requests and interrupted jobs before enabling retries | Junlang with Jiacheng; Yixing validates |
| Week 10–11 | Deploy a verified release with backup/rollback rehearsal; review account/data-access limits before wider sharing | Zhou Ran with Junlang; Yixing validates |
| Week 11–12 | Collect usability feedback on basic defaults and advanced questions; fix high-impact issues and update limitations | Whole team, documentation by Zhou Ran |
| Week 13 | Freeze release, rerun acceptance checks and prepare final demonstration/report with reproducible evidence | Whole team |

These are proposed priorities, not claims of completed features.

Possible future extensions include monthly calorie-intake trends and personalized
estimates of energy and macronutrient needs based on user-provided basic
information. These are exploratory ideas, not implemented features or committed
milestone deliverables. We will consider them after stabilizing the core workflow.

## 9. Artifact index

- [Self-guided TA demo](../../demo/README.md): runnable setup, UI instructions and fresh evidence.
- [Screenshot guide](../../demo/SCREENSHOT_GUIDE.md): six illustrated Chinese-workflow steps.
- [Follow-up verification](../../demo/VERIFICATION.md): current tests, live failures and limitations.
- [Root README](../../README.md): quick start, modes and current verification.
- [Architecture](../../docs/architecture.md): services, states and boundaries.
- [Operations](../../docs/operations.md): startup, logs, tests and recovery limits.
- [Demo guide](DEMO.md): exact live sequence and fallback.
- [Verification record](../../docs/evidence/week07-verification.md): observed results and limits.
- [Lifecycle JSON](../../docs/evidence/week07-worker-lifecycle.json): synthetic HTTP/DB/log evidence.
- [Data provenance](../../docs/nutrition-data.md) and [250-dish index](../../docs/recipe-catalogue.md).
- [Change log](../../docs/change-log.md).
- [AI Use Statement](AI_USE_STATEMENT.md).

The live application and evidence above are the primary demo materials; no slides
or screenshots are required to reproduce this checkpoint.

## 10. AI assistance

OpenAI Codex assisted substantially with implementation, debugging, tests,
documentation and preparation; Alibaba Qwen is also a runtime component of the
application. The separate statement explains this distinction and records what
has and has not been verified by the team.
