# Personal profile verification — 2026-10-27

Scope: the `test` branch increment based on account commit
`d5f1a50a8229a12b8a21c5137d4ca9c47a0979ec`. No original branch, public deployment or
Week 7 submission snapshot is changed by these checks.

## Automated checks

`pytest -q -p no:cacheprovider tests/unit tests/integration`: **513 passed** in the
final complete run, comprising the prior 420 tests and 93 new profile/calculation
cases. Two existing dependency deprecation warnings remain. Whole-repository Ruff
passed. JavaScript syntax and HTML ID/label references were checked separately.

New coverage includes independently calculated male/female examples, both goals,
all activity levels, round-half-up boundaries, consistency of macro energy, and
guard comparisons before rounding. Schema/API tests cover required fields,
inclusive bounds, numeric strings/booleans, fractional age, NaN/Infinity, unknown
fields, owner/calculated-value injection and invalid updates preserving old data.

Integration tests use real login sessions and verify empty-profile behavior,
independent database-session persistence, logout/login restoration, cross-account
isolation, spoofed identity headers/query values, CSRF/origin checks, no-store,
stale/future revisions, first-save conflicts, and no AI/worker job creation.

Reproduce with the account preview's Docker image and configuration, following
[account test commands](../accounts.md). The focused files are
`tests/unit/test_personalization.py` and `tests/integration/test_profile.py`.

## PostgreSQL migration and concurrency

Used a disposable PostgreSQL 16 container with temporary storage and no published
ports. The verifier joined its network namespace; existing databases were untouched.
The temporary container was removed afterward.

- Fresh upgrade to 0007, populated 0006→0007 upgrade and re-upgrade passed. Alembic
  metadata checks found no schema drift.
- Seeded users, sessions, owned/ownerless meals, cases and jobs retained every
  compared field across upgrade and downgrade. Downgrade dropped only profiles.
- Invalid range/enum/revision values, NaN/Infinity and nonexistent owner IDs were
  rejected by database constraints. Updates persisted with UTC timestamps, and the
  profile foreign key cascaded on deletion of its test owner.
- Simultaneous initial saves returned exactly one 200 and one 409. Concurrent
  updates with the same revision also returned one 200 and one 409, retaining a
  single consistent new revision.
- Authenticated endpoint checks returned the expected computed envelope; anonymous,
  missing-security-header and non-finite input checks returned 401/403/422.

## Browser workflow

The local preview at `http://localhost:8001` used synthetic accounts and synthetic
body measurements, not the user's personal information.

- Empty profile form required an explicit activity selection.
- Saving the sample profile produced the expected 2900 kcal muscle-gain reference.
- Unsaved edits hid the old reference; changing to fat loss and saving produced
  2480 kcal with corresponding macro values.
- A second tab's stale edit displayed a conflict and explicit reload action.
  Reload recovered the current saved profile rather than overwriting it.
- A low-weight fat-loss example saved its inputs but displayed a limitation message
  with no numeric targets. Restoring the ordinary example restored the reference.
- Reload retained the saved profile and existing confirmed meal. The existing meal
  content survived the migration and was independent of profile editing.

## Limits

Formula tests establish arithmetic and application behavior, not clinical accuracy
or effectiveness for muscle gain/fat loss. Goal offsets, activity multipliers and
macro split are disclosed product assumptions; see [the calculation policy](../personalization.md).
No Qwen call was needed for profile verification. This increment stores the current
profile only; daily logs, historical targets and trends are not implemented.
The `test` push does not trigger the existing main-only push CI workflow; these
local checks are not reported as a GitHub Actions run.
