> Historical course evidence and plan, retained on 2026-10-17 without changing its completion checklist. This is not the current implementation contract. See the [current API contract](../api-contract.md).

# Week 5 API Contract Evidence and Plan

## Scope

The Week 7 vertical slice accepts a text description of food, creates a persistent
nutrition analysis and background job, processes the job through the worker and
internal AI service, and exposes the persisted calories and macronutrients.

In scope:

- `POST /analyses`
- `GET /analyses/{analysis_id}`
- asynchronous API -> database/job -> worker -> AI -> persisted-result flow
- calories, protein, carbohydrates, and fat

Out of scope for Week 7:

- image recognition
- authentication and authorization
- idempotency keys and automatic retries
- production-grade nutrition data or medical guidance

## Activity A: API Contract Evidence Map

This evidence map records the starter behavior that was observed before defining the
project-specific nutrition interface.

| Evidence | Actual repository evidence | Observed or intended |
| --- | --- | --- |
| Workflow-starting route | `POST /cases` in `services/api/app/main.py`; route function `create_case()` | Observed starter behavior |
| Request schema | `CaseCreate` in `services/common/schemas.py` | Observed starter behavior |
| Validation rules | `title`: 3-200 characters; `description`: 5-4000 characters | Observed starter behavior |
| Main-record/job function | `create_case_with_job()` in `services/api/app/main.py` | Observed starter behavior |
| Records created | `Case` and `Job` from `services/common/models.py` | Observed starter behavior |
| Initial states | Case `queued`; Job `pending`; job type `triage_case` | Observed starter behavior |
| Response model | `CaseCreateResponse`, containing `CaseRead` and `JobRead` | Observed starter behavior |
| Missing-record behavior | `GET /cases/{case_id}` returns `404 {"detail":"Case not found"}` | Observed starter behavior |
| Validation-error behavior | Invalid or missing fields return FastAPI/Pydantic `422` details | Observed starter behavior |
| Integration test | `test_create_and_read_case_and_job()` in `tests/integration/test_api_case_flow.py` | Executed evidence |
| Project route | `POST /analyses` and `GET /analyses/{analysis_id}` | Implemented project behavior |
| Project schemas | `AnalysisCreate`, `AnalysisRead`, and `AnalysisCreateResponse` | Implemented project behavior |
| Project persistence | `Analysis` plus an `analyze_nutrition` `Job` | Implemented project behavior |
| Project integration test | `tests/integration/test_api_analysis_flow.py` | Executed evidence |

### Route-to-test trace

```text
POST /analyses
  -> AnalysisCreate
  -> create_analysis()
  -> create_analysis_with_job()
  -> Analysis + Job database rows
  -> AnalysisCreateResponse
  -> test_create_and_read_analysis_and_job()
```

### API design question and decision

**Question:** Should repeated identical `POST /analyses` requests return the same
analysis or create separate analyses?

**Week 7 decision:** Each valid POST creates a separate analysis. Idempotency keys are
deferred and this limitation is visible in the contract.

## Activity B: Observed API Behavior Matrix

The first four rows record starter behavior observed during the Lab. The final row
records the worker-completed starter flow that was also observed.

| Scenario | Request | Observed status | Response/state shape | Expected vs. actual | Evidence |
| --- | --- | --- | --- | --- | --- |
| Valid create | `POST /cases` with valid `title` and `description` | `201` | Case `queued`; Job `pending`; job type `triage_case` | Match | `create_case()`, `create_case_with_job()`, integration test |
| Retrieve created record | `GET /cases/{case_id}` | `200` | Current Case record | Match | `read_case()`, integration test |
| Missing required fields | `POST /cases` with `{}` | `422` | Structured validation details for `title` and `description` | Match | `CaseCreate` |
| Valid-format missing ID | `GET /cases/00000000-0000-0000-0000-000000000000` | `404` | `{"detail":"Case not found"}` | Match | `read_case()` |
| Worker-completed retrieval | Start worker, then repeat `GET /cases/{case_id}` | `200` | Case changed from `queued` with null AI fields to `triaged` with persisted AI result | Match | Worker and AI logs observed during Lab |

