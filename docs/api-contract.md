# NutriChat API contract

Current implementation: 2026-10-31. See the generated `/docs` and `/openapi.json` for exact schemas. The [historical Week 5 evidence](history/week05-api-contract.md) is retained separately.

## Routes

| Route | Request / purpose | Success |
| --- | --- | --- |
| `POST /analyses` | `{food_text, mode?}`; atomically create an analysis and pending job | 201, `{analysis, job}` |
| `GET /analyses/{id}` | Read saved state, dialogue and result | 200, analysis |
| `PATCH /analyses/{id}` | `{food_text, revision}`; replace description and reset dialogue, preserving mode | 200, `{analysis, job}` |
| `POST /analyses/{id}/reply` | `{revision, message}` OR `{revision, answers}`; supplement or correct | 200, `{analysis, job}` |
| `POST /analyses/{id}/mode` | `{revision, mode}`; switch mode on the same record | 200, `{analysis, job}` |
| `POST /analyses/{id}/ingredients` | Reviewed ingredient recipe replacing one draft item | 200, `{analysis, job}` |
| `POST /analyses/{id}/confirm` | `{revision}`; confirm a completed result | 200, analysis |
| `GET /foods` | Active provider, catalogue, legacy names and gram limit | 200, object |
| `GET /jobs/{id}` | Background job status and operational error | 200, job |
| `GET /app` | Application page | 200, HTML |

Existing `/cases` routes and internal `/triage` are retained from the starter. The internal AI service receives `POST /analyze-nutrition`; it is not a public model endpoint.

## Creation and saved fields

```json
{"food_text": "一份番茄炒蛋，两个水煮鸡蛋", "mode": "basic"}
```

`food_text` is trimmed and must contain 1–2000 characters. `mode` is `basic` or `advanced`; API default is `advanced`, while the UI explicitly sends `basic` by default. Each valid POST creates a new record; there is no idempotency key.

The response contains the new analysis (initial `revision: 1`, `status: queued`) and pending job. Poll `GET /analyses/{id}` for the saved result. Do not assume a particular final revision; use the latest returned value for every mutation.

Analysis fields include `id`, `food_text`, `mode`, `status`, `revision`, timestamps, `confirmed_at`, `interpreted_food_text`, `error_message`, four nutrient totals (`calories`, `protein_g`, `carbs_g`, `fat_g`), and:

- `conversation`: saved user/assistant messages, with optional display text.
- `draft`: extracted and user-supplied facts. Basic-mode defaults are not persisted as facts.
- `questions`: current structured clarification slots, labels and applicable options.
- `details`: per-food calculation, assumptions and source references.

## Clarification and corrections

Natural-language reply example (replace the revision with the current value):

```json
{"revision": 2, "message": "鸡蛋可食部分是80克，水煮，没有额外用油"}
```

Structured reply example, only if `0.grams` is a current issued question:

```json
{"revision": 2, "answers": {"0.grams": 180}}
```

Exactly one nonblank message or nonempty answers map is required. Messages are limited to 2000 characters and answers to 150 entries. Use server-issued question keys and values; do not manufacture fields or submit nutrition totals. Keys include item index plus `grams`, `weight_basis`, `preparation`, `oil_g`, `food_id`, `resolved` or `recipe`.

A recipe answer has the shape `{ingredients: {ingredient_id: grams}, yield_g: finished_batch_grams}`. It must match the issued recipe ingredient set. Set omitted ingredients to zero; describe added ingredients in a natural-language reply. Structured replies validate and update the draft without another Qwen call. Natural-language replies re-extract facts using the saved conversation, so advanced recipes require renewed approval.

Replies reject an existing conversation of 36 or more messages or a resulting serialized conversation above 45,000 characters. Extraction permits up to 30 items. Food grams must be positive and at most 10,000; recipe ingredient grams may be zero and at most 10,000; batch yield must be positive and at most 10,000; consumed extra oil is 0–1000g.

