# Week 6: asynchronous workflow evidence and Week 7 plan

Course reference: Week 6 Lab, Activities A–G (slides 11–21). This document separates
implemented behavior, executed evidence and future work. The chosen project path
is `POST /analyses -> Analysis + Job -> Worker -> AI -> saved result -> GET`.

## Activity A — worker lifecycle evidence map

Paths below are relative to the repository root.

| Question | Actual path / symbol | Evidence and limits |
| --- | --- | --- |
| What starts work? | `services/api/app/main.py`: `create_analysis`, `create_analysis_with_job` | POST /analyses creates queued analysis and pending job in one transaction; returns 201 |
| What validates input? | `services/common/schemas.py`: `AnalysisCreate` | Trimmed 1–2000-character description; demo also checks supported gram input |
| Where is durable state? | `services/common/models.py`: `Analysis`, `Job` | Status, attempts, claim/completion timestamps, result and error fields |
| What claims work? | `services/worker/app/main.py`: `run_worker`, `claim_next_pending_job` | Oldest pending row; `FOR UPDATE SKIP LOCKED`; commit claimed status, claim timestamp and increment attempts |
| Where is processing marked? | `claim_next_pending_job` | Job becomes claimed; Analysis stays queued. No analysis processing state exists |
| What calls AI? | `process_job`, `process_nutrition_job` | Finite-timeout HTTP call to internal `/analyze-nutrition` |
| What validates/persists success? | `NutritionAnalysisResponse`; `process_nutrition_job` | Validate before storing; result or questions and completed job committed together |
| What handles failure? | `run_worker` exception handler; `mark_job_failed` | Fail both records, save generic analysis message and bounded job error; no automatic retry |
| What exposes current state? | API `read_analysis`, `/jobs/{job_id}` | GET reads durable records; the browser polls |
| Which tests cover it? | `tests/integration/test_api_analysis_flow.py`, `test_worker_lifecycle.py`, `test_meal_dialogue.py` | Creation, successful persistence, actual loop error handling, claim metadata and clarification; SQLite tests do not prove PostgreSQL lock concurrency |

The retained starter path uses `/cases`, `create_case_with_job`, `process_triage_job`
and `GET /cases/{id}`. The lab evidence records it separately from the nutrition path.

## Activity B — why this step belongs in a worker

| Candidate | Long / uncertain? | Network or AI call? | Retryable in principle? | Must finish before initial response? | Decision |
| --- | --- | --- | --- | --- | --- |
| Meal interpretation and nutrient evaluation | Yes, model latency varies | Yes in Qwen mode | Some transient errors; not automatically retried now | No | Worker |
| Validate description and mode | No | No | No | Yes | API |
| Confirm a reviewed result | No | No | State/revision conflict requires refresh | Yes | API |

The minimum Week 7 slice is one nutrition job type, a saved useful result or failure,
and API retrieval. Multiple workers, scheduling and automatic recovery are outside
this slice. The inherited case path remains for course observation.

## Activities C and D — lifecycle and boundaries

