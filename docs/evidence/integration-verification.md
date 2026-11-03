# Integrated branch verification — 2026-11-03

## Source and scope

Merged `nutrichat` (`7c9525dc3a6af5ae63bc9dcfc5be19534b856bf1`) and local
`test` (`5af1780`) on `integrate/nutrichat-test`. Verification ran on the merge
working tree before its commit; the service fingerprint below identifies the
actual implementation independently of documentation/commit metadata.

All food data files match `nutrichat` exactly: **200 ingredients, 350 recipes**.
Catalogue SHA-256: `d9230087a5bd493afbc6d76a5c09e9b549df7746817f55e5ac43d1956a4e9db2`.

API, AI and worker in both isolated previews match service SHA-256
`ef910460f08f8a6dfb0a688632493f42348d54a32a6087ef76c282c3cc17b0fb`.
See [runtime fingerprints](integration/runtime-fingerprint.json) for the algorithm
and six container comparisons. Original worktrees, branches, preview databases,
public ECS deployment and the course submission tag were not modified.

## Automated checks

| Check | Result | Scope |
| --- | --- | --- |
| Python 3.11 unit/integration suite | **1,049 passed**, 2 smoke tests deselected | All existing and merged regressions, no live model calls |
| Frontend DOM suite | **35 passed** | Language switching, preserved fields, account/session races, profile/diary/charts, custom recipes and offline correction |
| Real-service smoke tests | **2 passed** | Authenticated API/worker/PostgreSQL offline stack |
| Ruff and Git whitespace checks | Passed | Current source and merge diff |
| Source data comparison | Unchanged | All `services/common/data` files match `nutrichat` |

Python emitted two existing dependency deprecation warnings. Frontend tests ran
on the local Node installation; CI is configured for Node 22. These are local
results, not a claim that a new GitHub Actions run has already passed. Counts from
previous reports are not added to these totals.

New regressions cover ownership on `/ingredients`, foreign/anonymous/ownerless
record rejection, CSRF, non-finite values, ingredient recipe → dated confirmation
→ private daily/trend aggregation, and correct effective provider reporting.
Model checks preserve unknown-food rejection, prevent model-supplied custom
recipes, and verify acknowledgment and replacement context boundaries.

## Database and key-free workflow

An isolated real PostgreSQL database was first migrated to the original
`nutrichat` revision `20261017_0005`. Two synthetic existing meals were inserted,
then upgraded through account/profile/tracking migrations to `20261027_0008`.
All original meal fields stayed identical; ownership remained null; a confirmed
meal at 17:30 UTC correctly received the following day's Hong Kong consumption
date. New users, sessions, profiles and daily-record tables were present.
See [upgrade evidence](integration/migration-upgrade.json).

The [offline durable check](integration/offline-check.json) passed registration,
pending DB state while the worker was stopped, background completion, correction
from **155 to 310 kcal**, confirmation/reload, locked edits, a saved profile,
manual calorie override/clear, daily weight, 30-day data and matching logs/metrics.
It used the separate `nutrichat-integrated-demo` project on port 8006 and revoked
its synthetic account session. It does not establish Chinese model recognition.

## Real HKUST integrated workflow

The final [HTTP acceptance record](integration/live-acceptance.json) contains
**12 successful workflow checkpoints using four model-facing submissions**, not
12 independent accuracy samples. Provider: HKUST; model: `gemini-2.5-flash-lite`;
isolated application: port 8005.

- Registration/session, protected routes and the 550-record catalogue.
- Synthetic profile references for both goals: 2,720 kcal muscle-gain reference
  and 2,330 kcal fat-loss reference for the stated fixture inputs.
- Basic `一份番茄炒蛋，两个水煮鸡蛋`: 365.2 kcal with visible reference assumptions.
- Switch the same record to Advanced, supply missing details and explicitly
  review the batch recipe: 365.2 kcal.
- Replace the whole meal with `白米饭150克熟重，水煮鸡蛋80克熟重`: 319 kcal,
  with the old dish removed from the current interpretation.
