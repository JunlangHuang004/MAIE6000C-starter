# Week 7 — Midterm Milestone Demo

## Team and checkpoint

- **Team:** NutriChat
- **Repository:** https://github.com/JunlangHuang004/Maie-6000c-starter-Junlang-Huang
- **Checkpoint tag:** `w07-midterm`
- **Primary artifact:** `submissions/week07/README.md`
- **Updated:** 2026-10-27
- **Mirror:** https://github.com/JunlangHuang004/MAIE6000C-starter/tree/nutrichat

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

Use the [rehearsal guide](DEMO.md); slides are optional and cannot replace the live path.

1. With the isolated worker stopped, send `100g egg` to `POST /analyses`; show HTTP 201
   with analysis and job IDs.
2. Query PostgreSQL: the meal is `queued`, the job is `pending`, and totals are null.
3. Start the worker; show the matching `job_claimed` and `job_completed` log events.
4. Read the saved result through HTTP and PostgreSQL: 155 kcal in the legacy demo
   catalogue, plus all three macronutrients. Confirm, reload and show a rejected edit.
5. Show `/health/ready`, the saved job timestamps and the evidence record.
6. If Qwen is available, demonstrate Chinese basic estimation, switch to advanced,
   answer recipe questions, correct quantities and confirm. Label provider failures
   honestly; the offline demo is not evidence of Chinese-language extraction.

## 3. Implementation status

| Status | Scope |
| --- | --- |
| Implemented | Durable API/job/worker/AI service integration; revision checks; dialogue, correction and confirmation; source-backed arithmetic; two modes; versioned food data; health/logs/metrics; optional HTTPS login deployment |
| Partially implemented | Chinese extraction depends on Qwen output quality; detailed inputs improve specificity but do not establish ground-truth accuracy; deployment exists but the public ECS has not been updated to this 250-dish milestone |
| Not implemented | Automatic job retries, recovery after worker crash, idempotency, individual account ownership, image recognition, clinical validation and measured cooking losses |

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

Fresh machine-readable evidence and exact checks are linked in the
[Week 7 verification record](../../docs/evidence/week07-verification.md).

## 6. Validation and its limits

- 359 unit/integration tests passed using the `pytest` console entry point used in CI;
  this fixes the previous `scripts.import_usda` collection failure.
- Ruff checks the whole repository. The original repository runs CI on `main`;
  the fork mirrors the same commit on `nutrichat`, which does not trigger push CI.
- Fresh isolated PostgreSQL/HTTP rehearsal and smoke tests validate the durable workflow;
  see the verification record for exact outcomes and commands.
- Catalogue tests exercise every reference recipe in both modes. They verify the
  calculation contract, not Qwen extraction accuracy or real-world nutrition accuracy.
- Failure-path tests cover timeouts, HTTP errors, malformed results and state conflicts.
  SQLite unit/integration tests do not prove concurrent PostgreSQL locking.
- Provider results are recorded separately from deterministic checks. Historical
  successful subflows do not imply that every live-Qwen run passed.

The coding assistant executed the recorded automated checks. Team rehearsal and
review before presentation remain a team responsibility; see the [AI Use Statement](AI_USE_STATEMENT.md).

## 7. Risks and revised scope

The main risk is inconsistent model extraction, compounded by uncertain recipes
and portions. We validate structured facts, show assumptions and ask questions;
we do not invent unsupported nutrition totals. Basic mode intentionally trades
precision for speed, while advanced mode requires more user input.

The main scope cut is a fixed catalogue of mainstream reference dishes rather than
all regional variants or unconstrained recipes. If time becomes tight, we will
freeze catalogue growth and prioritize reliable correction, failure handling and
clear evidence. The shared-account deployment is a teaching prototype.

## 8. Week 7–13 priorities

| Period | Deliverable and acceptance condition | Responsible members |
| --- | --- | --- |
| Week 7–8 | Team rehearses both modes, reviews milestone evidence and records failures; verify final tag before submission | Yixing (testing), Junlang/Jiacheng (fixes), Zhou Ran (docs) |
| Week 8–9 | Build a fixed Chinese-meal evaluation set covering ambiguous weights, oil and recipe corrections; report extraction successes/failures separately from arithmetic | Yixing with Junlang/Jiacheng |
| Week 9–10 | Improve provider failure messages and bounded recovery design; test duplicate requests and interrupted jobs before enabling retries | Junlang with Jiacheng; Yixing validates |
| Week 10–11 | Deploy a verified release with backup/rollback rehearsal; review account/data-access limits before wider sharing | Zhou Ran with Junlang; Yixing validates |
| Week 11–12 | Collect usability feedback on basic defaults and advanced questions; fix high-impact issues and update limitations | Whole team, documentation by Zhou Ran |
| Week 13 | Freeze release, rerun acceptance checks and prepare final demonstration/report with reproducible evidence | Whole team |

These are proposed priorities, not claims of completed features.

## 9. Artifact index

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
