# Week 13 final verification — 15 November 2026

The final automated release checks passed. Independent live API review completed
105 post-fix assertions with no failed assertions and one explicitly unmet
calculation check. The retained limitations below are part of the release scope;
this is not a claim that every meal description or every recipe works perfectly.
All accounts, profiles and meals created for these checks were synthetic.

## Source identity and environments

The source began at `c5a9ebd02aa358ea68a07832c3ba3dcaec296c4c`. Final review added
bounded phrase handling in `services/common/food_matching.py` and regressions in
`tests/unit/test_food_matching.py`; the release also packages documentation and
evidence. This report covers the original 15 November package at
`6b87aef772f7cfde139a383c866e5576ea955cb3`, preserved with its original annotated
tag object under `archive-w13-final-6b87aef`. Resolve that historical source using
`git rev-parse 'archive-w13-final-6b87aef^{commit}'`; the annotated tag object is
not the source commit. The updated `w13-final` package is described in the
[current release record](../../submissions/week13/README.md). Its publication
does not rerun or extend the dated evidence below.

- Fresh offline project: `nutrichat-w13-20261115`, localhost **8013**, new isolated
  PostgreSQL volume. Before first use, users, analyses, jobs and daily records were
  empty. It used `.env.example` with no private provider key.
- Live project: `nutrichat-ui-20261114`, localhost **8008**, HKUST. It reused the
  verified final build and retained its separate database. Existing public ECS and
  `nutrichat` were not deployed or modified.
- Final service-source SHA-256: `61fa01f506970553c5a819ff1925a9dab65a09c28e444cf103aac545796309b1`.
  All 40 Python/data/HTML/JavaScript service files matched in API, AI and worker.
  [Live fingerprint](week13/live-final-fingerprint.json).
- The automated build checked all 103 packaged source/test files against the
  working tree. [Automated fingerprint](week13/automated/source-runtime-fingerprint.json).
  Subsequent documentation packaging does not change the verified application.

## Automated and fresh-start checks

| Check | Final result | Evidence |
| --- | --- | --- |
| Backend regression suite | **1,230 passed**, 2 live smoke tests deselected, 2 dependency deprecation warnings | [Log](week13/automated/backend-tests.log) |
| Food identity regressions | **200 passed**; a subset of the backend suite, not an additional total | [Log](week13/automated/final-food-matching.log) |
| Frontend | **56 passed** after `npm ci`; frontend/test inputs unchanged by the backend-only fix | [Log](week13/automated/frontend-tests.log) |
| Running-service smoke tests | **2 passed** in the isolated offline stack | [Log](week13/automated/smoke-tests.log) |
| Ruff | Passed | [Log](week13/automated/ruff.log) |
| Chinese regression corpus | 7 cases / 5 categories valid; no model calls or accuracy measurement | [Log](week13/automated/chinese-corpus.log) |
| Fresh database and migrations | Empty initial application tables; head `20261030_0010` | [Initial state](week13/automated/fresh-database.json), [migration](week13/automated/alembic-current.log) |
| Durable lifecycle | Pending SQL rows, worker completion, 155→310 kcal correction, confirmation/readback, locked edits, profile/tracking and operational signals passed | [Harness report](week13/automated/demo-check.json) |
| Stop/start persistence | Same named volume and containers; confirmed meal, jobs, profile and daily record unchanged | [Readback](week13/automated/restart-persistence.json) |

Restart verification used PostgreSQL readback plus HTTP readiness, not a newly
authenticated post-restart HTTP read. Browser reload/login persistence was checked
separately. Unit/integration tests mostly use controlled model responses and
SQLite; they do not establish PostgreSQL concurrency or live model reliability.
See [summary](week13/automated/summary.json) and
[commands](week13/automated/backend-commands.json).

## Independent real-provider review and repairs

The independent reviewer received the repository/runtime and audit task without
prior conversation memory. It made **8 initial plus 6 deliberate post-fix requests**
(14 total; final cap 15), with **no automatic retries**. Structured answers,
ingredient edits and account/tracking checks do not call the model.
[Final review](week13/live/final-review.txt),
[budget/sanitization record](week13/live/final-sanitization-budget-check.json).