- `豉油鸡200克熟重，可乐鸡翅75克熟重（已去骨），蒜蓉空心菜150克熟重。`:
  exact expected dish IDs/weights, 743.8 kcal.
- Rice plus `月球紫晶兽肉`: unknown food remains unresolved; all totals withheld.
- Explicit chicken/oil/soy-sauce batch recipe replaces only the unknown item;
  rice remains, producing 244.8 kcal without another model request.
- Confirm for a chosen past date, verify calorie aggregation, manual override and
  clear, two weight records and a 30-day response with missing dates left blank.
- A second account cannot read the first account's meals, jobs, profile or trends.
- Logout revokes access; fresh login restores the same records.
- Stop and restart **all four isolated services**, including PostgreSQL: session,
  confirmed meal, profile and trend response remain identical.

The sampled inputs and reference arithmetic are workflow tests, not a clinical
nutrition accuracy score or a guarantee about every model response.

## Failures retained and repairs verified

Initial HKUST output used a Chinese preparation label and later an invalid weight
state. Native JSON-schema mode was also rejected by the school gateway. The fix
keeps supported JSON-object mode, adds the complete schema to the prompt, and
normalizes only exact equivalent enum labels. Invalid weight states, unknown
fields and invented nutrients are still rejected. No automatic retry or provider
fallback was added. See [the diagnostic record](integration/provider-schema-debug.json).

A later whole-meal replacement retained an old dish. The identity guard blocked
it correctly. Model instructions now share the same explicit replacement scope
as final validation, so old foods are not retained after a full replacement.
The original failed record, direct retest and final integrated pass are recorded
separately; see [replacement diagnosis](integration/provider-replacement-debug.json)
and [pre-fix acceptance](integration/live-before-replacement-fix.json).

An independent code review also found that “是的” after a real server weight
question could become an unsupported food, including after changing meals.
Narrow user-bound acknowledgment checks and positive/negative regressions now
cover both cases. Arbitrary assistant suggestions and unknown additions remain
blocked.

Two intermediate acceptance runs stopped because the check harness did not yet
handle a legitimate `resolved` confirmation question, then assumed every detail
had a `kind` key. These were harness defects, not application failures. They were
corrected without product changes; their partial reports remain under
[integration evidence](integration/) rather than being counted as completed runs.

## Qwen and browser checks

[Two final direct Qwen checks](integration/qwen-live.json) passed: soy chicken
200 g matched `dish_251` (468.9 kcal), and an unknown fictional food had no totals.
This is narrower than the full HKUST HTTP acceptance. An earlier overlapping probe
produced no report during the scheduled stack restart and is excluded. Ollama
remains an experimental adapter; no new live Ollama acceptance is claimed.

A fresh Chrome Guest session tested the real offline UI on desktop and a
390 × 844 mobile viewport in both languages: registration, profile save, 155 →
310 kcal correction, dated confirmation, daily records, charts, logout and fresh
login. Two daily calorie values (1,800 and 310) produced a 1,055 average; 70 →
69.8 kg produced a −0.2 kg change. Missing days remained blank. All four served
JavaScript assets matched the working files after the final UI rebuild; reload
preserved the same records. The expected anonymous `/auth/me` 401 after logout
was not a JavaScript failure.

See [the illustrated integrated guide](../../demo/INTEGRATED_GUIDE.md) and
[capture manifest](../../demo/images/2026-11-03/capture-manifest.json). Images are
synthetic examples; two plotted days do not represent a month of real user data.

## Boundaries

Food coverage remains finite; model extraction can still fail. Reference portions,
recipes and personal targets are approximations. There is no password recovery,
Google sign-in, reusable personal recipe library, historical target snapshots,
idempotency, automatic job retry or interrupted-claim recovery. Old ownerless
shared meals are retained but are not assigned to new accounts. No existing
user database was copied into this preview and no public deployment was changed.
