# ADR 0003 — Private tracking and final release boundaries

## Status

Accepted for the `test` final package, 2026-11-15.

## Context

The meal-estimation prototype needed independent accounts and a way to review
confirmed meals across days. Profiles, exercise entries and incomplete food logs
introduce additional uncertainty and private data. The existing `nutrichat`
branch, Week 7 snapshot and public deployment also need to remain reproducible.

## Decision

Enforce ownership in the API using opaque account sessions. Store only hashed
session tokens and password hashes server-side. Do not infer ownership of old
shared meals: migration 0006 retains them with null owners and account APIs do
not expose them to new users. Profiles and daily records belong to the session's
user; clients cannot select another owner.

Keep profile references and tracking deterministic in the API. They do not call
the model or send profile measurements in meal prompts. Migrations 0007–0010 add
profiles, daily records/meal dates, exercise and intake coverage. Use revision
checks on mutable records and lock a meal/date after confirmation. A manual daily
calorie total replaces the confirmed-meal sum; absent records remain gaps.

Calculate approximate daily expenditure as resting energy × 1.2 plus explicitly
recorded exercise. A blank exercise value is unknown, distinct from zero. Report
intake coverage as self-reported, and do not infer that logged meals cover an
entire day. Current profile changes can affect historical displayed balances;
no historical target snapshot is claimed.

Organize the interface into Meals, Daily diary, Trends and My goals. Preserve
unsaved values when switching panels/language, require explicit recipe review,
and prevent confirmation while a correction remains unsent. These presentation
changes do not submit a new meal or make assumptions into measured facts.

Publish the final source on `test` with checkpoint `w13-final`. Use an isolated
local Compose project (`nutrichat-merged-qwen`, loopback port 8005); keep the
key-free engineering check separate (`nutrichat-integrated-demo`, port 8006).
Do not redeploy the existing public server or move the `nutrichat` branch as part
of this release. A Git push is neither cloud deployment nor Canvas submission.

## Consequences and trade-offs

Account-private data and saved estimates survive restarts in PostgreSQL. Source
snapshots and separate Docker volumes allow the final workflow to be reviewed
without replacing earlier demos. The small six-food offline provider can verify
durable service boundaries, but only a real configured Qwen/HKUST request can
show live model interpretation.

The catalogue remains finite at 200 ingredients and 350 reference recipes. It
retains nutrient values and food identities, with an explicit 50 g peeled-egg
portion/source metadata addition. Reference recipes, model extraction and energy
formulas remain estimates. Repeated model calls are not a substitute for reporting
failures.

We retain a single-worker prototype with finite timeouts. Automatic retry,
interrupted claimed-job recovery, idempotency keys, password recovery, account
deletion and historical target snapshots are deferred. There is no production
security/load or clinical-accuracy claim.

## Alternatives considered

- Shared histories or assigning old meals to the first registrant: unacceptable
  ownership ambiguity; preserve the rows without granting access.
- Asking a model to calculate profiles or daily totals: adds private-data exposure
  and nondeterminism without a need for language interpretation.
- Adding exercise to activity-adjusted maintenance: risks counting activity twice;
  use the explicit fixed baseline and explain its limitations.
- Replacing the existing deployment during a course freeze: changes a separate
  operational system; retain local release verification and deploy separately.

See [architecture](../architecture.md), [tracking](../tracking.md),
[operations](../operations.md) and the [final package](../../submissions/week13/README.md).
