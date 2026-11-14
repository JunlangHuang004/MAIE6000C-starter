# Fresh source review — 2026-11-14

Reviewed snapshot: `254bebfc8fea07830d261adf2def54bc4cb217ed`, in `/Users/jadenhuang/Documents/Codex/2026-10-16/d/worktrees/nutrichat-qa-20261114`.

Scope: account isolation, profile calculations/guards, daily intake and exercise, completeness flags, trends, date boundaries, and revision concurrency. I read current source and `docs/accounts.md`, `docs/personalization.md`, and `docs/tracking.md`. I did not read prior QA reports or `docs/qa/MEMORY.md`. No tracked file was edited in this baseline checkout.

## Confirmed findings

### S1 — Profile conflict recovery leaves displayed energy balance based on the old profile (P2)

Source: `services/api/app/static/app.js:144–150`; compare the successful save refresh at line 154.

Reproduction: load a profile and a diary day, change that profile in another tab, attempt a stale profile save in the first tab, then choose “Load latest profile.” The first tab receives and displays the new profile, but `loadProfile()` refreshes neither the daily view nor the trend data derived from that profile.

The isolated DOM probe used a synthetic 30-year-old male coefficient, 180 cm, changing weight from 80 to 90 kg. After conflict recovery the profile correctly displayed resting energy of 1,880 kcal, while the daily balance still displayed the old 2,136 kcal baseline, derived from 1,780 × 1.2. At intake 2,000 and exercise 0, it showed deficit 136 instead of 256. No additional daily request was made. The server calculation itself is correct; the visible views disagree until separately refreshed.

Expected: after an explicit profile reload changes the saved profile, refresh dependent saved diary/trend calculations while preserving unsaved diary inputs.

Evidence: `source-ui-probes.cjs`, first test. It fails against this snapshot with actual `Calorie deficit 136 kcal`, expected `256`.

### S2 — An overnight tab rejects the current Hong Kong date until trends are refreshed (P2)

Source: `services/api/app/static/app.js:209`, `214`, `231`, `270–271`, `819–820`.

`trackingToday` and every date input's maximum are populated only by a `/tracking` response. There is no date refresh on focus, visibility change, or elapsed time. A tab initialized on November 3 still restricts dates to November 3 after Hong Kong advances to November 4. Selecting November 4 causes local rejection, clears the displayed daily record, and sends no request to the server, although that date is now valid. New meal defaults can likewise retain the previous day.

The isolated DOM probe changed the mocked server's current date from `2026-11-03` to `2026-11-04`, dispatched focus/visibility events, and selected November 4. Observed input maximum: `2026-11-03`; observed message: choose a date through today; observed new-day request: none. Refreshing trends or reloading the page is a workaround.

Expected: refresh the authoritative current date when returning to an open tab or before rejecting a newly current date. Preserve deliberately selected historical dates.

Evidence: `source-ui-probes.cjs`, second test. This is a DOM/source reproduction, not a real-clock overnight browser run.

### S3 — Meal correction/mode revisions accept unbounded integers and can return 500 (P2)

Source: `services/common/schemas.py:201–202`, `217–218`; `services/api/app/main.py:361–374`.

Unlike profile, diary, and confirmation revision fields, `AnalysisCorrection.revision` and `AnalysisMode.revision` have no upper bound. A valid authenticated owner supplying the valid JSON integer `10**100` reaches the database comparison. In the fresh TestClient/SQLite probe, both `PATCH /analyses/{id}` and `POST /analyses/{id}/mode` returned `500 Internal Server Error` instead of a validation/conflict response. The analysis remained completed at revision 1, calories 155.

Expected: reject values outside the supported revision range at validation, consistently with confirmation (`1..2147483646`). After the independent SQLite reproduction, the parent audit also confirmed both failures against the isolated PostgreSQL HTTP application; the same oversized revision on reply returned 409, because that route checks the loaded revision before the database update.

Evidence: `source-api-probe.py`, first two requests; parent HTTP evidence in `postgres-invalid-revisions.json`.

### S4 — Non-finite revision errors crash the generic validation response (P2)

Source: `services/api/app/main.py:158–179`; `services/common/schemas.py:201–224`.

Submitting an invalid non-finite revision (`NaN`) to meal correction, mode switching, or reply yields a Pydantic validation error, but these routes fall through to the default error handler. The rejected NaN is included in its error content, which cannot be serialized to a standard JSON response. All three routes returned 500 in the fresh probe. Confirmation, ingredient recipes, profile, and daily records already avoid this problem by omitting rejected input values from validation responses.

Expected: invalid numeric input consistently produces safe 422 responses; do not reflect non-finite values in the response. This does not demonstrate unauthorized access or persisted data damage.

Evidence: `source-api-probe.py`, final three requests. The persisted synthetic analysis remained unchanged after all five invalid requests. The parent independently confirmed the same three NaN failures against the isolated PostgreSQL HTTP app, with the record unchanged; see `postgres-invalid-revisions.json`.

