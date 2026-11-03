# Independent account verification — 2026-10-27

Scope: the experimental `test` branch based on
`93ad2074226e8e7c7dcd3df058605f8a233dca35`. This evidence concerns independent accounts,
not personalized nutrition targets, trends, Google OAuth or a public deployment.

## Automated checks

- `pytest -q tests/unit tests/integration`: **420 passed**, including the previous
  359 tests and 61 account/security cases. Tests use real registration and cookie
  sessions, isolated SQLite databases and mocked model responses where appropriate.
- `ruff check --no-cache .`: passed across the repository.
- Both HTML script blocks passed JavaScript syntax checking.
- Authenticated smoke checks against the isolated `nutrichat-accounts` Compose
  project: **2 passed**. These exercised real PostgreSQL, the worker and internal
  HTTP with the offline demo provider. No Qwen quota was used.
- Two existing dependency deprecation warnings remain (Starlette/AnyIO and
  python-json-logger). They did not cause failures.

The account regression cases check anonymous access, foreign reads and every meal
mutation, job/case ownership, ownerless historical records, forged identity fields,
normalization/duplicate usernames, password salt/hash and response redaction,
session expiry/rotation/logout replay, cookie attributes, CSRF headers/origins,
registration closure and rate limits. Missing and foreign record IDs return 404.

A separate concurrent-request check produced one success and one conflict for
simultaneous mixed-case registrations, leaving exactly one user and session. Two
independent browser sessions could log in concurrently; logging out one did not
invalidate the other. This check used SQLite, not a production load test.

The authenticated workflow helper was checked with an offline HTTP transport for
cookie/header preservation, untrimmed passwords, missing credentials and logout
on both success and failure. A disposable SQLite seed check verified that all
three synthetic cases receive the selected existing owner, and that missing or
unknown owners fail before insertion.

## PostgreSQL migration checks

Used a disposable PostgreSQL 16 container with a temporary filesystem and no host
ports. It was stopped and removed afterward; existing databases were not touched.

- Fresh migration to `20261027_0006` succeeded; Alembic metadata check found no drift.
- Downgrade to 0005 and re-upgrade succeeded on the disposable database.
- A populated 0005 analysis, case and their jobs retained their IDs and values after
  upgrade; both ownership columns were null.
- Duplicate usernames and nonexistent user foreign keys were rejected. Deleting a
  user with owned records was restricted.
- A populated downgrade/re-upgrade retained meal/case/job records but discarded
  account/session/ownership data, as the migration specifies. A real rollback needs
  a compatible backup, not merely an older application image.

## Browser workflow

Checked the isolated preview at `http://localhost:8001` using synthetic accounts:

1. Anonymous `/app` redirected to the account page.
2. Account A logged in, submitted `100g egg`, received 155 kcal through the offline
   worker, and confirmed the persisted meal.
3. A second browser tab restored the same confirmed record.
4. Logout returned both tabs to sign-in and cleared displayed meal data.
5. Account B had an empty history and no restored A record.
6. Logging back into A restored its confirmed meal.

Registration is covered by real HTTP integration/smoke checks. Browser credentials
were pre-created through the local test API; no real user password was changed.

## Reproduction and limits

Use [the account guide](../accounts.md) for Compose and test commands. Smoke tests
create two synthetic accounts per run; repeated runs may reach the deliberate
five-registration-per-IP/hour limit. Use an existing dedicated smoke account for
repeated runs instead of disabling rate limiting.

Public Compose rendering and a temporary Nginx syntax/routing check passed with
a synthetic certificate and no host ports. Login/auth routes reached the API,
anonymous `/app` redirected to login, and `/metrics` returned 404. No production
certificate or deployment was changed.

These checks do not establish public TLS configuration, Qwen reliability, production
load capacity or comprehensive security certification. The rate limiter is per
process, browser cross-tab notifications require working localStorage, and password
recovery/MFA/Google login are not implemented. The public ECS application and the
frozen `w07-midterm` submission are unaffected. A `test` push does not trigger the
existing main-only push workflow; local checks are reported separately from CI.