Initial checks exposed phantom foods from ordinary explanatory clauses such as
“可食净重”, “没有称重”, “也没加任何其他油” and portion-correction metadata. The
“另吃” wrapper also caused a known rice item to lose its identity. The fix accepts
only bounded complete clauses; unknown additions must still withhold all totals.
One intermediate implementation failed two new wrapper tests and was corrected
before the final build. [Preserved first review](week13/live/first-pass-review.txt)
and [intermediate test failure](week13/automated/candidate-1-failed-targeted/final-food-matching.log).
The raw first-pass harness also incorrectly expected Qwen although the runtime
correctly reported HKUST; its narrative identifies this as a harness error.

| Exact replay or workflow | Final observed outcome |
| --- | --- |
| 青椒肉丝150克，称的是炒熟后实际吃下的可食净重。 | Correct dish, 150 g, completed **149.1 kcal** |
| Unknown invented dish plus separate rice | Unknown remains unresolved; rice retained; all totals withheld until actual ingredients are supplied |
| Actual-ingredient recovery | Consumed basis **359.5 kcal**, batch basis **244.8 kcal**; other meal items retained |
| Three pieces of pork without weighing | Asked for grams without a phantom food; completed after explicit **90 g** |
| Advanced tomato/egg recipe and natural correction | Recipe review required; correction to 150 g completed at **157.7 kcal**, confirmed and read back |
| Zero-oil cold cucumber | No phantom foods; zero-oil facts retained. Cooked-weight question remains, so completed arithmetic was **not verified** |
| Accounts and private data | Owner/stranger/anonymous checks, revocation, invalid/stale writes and confirmed-meal immutability passed |
| Daily diary and trends | Three confirmed meals sum to **551.6 kcal**; manual override/clear, exercise, coverage and 30-day data passed |

The post-fix report records **105 passed, 0 failed, 1 unmet** assertions, not a
105-meal accuracy result. [Post-fix summary](week13/live/postfix/summary.json).
Both disposable sessions were revoked; replay returned 401.

## Visible browser review

The implementing reviewer separately operated the real in-app browser using a
synthetic account. This is assistant-driven UI verification, not an external
human-user study or a team rehearsal. Its one initial HKUST request brings the
combined review total to **15 model-triggering submissions**. Frontend assets
were unchanged by the subsequent phrase fix; final backend replays are above.

- Register/sign in; Basic `番茄炒蛋200克，熟米饭150克` gave **405.2 kcal**.
- Switch to Advanced, change whole-batch oil 15→5 g; acceptance clears and survives
  language switching. Reacceptance gives **361 kcal**.
- An unsent correction blocks confirmation even after closing the editor. Clearing
  it restores confirmation. Confirm/reload/logout/login restores the saved meal.
- Synthetic profile 30 years, 175 cm, 75 kg, male coefficient, light activity,
  muscle-gain goal yields a **2,450 kcal/day** reference.
- Diary automatically sums **361**, manual **2100** replaces it, and clearing
  restores **361**. Two synthetic dates produce a 30-day chart with **2/30**
  recorded days, **1230.5 kcal** recorded-day average and **−0.4 kg** weight change.
- At 390×844, document width remains 390; the viewport was reset afterwards.

[Browser check record](week13/browser/browser-checks.json) and
[seven screenshots with captions](../../submissions/week13/DEMO.md#captured-synthetic-browser-examples).

## Remaining limits and release interpretation

Cold cucumber still asks whether its weight is cooked; the reviewer did not invent
that fact to force completion. Mixed millilitre/gram input was neither fixed nor
replayed: its initial model draft assumed 250 ml as 250 g, but the identity guard
withheld totals. Do not claim validated volume conversion; supply edible grams.
[Cold-dish evidence](week13/live/postfix/cold_dish_basis_limitation.json),
[original mixed-unit attempt](week13/live/provider_07_mixed_units.json).

Other documented limits remain: finite 200-ingredient/350-recipe coverage, recipe
and portion assumptions, imperfect model output/household wording, no automatic
retry or interrupted-job recovery, and no measured nutrition/security/load audit.
Health checks do not prove provider quota. Human team rehearsal and public
redeployment are not represented by these checks.

Local results do not establish hosted CI for a later commit. Verify the submitted
SHA in [fork Actions](https://github.com/JunlangHuang004/MAIE6000C-starter/actions)
and [mirror Actions](https://github.com/JunlangHuang004/Maie-6000c-starter-Junlang-Huang/actions).
The original release required the published `test` branches and then-current
`w13-final` tags to resolve to the same commit. Reproduce this historical package
from `archive-w13-final-6b87aef`; current branch/tag requirements are in the
[current release record](../../submissions/week13/README.md). Canvas submission
remains a separate team action.