See the [architecture state-ownership table](architecture.md#week-6-worker-contract-and-state-ownership)
for each state, owner, entry condition and API meaning.

- Client: submit, read, answer questions, correct and confirm via the API; cannot set worker states.
- API: validate, perform revision-checked mutations and enqueue atomically; does not wait for model inference.
- Worker: claim, call the processor, validate output and persist outcome; exposes no public API.
- AI service: parse/evaluate and return a result or error; does not own database lifecycle transitions.
- Authorization: the optional gateway has one shared demo account. Analyses have no per-user ownership; local lab access is internal to Compose.

`needs_input` is not a retry or failure: the current job is completed, and a valid
reply queues a new job. Confirmation is a user action after computation.

## Activity E — failure, retry and idempotency policy

| Scenario | Current policy | Client-visible / persisted state | Verification |
| --- | --- | --- | --- |
| Invalid create | Reject; do not enqueue | 422; no analysis/job rows | Existing invalid-input tests |
| AI timeout | One attempt, no retry delay | Analysis failed; Job failed, attempts 1, completion timestamp | Worker-loop timeout test with fake HTTP boundary |
| HTTP processor error | Terminal failure | Failed records and generic analysis message | Worker-loop HTTP 503 test |
| Malformed processor result | Reject incomplete nutrient schema; terminal failure | Failed, no partial nutrient totals | Worker-loop malformed-result test |
| Crash after claim | No lease or recovery rule implemented | Job may remain claimed; Analysis queued | Claim test documents lack of reclaim; actual process-kill recovery remains a gap |
| Repeated client POST | Idempotency deferred; each POST creates new records | Two 201 responses with distinct IDs | Duplicate-POST integration test |
| User corrects failed meal | New revision-checked job, not retry of old job | Analysis queued; new Job pending | Existing correction test |

There is no stable machine-readable failure code yet. `Analysis.error_message` is
generic, while `Job.error` stores up to 1000 characters of operational exception
text and is readable via the job endpoint. Do not treat that endpoint as a fully
sanitized public error interface. Crash recovery, error-code design and duplicate
request protection remain explicit gaps rather than claimed implementations.

## Activity F — worker contract and pseudocode

Input is one pending job loaded from PostgreSQL. The nutrition processor receives
`analysis_id`, `food_text`, `mode`, `conversation` and `draft`, not database credentials
or login credentials. Qwen receives the extraction prompt, catalogue context and
meal/dialogue facts; provider credentials are supplied separately by the AI service.

Expected output is either all four nonnegative nutrient totals with evidence, or a
nonempty draft plus questions and null totals. Python validates the response before
persisting it. There is no client-controlled nutrient overwrite.

```text
repeat:
    transaction: select oldest pending job FOR UPDATE SKIP LOCKED
                 set claimed, claimed_at, attempts += 1; commit
    if no job: wait briefly and poll again
    load durable resource data; dispatch by job type
    call internal AI with finite configured HTTP timeout
    validate response schema
    transaction: save result or questions and job completed; commit
    on ordinary exception after claim:
        transaction: save resource failed and bounded job error; commit
        wait briefly; next poll only selects pending jobs
    on process interruption:
        no automatic claimed-job recovery is implemented
```

Cloud Qwen/worker timeouts are 30/45 seconds. `.env.example` uses 12/20 seconds.
The worker request timeout must exceed the Qwen timeout. These are request timeouts,
not a durable job lease or an end-to-end deadline for the entire workflow.

## Activity G — Week 7 tests and demo

| Minimum behavior | Test / command | Expected evidence |
| --- | --- | --- |
| Valid create queues work | `test_create_and_read_analysis_and_job` | 201; Analysis queued and Job pending, linked IDs |
| Worker saves a useful result | `test_worker_persists_nutrition_result`; `test_worker_loop_persists_processor_outcome[success]` | GET exposes totals; database result and completed job |
| Invalid create returns 422 | `test_invalid_meal_writes_nothing` | 422 with no unintended rows |
| Processor failure is visible | `test_worker_loop_persists_processor_outcome[timeout/http_error/malformed]` | Failed persisted rows, attempts 1, timestamps, no totals |
| Claim metadata and recovery gap | `test_claim_persists_attempt_and_does_not_reclaim_interrupted_job` | Persisted claim and attempts; later polling does not reclaim it |
| Duplicate POST decision | `test_repeated_post_creates_separate_records_without_idempotency` | Distinct analyses/jobs for identical POSTs |
| Clarification and confirmation | Existing dialogue/review tests; `scripts/check_dialogue.py` for real Qwen | Questions, revision protection, correction and locked confirmation |

Unit/integration tests use isolated SQLite databases and fake processor responses.
They verify API/persistence logic, not PostgreSQL row-lock concurrency or live Qwen.
The separate local Docker observation uses real PostgreSQL and HTTP between services,
with the demo provider and one worker. It does not prove multi-worker exclusion or
crash recovery. Poll with a terminal-state deadline; do not use a fixed long sleep.

### Reproduce the isolated observation

Use current Docker Compose with `!override` / `!reset` support. This lab overlay
loads `.env.example`, forces demo mode, clears model credentials and removes host
ports. `-p nutrichat-week06` gives it a separate database volume. Do not run these
commands against the public ECS project.

```sh
docker compose -p nutrichat-week06 --env-file .env.example -f compose.yaml -f compose.week06.yaml build api ai worker
docker compose -p nutrichat-week06 --env-file .env.example -f compose.yaml -f compose.week06.yaml up -d --wait db ai api
docker compose -p nutrichat-week06 --env-file .env.example -f compose.yaml -f compose.week06.yaml stop worker
```

With the worker stopped, call `/health/live` and `/health/ready`, POST a synthetic
case to `/cases`, and POST `{"food_text":"100g egg"}` to `/analyses`. Use a Python
HTTP client inside the API container (`exec -T api python`) against `http://api:8000`.
Save the returned resource/job IDs, HTTP statuses and JSON responses. GET both
resources and jobs before starting the worker. Inspect PostgreSQL for those IDs.

```sh
docker compose -p nutrichat-week06 --env-file .env.example -f compose.yaml -f compose.week06.yaml exec -T db psql -U postgres -d maie6000c -c 'SELECT id, job_type, status, attempts, claimed_at, completed_at FROM jobs ORDER BY id;'
docker compose -p nutrichat-week06 --env-file .env.example -f compose.yaml -f compose.week06.yaml up -d --no-build worker
```

Poll GET for up to 60 seconds until the case is triaged and the analysis completed;
fail early on a failed result. The claimed intermediate state may be too brief to
observe through polling; use persisted timestamps and job-ID logs as claim evidence.
Repeat database reads for the same IDs, then collect logs:

```sh
docker compose -p nutrichat-week06 --env-file .env.example -f compose.yaml -f compose.week06.yaml logs --no-color --tail=100 worker ai
docker compose -p nutrichat-week06 --env-file .env.example -f compose.yaml -f compose.week06.yaml down
```

`down` preserves the lab volume. Production/local application volumes are unaffected.

### Executed evidence

Observed on **2026-10-17 at 16:09 HKT** in the isolated `nutrichat-week06` project.
Machine-readable [HTTP, database and log evidence](evidence/week06-worker-lifecycle.json)
contains only synthetic lab data. Source base was `5a95caf`; the Week 6 additions
were uncommitted during observation and runtime service code was unchanged.

| Evidence source | Worker stopped | Worker started |
| --- | --- | --- |
| HTTP | Health endpoints 200; case/analysis POSTs 201; GET shows queued; jobs pending | GET case triaged; GET analysis completed; both jobs completed |
| PostgreSQL | Jobs 1 and 2 pending, attempts 0, no claim/completion time; resource results null | Both attempts 1 with claim/completion timestamps; case label general; analysis totals saved |
| Worker logs | No processing before start | Matching `job_claimed` and `job_completed` events for both job IDs |
| Nutrition result | All four totals null | 100g egg: 155 kcal, 13g protein, 1.1g carbohydrates, 11g fat (legacy demo values) |

The recorded case ID is `90ad1d78-674e-424f-a651-213ed23e3f3e`; analysis ID is
`e9609fe4-8c3b-4760-88af-bc03d1fe2282`. Do not expect these IDs in another environment.
The claimed state was established by database timestamps and logs; it was not
claimed to have been captured in an intermediate HTTP response.

[Verification results](evidence/week06-verification.md): six new lifecycle cases
passed; the full unit/integration suite passed 65 tests (two smoke tests deselected);
Ruff passed; both smoke tests passed against the isolated PostgreSQL stack.
There were two dependency deprecation warnings. Failure tests use fake HTTP
responses; this run did not interrupt a live Qwen request or kill a worker process.

## Sprint ownership and outstanding work

Current assignments (confirmed by the team representative on 2026-10-27):

- Implementation: Junlang Huang; supporting development: Jiacheng Cao.
- Documentation and deployment/integration: Zhou Ran.
- Testing: Yixing Huang.

The [Week 7 milestone](../submissions/week07/README.md) and
[AI Use Statement](../submissions/week07/AI_USE_STATEMENT.md) now supersede the
pending ownership/statement notes in the historical Week 6 evidence.

- [ ] Review the shared-account/error-detail limitations before wider public use.
- [ ] If expanding scope, design idempotency and claimed-job recovery with appropriate tests.
