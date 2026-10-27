# Daily tracking verification — 2026-10-27

Scope: the `test` increment based on
`ea39740ee1af3d4fe44a7c8665906161156e4d51`. Original branches, the Week 7 tag and
the public ECS deployment remain unchanged. The isolated preview uses port 8001.

## Automated checks

The complete `pytest -q -p no:cacheprovider tests/unit tests/integration` run passed
**594 tests**, including 81 new tests in `tests/integration/test_daily_tracking.py`.
Two existing dependency deprecation warnings remain. Whole-repository Ruff,
JavaScript syntax, HTML ID uniqueness/label references and Git whitespace checks
passed. Two authenticated API/worker smoke tests passed on the upgraded preview.

The new tests cover:

- Thirty consecutive dates across leap days, month/year boundaries and the minimum
  supported date; Hong Kong midnight defaults and rejection of future dates.
- Missing versus explicit-zero values, independent weight-only days, daily
  aggregation, manual override/reset, and summary denominators/first-last weights.
- Filtering by owner, confirmation state and consumed date; inaccessible ownerless
  meals, separate accounts, logout and CSRF/origin/no-store behavior.
- Initial/update revision conflicts, required nullable fields, input bounds,
  non-finite values, numeric coercion, owner injection and sanitized errors.
- Backdated/default meal confirmation, repeated confirmation conflict, preserved
  profile inputs/references and absence of new AI jobs from diary operations.

Use the Docker commands in [the account guide](../accounts.md) to reproduce the
unit/integration and smoke checks. No Qwen key is needed. The smoke check writes
synthetic meals; run it only against the isolated preview or a disposable database.

## PostgreSQL migration and concurrent writes

Disposable PostgreSQL 16 containers used temporary storage, no published ports and
no external network. They were removed after verification.

- Fresh upgrade to 0008 and populated 0007→0008 upgrade passed. Old users, sessions,
  profiles, owned/ownerless analyses, cases and jobs preserved their existing columns.
- A confirmation at 17:30 UTC received the next calendar date in Hong Kong.
  A legacy confirmed row without `confirmed_at` used `created_at`; an unconfirmed
  row kept a null date. Ownership was unchanged.
- Downgrade to 0007 removed only the new tracking schema, and re-upgrade passed.
  Alembic metadata comparisons found no drift at the new head.
- Thirteen invalid constraint cases were rejected, including range, revision,
  earliest date, NaN/Infinity and nonexistent owner inputs. Nullable clearing was
  accepted; deleting a synthetic owner cascaded its daily records.
- Two simultaneous first saves returned one 200 and one 409, leaving one row at
  revision 1. Concurrent updates likewise returned 200/409 and one revision 2.
  In both cases the persisted values matched the successful response.

The preview database was backed up before its additive migration. Its existing
confirmed 155-kcal sample meal and saved 80-kg profile survived the upgrade.

## Browser workflow

All example weights and calorie entries belonged to a dedicated synthetic account.

- Saved today's weight and calorie total and observed both summaries/charts update.
- Created a meal through the actual worker, confirmed it for a past date, and saw
  155 kcal appear in that date's automatic total.
- Entered a 2100-kcal manual total and verified the source label showed the separate
  155-kcal meal sum without adding it. Clearing the total restored 155 kcal.
- Updated the same date from a second authenticated session. The stale browser
  showed a conflict and required explicit reload before further editing.
- Selected a historical window, returned to today, and checked the daily table.
  Missing observations remained dashes and chart gaps; sources and meal counts
  matched the saved data. Weight-axis scaling was disclosed beside the plot.
- Reload restored the diary, charts and confirmed meal date. The profile reference
  stayed unchanged. Logout returned to the account page and removed private views.

A separate temporary JavaScript harness checked empty charts, explicit zero,
adjacent versus missing-date segments, finite axes for constant weights, and
chart/table clearing on logout. Browser layout was visually inspected.

## Limits

These checks establish persistence, privacy boundaries and arithmetic behavior,
not nutritional measurement accuracy. A meal-derived day may be incomplete, and
daily tracking does not infer missing food or measurements. There is no historical
target snapshot, edit audit or automatic profile update. The charts show a rolling
30-day window, not a calendar month. See [tracking policy](../tracking.md).

The existing GitHub Actions workflow does not run on `test` pushes. These are local
test results, not a reported remote CI run. No real-provider call or public deploy
was included.
