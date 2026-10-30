# Week 7 — Midterm Milestone Demo

## Team and checkpoint

- **Team:** NutriChat
- **Repository:** https://github.com/JunlangHuang004/MAIE6000C-starter
- **Demo branch:** [`nutrichat`](https://github.com/JunlangHuang004/MAIE6000C-starter/tree/nutrichat)
- **Required tag:** `w07-midterm`
- **Primary artifact:** `submissions/week07/README.md`
- **Updated:** 2026-10-31
- **Catalogue version:** `2026-10-31.1` — 200 ingredients and 350 reference recipes

This milestone covers the Chinese/English interface, strict food-identity
validation, structured ingredient recipes and the expanded Chinese catalogue.
Use `w07-midterm` for grading; branch HEAD may advance later. Historical
verification records retain their dates and source versions, and archived
checkpoint tags preserve earlier snapshots. Use the full commit resolved from
the required tag in Canvas, not the annotated tag object's SHA:

```sh
git fetch origin --tags
git rev-parse 'w07-midterm^{commit}'
```

If an older checkout already has a different local tag, compare the remote with
`git ls-remote origin 'refs/tags/w07-midterm*'` or use a fresh clone. Do not assume
an earlier Canvas SHA points to this refreshed version.

The [ingredient-recipe builder](../../docs/ingredient-recipes.md) lets a user
explicitly supply actual ingredients and consumed/batch portions for an unsupported
item and displays quantity provenance. It saves a custom recipe inside that meal;
it does not add a global catalogue food, a personal recipe library or individual
accounts. Repository updates do not submit or amend Canvas automatically.

| Member | Agreed responsibility |
| --- | --- |
| Junlang Huang | Lead development and feature integration |
| Jiacheng Cao | Supporting development |
| Zhou Ran | Documentation and deployment |
| Yixing Huang | Testing and validation |

These responsibilities were supplied by the team representative; they do not
claim that each member personally executed every recorded check.

## 1. Direction and working slice

People increasingly care about their health but often do not know the nutrition
of familiar meals. NutriChat helps students and busy home-food eaters estimate
calories, protein, fat and carbohydrates from descriptions, especially Chinese
food. It supports everyday awareness; uncertain recipes and portions prevent us
from claiming measured or medical accuracy.

The working slice is **describe → persist a queued meal/job → process
asynchronously → save nutrition or questions → review/correct → confirm and
reload**. Basic mode uses labelled reference portions and recipes when details
are missing. Advanced mode asks for edible weight, preparation, oil and editable
recipe details. Required unanswered questions leave totals empty. Confirmed
records cannot be edited.

The Qwen path has **200 USDA ingredient records and 350 project-authored Chinese
reference recipes**. Qwen interprets language; validated Python arithmetic
calculates nutrition from the catalogue. The interface can switch between
Chinese and English without changing food IDs, nutrient values or unsent form
entries. The original 388 records retain their English display mappings; the
162 new Chinese-first records use Chinese fallback where translations are absent.
This display feature does not improve model recognition by itself.

## 2. Run and inspect the demo

Start with the [self-guided TA demo](../../demo/README.md), which includes fresh
setup instructions, a browser walkthrough and an automated integration check.
The demo is a working system documented on GitHub; no screen recording or
in-person presentation is required. The [earlier terminal rehearsal](DEMO.md)
provides another way to inspect service boundaries.

1. Follow the Qwen setup and open **`http://localhost:8003/app`** directly. Local
   use requires no registration or login. The operator configures an authorized
   model key once; the repository does not distribute credentials.
2. Choose **中文** or **English** in the header. Basic mode estimates a meal such
   as `一份番茄炒蛋，两个水煮鸡蛋`. Inspect the interpreted foods, portions,
   recipe assumptions and nutrients.
3. Switch to Advanced and answer edible-weight, preparation and recipe questions.
   Required unanswered questions withhold totals.
4. Correct a consumed portion in conversation, complete remaining questions and
   inspect the recalculated values. Switching the interface language preserves
   unsent text, recipe quantities, batch yield and acceptance checkboxes.
5. Confirm and reload. Compare the same record ID, confirmed status and totals;
   later corrections are blocked. Follow the
   [illustrated sequence](../../demo/SCREENSHOT_GUIDE.md).
6. For reproducible engineering evidence without a model key, run
   `python3 demo/run.py start` then `python3 demo/run.py check`. The separate
   offline stack inspects a pending PostgreSQL job with its worker paused,
   resumes processing, checks correlated logs and saved results, corrects
   155 → 310 kcal, confirms, reloads and verifies locked edits. Its six English
   fixture foods do not prove Chinese-language extraction.

For unsupported-food handling, enter the synthetic unknown `200克月球紫晶兽肉`:
it must not receive another dish's estimate. Use **Build from actual ingredients**
to select reviewed real ingredients and consumed amounts or batch yield/portion.
Follow the [ingredient guide](../../docs/ingredient-recipes.md) for reproducible
calculation examples and confirmation. Soy-sauce chicken (`豉油鸡`) now has its own
catalogue recipe and is no longer an unsupported-food test case.

The Qwen route needs valid provider access and consumes the configured account's
quota. If access is unavailable, use the offline check and inspect the recorded
Chinese walkthrough separately; do not present fixture results as live Qwen
success. The public ECS deployment is older and is not the reference for this
demo.

## 3. Implementation status

| Status | Scope |
| --- | --- |
| Implemented | Durable API/job/worker/AI service integration; revision checks; Basic and Advanced modes; correction, confirmation and reload; deterministic food-identity checks; versioned food data and arithmetic; structured consumed/batch ingredient recipes; Chinese/English controls and catalogue search; bounded Qwen catalogue context; health, logs and metrics |
| Partial or limited | Coverage is limited to 200 ingredients and 350 reference recipes; new English food translations are deferred; model extraction and free-text ingredient recovery are fallible; recipe/portion defaults are estimates; the optional public deployment is older |
| Not implemented | Individual account registration/login and per-user record ownership in the local app; automatic retries, interrupted-job recovery, request idempotency, measured cooking losses and clinical validation |
| Rejected scope | Image-based nutrition estimation; the product remains focused on meal descriptions and clarification |

## 4. Architecture and changes from the starter

We retained the starter's API, PostgreSQL, durable job table, separate worker,
HTTP AI service, migrations and operational signals. The original case-triage
path remains available. The meal path uses `analyses` and nutrition jobs with
saved conversation, drafts and evidence, revision-based updates and confirmation.

The design moved toward a bounded food catalogue and deterministic calculation
instead of accepting model-generated nutrient numbers. Reference recipes make
Chinese dishes inspectable and editable. The interface update added
presentation dictionaries and served JavaScript assets without changing the
Qwen extraction prompt, database schema or calculation engine. Later changes add
a separate identity check before calculation, a structured ingredient-recipe API
and a bounded prompt shortlist (at most 120 candidate/context records). The
catalogue expansion changes versioned food data; it does not train the model.
Structured ingredient calculations reuse the worker path without another Qwen call.

See [architecture](../../docs/architecture.md), the
[design decision](../../docs/adrs/0002-source-backed-dual-mode.md) and
[API contract](../../docs/api-contract.md).

## 5. Evidence of integration

| Boundary | What can be checked |
| --- | --- |
| Input → database | HTTP 201 returns analysis/job IDs; PostgreSQL contains queued input and a pending job before processing |
| Database → worker | The worker claims the saved job and records its attempt and timestamps |
| Worker → AI service | Internal HTTP crosses the separate AI service boundary using the selected provider |
| AI → saved result | Validated food facts drive catalogue arithmetic; HTTP and PostgreSQL agree on the saved nutrients |
| Result → review | Correction creates another job; confirmation persists; GET restores the record and a subsequent edit returns HTTP 409 |
| Operational signal | Readiness HTTP 200, matching job log IDs and an increased AI request counter accompany the workflow |

The offline check produces fresh `demo/output/check.json` evidence for the TA's
run. The [expanded-source integration evidence](../../demo/evidence/offline-expanded-check-2026-10-31.json)
records the successful rebuilt offline check on `71a0ecd`, including durable
pending input, worker processing, correction, confirmation and operational signals.
It is distinct from the subsequent edible-state matching fix; it does not prove
live Qwen extraction. Earlier observations remain separately dated: the
[language-update offline check](../../demo/evidence/offline-check-2026-10-31.json),
[original verification](../../docs/evidence/week07-verification.md),
[28 October follow-up](../../demo/VERIFICATION.md) and
[31 October interface verification](../../docs/evidence/ui-language-verification.md)
and [English food-name checks](../../docs/evidence/qwen-english-verification.md).

## 6. Validation and limits

| Check | Recorded result and scope |
| --- | --- |
| Original checkpoint | 359 unit/integration tests passed; isolated PostgreSQL/HTTP rehearsal and two smoke tests passed |
| 28 October follow-up | 408 unit/integration tests and whole-repository Ruff passed; actual browser, worker and storage checks are recorded separately |
| 31 October interface update | **417 Python tests passed**, with two smoke tests deselected and two dependency warnings; **15 frontend DOM tests passed**; whole-repository Ruff passed |
| Expanded-source offline check on `71a0ecd`, 31 October | Rebuilt the isolated stack; durable HTTP/PostgreSQL/worker verification and both smoke tests passed. The saved report identifies the initial expanded service source. |
| Earlier matching follow-up | Initial 454 Python tests and 17 frontend DOM tests passed; 469 Python tests passed after correction/recovery refinements. The independent live baseline retained five failures; consult matching verification and QA memory for subsequent retests. |
| Ingredient builder on `7c841b1` | 545 Python tests, 26 frontend DOM tests and Ruff passed; real HTTP/worker/PostgreSQL batch calculation, confirmation and locked reload passed. See [verification](../../docs/evidence/ingredient-recipe-verification.md) and the dated independent browser report for its eight passing checks. |
| Initial Chinese catalogue expansion on `71a0ecd` | Passed 654 Python tests, 26 DOM tests and Ruff. Main browser flow and new-dish checks are attributed to this runtime in [expanded QA](../../docs/qa/reports/2026-10-31-expanded-demo.md). NC-QA-008 exposed a false unsupported result for a known dish with an edible-state annotation. |
| Current matching follow-up on `dae0b94` | Passed 664 Python tests and Ruff after adding ten regression cases for adjacent `已去骨` / `已去壳` annotations. UI and data are unchanged; the 26 DOM tests passed on the initial expanded source. The exact NC-QA-008 live retest passed with all three intended dishes and quantities; consult [expansion verification](../../docs/evidence/chinese-expansion-verification.md) for its actual outcome and final runtime source. |
| Language-update browser check | Switched language while queued and while editing an Advanced recipe; preserved values and acceptance, submitted, confirmed and reloaded the same saved result |
| Live Chinese food/weight matrix | **14 of 17** checks passed; 0 g, −100 g and 10001 g produced generic failures with no totals, rather than useful input-specific guidance |
| Expanded Chinese conversation | One failed attempt, then one deliberate successful rerun; both outcomes remain documented |
| Live English food-name checks | **19 of 21** scenarios passed; garlic gai lan was mapped to broccoli, and twice-cooked pork failed without nutrient totals |

The current CI workflow runs on `main` and `nutrichat` pushes and pull requests,
including the frontend suite. Local passing results do not establish the status
of a remote GitHub Actions run; inspect the run for the actual pushed commit.

Catalogue tests exercise every reference recipe in both calculation modes. They
validate the calculation contract, not real-model extraction or ground-truth
meal nutrition. SQLite tests do not prove concurrent PostgreSQL locking; the
recorded PostgreSQL rehearsal uses a single worker. The rebuilt `71a0ecd` offline
stack passed the durable workflow check and two smoke tests; these are separate
from the final matching follow-up's 664 Python tests. Live provider checks are small samples and do not establish an
overall reliability rate.

The coding assistant executed the recorded checks. Independent team review and
rehearsal remain a team responsibility; see the [AI Use Statement](AI_USE_STATEMENT.md).

## 7. Risks and revised scope

**Food coverage is limited.** The catalogue contains 200 ingredient records and
350 reference recipes, not every common dish, name, brand or preparation. Foods
without a corresponding record must be reported as unsupported, with no nutrition
estimate from a substitute dish. Unlisted synonyms or spelling variants can also
need correction. Users may explicitly select actual supported ingredients and
weights in the structured recipe form; the application must not invent a
decomposition of an unknown dish. Free-text ingredient recovery remains a known
limitation, and a custom recipe cannot be saved as a reusable personal template.

The earlier 31 October English-input check returned a broccoli estimate for gai
lan, and subsequent user testing reported unsupported soy-sauce chicken matched
to steamed carp before soy-sauce chicken was added as its own recipe. The matching
guard resolves identity through a deterministic exact
name/alias lookup grounded in the user's complete food mention, independently of
the model's proposed ID.
[Matching verification](../../docs/evidence/food-matching-verification.md) records
separate checks; the earlier 19/21 result remains historical
evidence. Model extraction and portion/recipe assumptions still require review,
and stricter matching is not a guarantee of complete language understanding.

**Individual accounts are not implemented in the local app.** There is no local
registration/login or per-user record ownership; the visible **Log out** button
has no local authentication function. The optional public deployment does have
an implemented shared-password login and signed-session gateway. It controls
access to the shared demo, rather than providing separate user accounts or
private meal histories.

Basic mode trades precision for speed. Advanced questions improve specificity
without establishing measured accuracy. Provider failures, generic invalid-weight
errors and the lack of automatic retry or crash recovery remain open issues.

The scope is a curated catalogue of mainstream reference dishes, not every regional
variant or unconstrained recipe. The new 100 recipe formulations and 62 ingredient
selections increase coverage; they do not establish nutrition accuracy or universal
language recognition. We will prioritize reliable mapping, correction, failure
handling and clear evidence before expanding further.

## 8. Week 7–13 priorities

| Period | Deliverable and acceptance condition | Responsible members |
| --- | --- | --- |
| Week 7–8 | Rehearse both modes and language switching; review evidence and verify the final remote tag | Yixing; Junlang/Jiacheng for fixes; Zhou Ran for docs |
| Week 8–9 | Maintain a fixed Chinese/English meal evaluation set, including gai lan versus broccoli, ambiguous weights, oil and recipe corrections; report extraction separately from arithmetic | Yixing with Junlang/Jiacheng |
| Week 9–10 | Improve invalid-input/provider errors and design bounded recovery; test duplicate requests and interrupted jobs before enabling retries | Junlang/Jiacheng; Yixing validates |
| Week 10–11 | Deploy a verified release with backup/rollback rehearsal and review access limits before wider sharing | Zhou Ran with Junlang; Yixing validates |
| Week 11–12 | Collect feedback on Basic defaults, Advanced questions and bilingual controls; resolve the highest-impact usability issues | Whole team; Zhou Ran documents |
| Week 13 | Freeze the release, rerun acceptance checks and prepare the final demonstration/report with reproducible evidence | Whole team |

These are proposed priorities, not claims of completed features.

## 9. Artifact index

- [TA demo](../../demo/README.md): setup, user workflow and reproducible checks.
- [Screenshot guide](../../demo/SCREENSHOT_GUIDE.md): Chinese flow and English interface.
- [Root README](../../README.md): quick start and current capabilities.
- [Architecture](../../docs/architecture.md) and [operations](../../docs/operations.md).
- [Expansion verification](../../docs/evidence/chinese-expansion-verification.md): current catalogue checks and runtime evidence.
- [Ingredient verification](../../docs/evidence/ingredient-recipe-verification.md): earlier `7c841b1` arithmetic, persistence and browser checks.
- [Interface verification](../../docs/evidence/ui-language-verification.md): dated language-update tests and browser observations.
- [English recognition verification](../../docs/evidence/qwen-english-verification.md): live food mappings and failures.
- [Demo verification](../../demo/VERIFICATION.md): earlier live outcomes and limitations.
- [Original verification](../../docs/evidence/week07-verification.md) and [lifecycle JSON](../../docs/evidence/week07-worker-lifecycle.json).
- [Data provenance](../../docs/nutrition-data.md), [recipe index](../../docs/recipe-catalogue.md) and [change log](../../docs/change-log.md).
- [AI Use Statement](AI_USE_STATEMENT.md).

The live application is the primary demo; screenshots support the walkthrough.