## Implementation and meaningful test coverage

These are source/test mappings, not a claim that the entire existing suite was rerun by this subagent. The parent owns the full-suite result.

| Feature | Implementation finding | Relevant current tests |
|---|---|---|
| Accounts, cookies, session expiry/revocation | User lookup joins an unrevoked, unexpired token digest; password hashes are salted scrypt; logout revokes the current session | `tests/integration/test_accounts.py`: registration/salting, case-insensitive identity, hashed opaque session, secure cookie, logout stolen token, login rotation, expiry |
| Account isolation | All API meal/case/job routes pass the authenticated owner into their queries; malformed job parent links are excluded; profiles and daily aggregates key by authenticated user | `test_accounts.py`: foreign meal read/patch/reply/mode/confirm/job, foreign cases, malformed links, legacy ownerless records, owner spoofing; `test_profile.py` and `test_daily_tracking.py`: separate accounts with spoofed query/header IDs |
| Origin/header and private responses | All mutations require the custom header and exact configured Origin when present; private paths are no-store | Auth/profile/tracking integration tests check missing security header, cross-origin rejection, anonymous requests, cache headers |
| Profile equations and bounds | Decimal Mifflin equation, documented factors/goal adjustments, half-up goal/macros; unrounded BMI/energy guard conditions; guarded targets are all null | `tests/unit/test_personalization.py`: independent male/female examples, both coefficients and all activity factors, exact rounding boundaries, BMI boundary, minimum-energy boundary, combined guards, strict finite fields |
| Profile persistence and revision conflicts | Atomic conditional update; unique owner key guards simultaneous first creation; valid guarded profiles still persist | `test_profile.py`: fresh DB session persistence, recomputation, conflict/retry, rejection without mutation, no AI/queue calls; new simultaneous-write probe below |
| Meal-derived daily totals | Only owned confirmed meals with a consumed date and non-null calories are summed; manual calories replace rather than add to this total | `test_daily_tracking.py`: owned/status/date aggregate exclusion, manual override and clearing, repeated confirmation cannot double-count |
| Missing values, zero, trends | Nulls remain gaps, explicit zero remains recorded; exactly 30 inclusive dates; calorie averages use observed calorie days; weight change uses first/last recorded dates | `test_daily_tracking.py`: missing history, leap/year/minimum date windows, observed-day average, first/last weights and single-weight case; frontend gap/zero/chart test |
| Exercise and balance | Fixed resting ×1.2 baseline plus explicit exercise; profile activity not double-counted; null prerequisites withhold balance; guarded profiles cannot generate balance | `test_daily_tracking.py`: positive surplus/deficit/zero, missing prerequisites, guarded profile, zero vs unknown exercise, bounds/non-finite values, older-client preservation |
| Intake completeness | Exactly five strict boolean categories; all must be true; omitted newer field preserves old value; null explicitly clears | `test_daily_tracking.py`: all-five requirement, partial/invalid coverage, older-client preservation, explicit clearing; bilingual frontend exercise/coverage save test |
| Dates | Server uses Asia/Hong_Kong; exact ISO dates; lower bound and future date restrictions; confirmation defaults to server today | `test_daily_tracking.py`: malformed/future dates, invalid confirmation date, Hong Kong midnight, year/leap boundaries; S2 covers the missing open-tab rollover case |
| Browser stale responses and conflicts | Session version counters discard old meal responses; user-specific meal key; profile/diary request counters prevent older reads replacing later date selections | Frontend in-flight meal/session change test; profile conflict test; API sequential two-browser conflict tests. S1 covers the missing dependent-display refresh after conflict recovery |

## Additional simultaneous-write checks executed

`source-concurrency-probe.py` ran in the fresh API Docker image with an isolated temporary SQLite database, separate database sessions and separate clients per request, using a barrier to start each pair together. All checks passed:

- Two initial profile writes: exactly one 200 and one 409.
- Two profile updates from revision 1: exactly one 200 and one 409.
- Two initial daily-record writes for one user/date: exactly one 200 and one 409.
- Two daily-record updates from revision 1: exactly one 200 and one 409.
- Two confirmations of one completed meal: exactly one 200 and one 409.
- Final daily aggregate: revision 2, one confirmed meal, 155 kcal; no duplicate contribution.

This strengthens the existing sequential conflict tests. It does not substitute for PostgreSQL concurrency or migration tests. The current integration fixtures create tables from metadata, use SQLite, and share one Session across ordinary test clients; therefore they do not by themselves establish PostgreSQL migration behavior or true simultaneous-request handling.

## Scope and limits

No source-level account-isolation, arithmetic, or aggregate defect was found in the reviewed valid-input paths. The issues above are specific reproducible gaps, not evidence of broader compromise. No credentials, external accounts, model calls, or real health data were used. No Git commit or push was performed. Follow-up fixes, if any, must be verified against a separate working checkout so this baseline and its reproduction remain intact.
