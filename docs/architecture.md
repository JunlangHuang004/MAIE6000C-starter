# Nutrition Analysis Architecture

## Components

- **API service**: accepts requests, validates input, persists workflow state
- **PostgreSQL**: stores analyses, cases, and background jobs
- **Worker**: polls pending jobs and processes them outside the request cycle
- **AI service**: estimates calories and macronutrients from food text; the starter triage
  endpoint remains available

## Primary API contract

The detailed Week 5 evidence map, observed behavior matrix, endpoint contracts, and
Week 7 test plan are recorded in [`docs/api-contract.md`](api-contract.md).

### `POST /analyses`

Starts a nutrition-analysis workflow. The request is:

```json
{
  "food_text": "200g chicken breast and 230g cooked white rice"
}
```

`food_text` is required and must contain 3-2000 characters after surrounding
whitespace is removed. A successful request returns `201 Created` with an
`Analysis` in `queued` state and an `analyze_nutrition` `Job` in `pending` state.
Nutrition result fields are `null` until background processing completes.

### `GET /analyses/{analysis_id}`

Returns the current persisted analysis state and the `calories`, `protein_g`,
`carbs_g`, and `fat_g` result fields. An unknown ID returns `404` with
`{"detail": "Analysis not found"}`.

## Nutrition-analysis flow

1. client sends `POST /analyses`
2. API writes an analysis and pending job in one transaction
3. worker claims the pending `analyze_nutrition` job
4. worker calls the internal AI service at `POST /analyze-nutrition`
5. worker persists the nutrition result and marks the analysis and job completed
6. client retrieves the persisted result with `GET /analyses/{analysis_id}`

## State ownership

| State change | Owner |
| --- | --- |
| analysis does not exist -> `queued` | API |
| job does not exist -> `pending` | API |
| job `pending` -> `claimed` | Worker |
| analysis `queued` -> `completed` | Worker, after a valid AI response |
| job `claimed` -> `completed` | Worker |
| analysis/job -> `failed` | Worker, after processing failure |

## Errors and scope decisions

- invalid or missing `food_text` returns `422`
- an unknown analysis ID returns `404`
- an AI timeout or invalid AI response marks both the job and analysis `failed` and
  records the error on the job
- repeated `POST /analyses` calls create separate analyses; Week 7 has no idempotency key
- authentication and authorization are outside the Week 7 prototype scope
- image recognition is outside the Week 7 prototype scope

## Week 7 test plan

- valid create returns `201`, `queued` analysis, and `pending` nutrition job
- invalid `food_text` returns `422`
- existing and missing analysis retrieval return `200` and `404` respectively
- worker completion persists all four nutrition fields and completed states

## Baseline flow

1. client sends `POST /cases`
2. API writes a case row
3. API writes a pending job row
4. worker claims the pending job
5. worker calls the internal AI service
6. worker writes the triage result back to the case
7. API exposes the updated case state

## Why this starter exists

This starter is intentionally small.

Its purpose is to demonstrate the engineering shape of the course contract:

- persistence
- API boundaries
- async work
- service-to-service communication
- testing
- observability
- reproducible deployment

## Current limitations

- single polling worker
- deterministic, small-catalogue nutrition estimator rather than a production model or
  authoritative nutrition database
- no authentication or authorization
- no retry strategy beyond basic failure recording
- minimal domain model