## Activity C: Project Endpoint Contracts

### `POST /analyses`

**Caller and purpose:** A user-facing nutrition application calls this endpoint to
start an asynchronous nutrition analysis from food text.

**Request:**

```json
{
  "food_text": "200g chicken breast and 230g cooked white rice"
}
```

`food_text` is required. Surrounding whitespace is removed, after which the value
must contain 3-2000 characters.

**Success:** `201 Created`

```json
{
  "analysis": {
    "id": "analysis-uuid",
    "food_text": "200g chicken breast and 230g cooked white rice",
    "status": "queued",
    "calories": null,
    "protein_g": null,
    "carbs_g": null,
    "fat_g": null,
    "created_at": "2026-10-10T00:00:00Z",
    "updated_at": "2026-10-10T00:00:00Z"
  },
  "job": {
    "id": 1,
    "case_id": null,
    "analysis_id": "analysis-uuid",
    "job_type": "analyze_nutrition",
    "status": "pending",
    "attempts": 0,
    "error": null,
    "created_at": "2026-10-10T00:00:00Z",
    "claimed_at": null,
    "completed_at": null
  }
}
```

**Visible errors:** Invalid or missing input returns `422`. A database failure may
surface as a server error and must not return a false successful state.

**Database writes:** The API writes one `Analysis` and one `Job` in the same database
transaction. The analysis starts as `queued`; the job starts as `pending` with job
type `analyze_nutrition`.

**Allowed API transition:** Analysis does not exist -> `queued`; Job does not exist ->
`pending`. The API does not mark processing complete.

**Authentication:** Not required for the Week 7 prototype.

**Retry/idempotency:** Repeated POST requests may create separate analyses. No
idempotency key is included in Week 7.

**Verification:** `test_create_and_read_analysis_and_job()` and
`test_create_analysis_validates_food_text_length()`.

### `GET /analyses/{analysis_id}`

**Caller and purpose:** The user-facing application retrieves the current state and
persisted nutrition result.

**Request:** No request body. `analysis_id` is supplied in the path.

**Queued response:** `200 OK`

```json
{
  "id": "analysis-uuid",
  "food_text": "200g chicken breast and 230g cooked white rice",
  "status": "queued",
  "calories": null,
  "protein_g": null,
  "carbs_g": null,
  "fat_g": null,
  "created_at": "2026-10-10T00:00:00Z",
  "updated_at": "2026-10-10T00:00:00Z"
}
```

**Completed response:** `200 OK`

```json
{
  "id": "analysis-uuid",
  "food_text": "200g chicken breast and 230g cooked white rice",
  "status": "completed",
  "calories": 629.0,
  "protein_g": 68.2,
  "carbs_g": 64.4,
  "fat_g": 7.9,
  "created_at": "2026-10-10T00:00:00Z",
  "updated_at": "2026-10-10T00:00:02Z"
}
```

**Visible error:** An unknown ID returns `404` with
`{"detail":"Analysis not found"}`.

**Database read:** Reads the current `Analysis` row. It does not calculate results or
change state.

**Allowed transition:** None; this is a read-only endpoint.

**Authentication and retry:** Authentication is outside Week 7 scope. GET is safe to
repeat.

**Verification:** `test_read_missing_analysis_returns_404()` and
`test_worker_persists_nutrition_result()`.

**Optional endpoint decision:** No optional endpoint is required for the Week 7
vertical slice. Retry, update, review, and list endpoints are deferred.

## Activity D: State Ownership, Errors, and Boundaries

