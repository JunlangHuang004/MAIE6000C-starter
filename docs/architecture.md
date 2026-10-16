# NutriChat architecture

Current implementation: 2026-10-17.

## Services and data flow

```text
Browser -> [optional HTTPS proxy + session gateway] -> FastAPI API
                                                       | PostgreSQL
                                                       | analyses + jobs
                                                     Worker
                                                       | HTTP
                                                Internal AI service
                                                  |           |
                                             Qwen API    Python meal engine
                                                  |           |
                                              extraction   catalogue arithmetic
```

The API atomically saves an analysis and pending job. A separate worker claims the job, calls the internal AI service and persists the result or questions. The browser polls the API and renders saved state. PostgreSQL is the source of truth; localStorage remembers only the last analysis ID for restoration.

- API: validation, revision/state checks, saved records, catalogue and HTML UI.
- Worker: asynchronous orchestration and job/error bookkeeping.
- AI service: Qwen extraction or legacy demo parsing, followed by deterministic evaluation.
- Shared meal engine: catalogue validation, questions, structured answers, assumptions and nutrient arithmetic.
- PostgreSQL: analyses, conversations, drafts, questions, evidence and jobs; historical cases remain available.

## Qwen's role

Qwen runs in Alibaba Cloud Model Studio, not on ECS. It interprets Chinese descriptions, names, preparation, quantities and corrections and maps them to supported catalogue IDs. The adapter requests structured JSON, with `enable_thinking=false`, temperature 0 and a configurable model (default `qwen-plus`). Disabling deep-thinking mode does not remove language inference or guarantee correctness.

The model does not supply authoritative calorie/macronutrient values, approve recipes, or train on project updates. Python validates the extracted facts and calculates from the versioned catalogue. Structured question answers bypass another model call; natural-language replies use the bounded conversation as context. Updating aliases, food data or prompts changes application behavior without retraining model weights.

## Two modes and uncertainty

Basic mode applies labelled defaults to a calculation copy: reference portions, reference recipes and applicable extra-oil assumptions. The stored draft retains missing fields, so switching to advanced mode asks for details that were never supplied.

Advanced mode asks for grams, weight state, preparation and consumed oil as needed. Recipe calculations require explicit acceptance of editable ingredient quantities and finished batch yield. Unmatched foods or contradictory raw/cooked/preparation facts can require questions in either mode. Pending questions leave every nutrient total null.

Nutrients equal the sum of ingredient grams multiplied by their per-100g data. Recipe portions scale the whole-batch nutrients by consumed cooked weight divided by finished batch weight. Data provenance, limits and exceptions are detailed in [nutrition data](nutrition-data.md).

## Persistence and concurrency

Analysis states are `queued`, `needs_input`, `completed`, `failed`, `confirmed`. Jobs track `pending`, `claimed`, `completed`, `failed`. A question is a completed worker operation, not a failed job. User correction/reply/mode-switch requests check the current revision and state; confirmation locks completed records. The [API contract](api-contract.md) defines the payloads and transitions.

Alembic migrations add the analysis workflow, revision/confirmation fields (0003), JSON dialogue and evidence (0004), and mode (0005). Existing analyses receive `advanced` as their default mode. API startup runs migrations before the worker starts.

## Deployment boundaries

Local Compose publishes development ports for API, AI and PostgreSQL. Cloud Compose exposes only API loopback access; AI and database remain internal. Optional public Compose adds Nginx on 80/443 and an internal session gateway. Secrets and certificates are external runtime files excluded from Git. See [cloud deployment](cloud-deployment.md).

The API readiness probe checks PostgreSQL. AI readiness reports service availability but does not call Qwen. Structured logging and Prometheus metrics support observation; they do not constitute end-to-end model validation.

## Current limitations

The public account is shared and analyses have no per-user ownership. There is no idempotency key, automatic retry, claimed-job recovery, image recognition, model training or measured cooking-loss model. Use one worker for this prototype. Reference recipes and portions are assumptions, and even detailed estimates depend on the quality of input and food mappings.

See [ADR 0001](adrs/0001-baseline-stack.md) for the starter stack and [ADR 0002](adrs/0002-source-backed-dual-mode.md) for the nutrition design.