`PATCH` replaces the description and clears the old conversation/draft. `/reply` continues the conversation. `/mode` retains explicit draft facts and conversation, but clears results and requeues calculation. Use `/mode` to change modes; `PATCH` does not change mode.

## Explicit ingredient recipe

`POST /analyses/{id}/ingredients` uses this body, with the latest revision and the
zero-based index of the item the user is explicitly replacing:

```json
{
  "revision": 1,
  "item_index": 0,
  "name": "My chicken recipe",
  "basis": "batch",
  "ingredients": [
    {"food_id": "chicken", "grams": 300},
    {"food_id": "oil", "grams": 10},
    {"food_id": "soy_sauce", "grams": 20}
  ],
  "batch_yield_g": 600,
  "consumed_g": 150,
  "accepted": true
}
```

Use `basis: "consumed"` with null batch/consumed fields when every ingredient
amount already represents the eaten portion. There must be 1–30 distinct existing
ingredient IDs; reference-dish IDs, unknown IDs and client nutrient values are
rejected. Gram values must be finite numbers greater than zero and at most 10,000;
numeric strings and booleans are rejected. Batch mode requires both weights and
`consumed_g <= batch_yield_g`. Acceptance must be explicitly true.

The endpoint preserves all other items, records a server-created `custom_recipe`
draft entry and queues the existing worker. It does not send the form to Qwen or
add a global catalogue entry. Another unresolved item still suppresses all meal
totals. Custom details have `kind: "custom_recipe"` and `quantity_provenance` with
ingredient states, input grams, consumed-equivalent grams and batch fraction.
Consumed-basis detail grams are the ingredient sum, not a finished cooked weight.

Custom recipes follow the same revision and confirmation locks. A free-text
`/reply` while any custom recipe exists returns 422 with guidance to use the
structured editor or start a new meal. Structured answers for other items and
mode changes preserve custom recipes. `PATCH` remains an explicit reset of the
whole description/draft. See [the user guide](ingredient-recipes.md).

## State and revision rules

```text
POST -> queued -> completed -> confirmed
               -> needs_input
               -> failed
needs_input / completed / failed -> queued (reply, correction or mode switch)
```

The worker owns processing transitions from `queued`. Clarification is a successful job outcome: the analysis becomes `needs_input` and all nutrient totals remain null. A valid complete result becomes `completed`, ready for user review. Upstream/API/parsing failures become `failed` with a user-facing error. Job states are `pending -> claimed -> completed/failed`.

User mutations compare both the current state and revision in a conditional database update. Correction, reply and mode switch are permitted only from `needs_input`, `completed` or `failed`. They clear prior totals, evidence and errors and create a new job. Confirmation accepts only `completed`, increments revision and records `confirmed_at`. Queued records cannot be edited; confirmed records are locked.

## Provider and error behavior

- Demo provider synchronously rejects unsupported English/gram input with 422; it retains the legacy small catalogue.
- Qwen provider validates text length synchronously, then extracts catalogue IDs and meal facts asynchronously. Unmatched foods and missing facts produce clarification when representable; invalid model responses and service failures fail the job. There is no fabricated fallback total.
- Basic mode uses visible reference assumptions for missing portions/recipes/oil where supported; advanced mode asks for details. Unknown foods or contradictory state/preparation can still require clarification in basic mode.
- Missing record: 404. Invalid payload or answer: 422. Stale revision or disallowed state: 409; reload before retrying.
- No automatic retry or recovery of interrupted claimed jobs is implemented.

## Access and evidence

Local API has no built-in per-user authentication. The optional public deployment adds an HTTPS session gateway: unauthenticated application requests redirect to `/login`, wrong passwords return 401, and `/metrics` is blocked externally. This is a shared-account demo, not per-user authorization.

Tests in `tests/integration/test_api_analysis_flow.py` and the other integration/unit modules cover persistence, validation, questions, correction, mode switching and confirmation conflicts. `scripts/check_dialogue.py` exercises the real-provider workflow with synthetic meals. See [operations](operations.md) and [change log](change-log.md) for commands and recorded validation.