| Question | Team decision for Week 7 |
| --- | --- |
| Which transition does the API make? | Create Analysis `queued` and Job `pending` in one transaction |
| Which transitions belong to the worker? | Job `pending` -> `claimed` -> `completed`; Analysis `queued` -> `completed` |
| What happens when input is invalid? | API returns `422`; no Analysis or Job is written |
| What happens when the record does not exist? | GET returns `404 {"detail":"Analysis not found"}` |
| What happens when AI processing fails or times out? | Worker marks Analysis and Job `failed`; Job stores a bounded error message |
| What must not be repeated accidentally? | A client should avoid retrying POST after an ambiguous response because Week 7 has no idempotency key |
| What is the authorization scope? | No authentication/authorization in Week 7; required before multi-user or sensitive-data use |
| What is the AI timeout policy? | Worker HTTP call uses the configured timeout; timeout or invalid response follows the failed-state path |

The client-visible failure path is `Analysis.status = "failed"`. The existing GET
endpoint exposes this state without pretending that a nutrition result exists.

## Activity E: Week 7 Contract-Test Plan

Interim documentation/test owner: **Junlang Huang (repository owner; team should
confirm ownership before submission).** Completed dates below record the current
implementation work; the live-stack target remains the Week 7 demo deadline.

| Test name | Setup | Request/action | Expected HTTP response | Expected persisted state | Owner | Target/status |
| --- | --- | --- | --- | --- | --- | --- |
| `test_create_and_read_analysis_and_job` | Empty test database | Valid `POST /analyses`, then GET returned ID | POST `201`; GET `200` | Analysis `queued`; Job `pending`; result fields null | Junlang Huang | Completed 2026-10-10 |
| `test_create_analysis_validates_food_text_length` | Empty test database | POST too-short, whitespace-only, and too-long food text | `422` for each request | No Analysis or Job created | Junlang Huang | Completed 2026-10-10 |
| `test_read_missing_analysis_returns_404` | Empty test database | GET valid-format missing analysis ID | `404` with stable detail | No state change | Junlang Huang | Completed 2026-10-10 |
| `test_worker_persists_nutrition_result` | Create queued analysis; mock internal AI HTTP response | Claim and process job, then GET analysis and job | GET responses `200` | Analysis and Job `completed`; four nutrition fields persisted | Junlang Huang | Completed 2026-10-10 |
| Live-stack end-to-end test | PostgreSQL migration applied; API, worker, and AI services running | POST analysis -> wait for worker -> GET result | POST `201`; final GET `200` | Real database contains completed Analysis and Job | Junlang Huang | Before Week 7 demo; exact Canvas date to confirm |

Latest automated result recorded on 2026-10-10: `10 passed, 1 skipped`. The skipped
test is the smoke test that requires a running stack. The two warnings are third-party
deprecation warnings and are not test failures.

## Peer Review Preparation

The following is a self-review prepared for the required team exchange. It must not be
presented as peer feedback until another team member actually reviews it.

- **Strength:** The API response is truthful while processing is incomplete: status is
  `queued` and nutrition fields remain null.
- **Ambiguity to review:** Decide whether future clients need an idempotency key or a
  retry endpoint after an ambiguous network failure.
- **Risk/recommendation:** The current deterministic nutrition catalogue is suitable
  for the vertical slice but not for production accuracy; a validated data source,
  uncertainty policy, and broader parsing strategy are future decisions.

Actual peer reviewer: **TBD**

Peer-review date: **TBD**

Peer feedback or confirmation: **TBD**

## Exit Checklist

- [x] Evidence map based on actual starter code
- [x] Observed API behavior matrix
- [x] Two required project endpoints defined
- [x] No optional endpoint added without justification
- [x] State-transition ownership table
- [x] Error, timeout, retry/idempotency, and authorization-scope decisions
- [x] At least three planned API tests with current implementation status
- [x] Interim documentation owner recorded
- [x] Clear Week 7 vertical-slice target
- [ ] Actual peer review completed and reviewer feedback recorded
- [ ] Live Docker/PostgreSQL end-to-end smoke test completed
