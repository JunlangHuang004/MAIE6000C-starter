# NutriChat fresh baseline QA — 2026-11-14

**Verdict: the documented account, calculation, diary, recipe and structured review workflows work in the tested paths, but the baseline is not an unconditional pass.** Ordinary Chinese correction/detail phrases can block an otherwise valid meal; profile-conflict recovery and an overnight tab have stale-display defects; malformed meal revisions can return server errors. The first-screen layout also obscures the main meal task.

## Independence and runtime

- Fresh review of detached GitHub `test` snapshot `254bebfc8fea07830d261adf2def54bc4cb217ed` at `/Users/jadenhuang/Documents/Codex/2026-10-16/d/worktrees/nutrichat-qa-20261114`.
- Read current README, feature/setup/API docs, source and tests. No prior `docs/qa/MEMORY.md`, prior QA report or earlier chat verdict was used.
- Built the actual checkout into isolated Docker project `nutrichat-freshqa-20261114`, with its own PostgreSQL volume and loopback API `http://localhost:8007`. Existing deployments/volumes were not changed. Private model configuration was referenced externally; no credentials were copied into evidence.
- Health/ready passed. The app reports the configured HKUST provider. The live checks used synthetic accounts, meals and measurements only.
- Baseline tracked source was not edited; no Git commit or push was made.

## Executed checks

| Check | Result | Evidence |
|---|---|---|
| Backend unit/integration suite, controlled model boundary, excluding live smoke | **1,069 passed; 2 deselected; 2 dependency deprecation warnings** | `baseline-backend-tests.log` |
| Frontend jsdom suite | **36 passed** | `baseline-frontend-tests.log` |
| Ruff | **Passed** | `baseline-ruff.log` |
| Fresh HTTP acceptance, real app/PostgreSQL, seven live model extraction attempts | **143/145 assertions passed**; two Chinese wording failures below | `http-acceptance.json`, `acceptance*.log` |
| Independent simultaneous-write source probe | **Five races passed**: first/update profile, first/update diary, meal confirmation; one 200 and one 409 each | `source-review.md`, `source-concurrency-probe.py` |
| Malformed revision HTTP probes on PostgreSQL | **Five 500 responses reproduced**, record unchanged | `postgres-invalid-revisions.json` |
| Native Chrome browser | Registration, login, language switching, Chinese Basic entry/result, disclosure/layout inspection | original local `baseline-top.png`, `baseline-result.png` (not packaged; current captures are in the main report) |

The 145 HTTP assertions include status checks and behavior checks; they are not 145 distinct user scenarios. Test-runner schema assumptions were corrected during the run (catalogue nesting, per-item nutrient nesting, integer job IDs, draft list, and diary field names). Interrupted harness attempts and their logs are retained. Those harness errors are not classified as product failures. The consolidated JSON contains the final accumulated assertions and saved responses.

## Functional coverage

| Advertised functionality | Fresh result and depth |
|---|---|
| Registration/login/logout, case-insensitive identity | Browser registration and automatic login passed. HTTP bad-password and duplicate-username behavior passed; logout rejected the old client, and login restored private data. Expiry, cookie protections and password hashing were covered by passing controlled integration tests, not an eight-hour live wait. |
| Account isolation | Real HTTP anonymous reads returned 401; second account could not read/edit/confirm/switch mode/build ingredients for the first account's meals, or read its job. Foreign records returned 404; history/profile/diary aggregates were empty for the second account. Missing security header and foreign Origin returned 403. |
| Optional profile, persistence, formulas | Empty profile supported; saved values persisted and remained private. Synthetic male 30/180 cm/80 kg/moderate gave 1,780 resting, 2,759 maintenance; gain reference 2,900 kcal /181.3 g protein/96.7 g fat/326.3 g carbs, loss 2,480/155/82.7/279. Strict invalid types/ranges and stale revisions rejected. |
| Profile output guards | Real HTTP low-BMI fat-loss case retained inputs and withheld all four targets with `needs_review`. Other boundary cases and coefficients/activity factors are covered by deterministic unit tests. |
| Daily weight, calorie total, exercise, coverage | Real HTTP save/read/update/clear passed. All five intake categories required for completeness; explicit zero retained and blank remained unknown. Daily weight did not change profile. Old-client saves preserved omitted exercise/coverage. |
| Daily energy balance | 2,000 intake, 300 exercise and 1,780 resting yielded baseline 2,136, expenditure 2,436, positive deficit 436. Missing prerequisites withheld balance. Source review confirmed no activity-factor double counting. |
| Automatic/manual daily calories | Confirmed 310-kcal meal appeared on its backdated day; manual 1,000 replaced the meal sum; clearing restored 310. Other account saw no contribution. Unconfirmed statuses and ownerless records are also covered by existing tests. |
| Trends, gaps and averages | API returned exactly 30 consecutive Hong Kong dates. Weight-only/missing dates excluded from calorie average; explicit zero included. Two recorded values 2,000 and zero averaged 1,000. Chronological weight change was correct. Final manual 2,100, zero and backdated 310 averaged 803.3. Chart behavior is covered by jsdom tests; a real browser chart with populated data was not exercised in baseline. |
| Chinese Basic meal | Browser and HTTP `一份番茄炒蛋，两个水煮鸡蛋` completed at 365.2 kcal, with 200 g reference stir-fry and 100 g egg, visible portions/assumptions and USDA source links. No claim of measured accuracy is made. |
| Advanced questions and reference recipe review | Switching the same Basic meal to Advanced withheld totals and issued grams, cooked-state, resolution and recipe questions. Submitting only issued structured answers and reviewing the reference recipe completed at 365.2. A separate Advanced egg completed at 155 after grams/state answers. |
| Corrections and mode changes | Basic↔Advanced retained the meal and worked. Simple explicit `改成200克水煮鸡蛋` completed at 310. Ordinary longer correction failed (F1). Full-description replacement with a common oil phrase failed (F2). |
| Unknown food behavior | Known 100 g rice plus invented dish produced `needs_input` with all four meal totals null; no substituted dish or partial total. The unknown item's display name combined the whole input, a minor clarity issue. |
| Actual-ingredient custom recipes | Batch chicken300/oil10/soy sauce20, finished600/eaten150, plus existing rice100 gave **244.8 kcal**. Editing to consumed chicken150/oil5/soy sauce10 gave **359.5**. Other item preserved, explicit acceptance required, foreign edit rejected, free-text reply blocked while custom recipe existed, confirmation/readback persisted exact record. Tested through HTTP; builder controls not manually completed in baseline browser. |
| Meal date, confirmation locks, history | Backdated confirmation saved selected date and locked edits/reconfirmation. Future date rejected. History and profile/diary survived logout/login. Browser opened one saved estimate; arbitrary history selection/reload was not manually exercised in baseline. |
| Catalogue | Public API contains exactly **200 ingredients +350 recipes**. No broad live test of every item/name/synonym. |
| Internationalization | Browser Chinese→English translated profile, meal, diary and trends; original Chinese meal text remained unchanged. 36 frontend tests include language/state preservation and translation behavior. No attempt to prove every newer catalogue item has an English name; docs explicitly describe Chinese fallback. |
| Mobile and keyboard accessibility | **Not yet baseline-tested on a narrow viewport or physical mobile device.** The fresh browser uses native Chrome via CUA; final targeted verification is pending. No full screen-reader audit. |

## Reproducible baseline failures

### F1 — Ordinary full-meal correction creates nonexistent extra foods (P1 functionality)

1. Create Basic `一份番茄炒蛋，两个水煮鸡蛋`; receive completed 365.2 kcal.
2. Switch Advanced then Basic without entering new facts.
3. Reply: `更正：不要番茄炒蛋了，只吃了100克水煮鸡蛋，去壳后的熟重，没有额外用油。`
4. The model's correct 100 g cooked peeled egg, boiled, oil 0 remains in the draft, but the grounding stage also retains/adds five unsupported items: the removed tomato-and-egg dish, the removal instruction, “only ate 100 g,” the cooked/peeled-weight detail, and “no extra oil.” Result: `needs_input`, no totals, five inappropriate food-name questions.

Expected: interpret explicit removal/replacement and preparation details as such. Existing strict unknown-food protection should remain intact. The failure is not evidence of unsafe nutrient fabrication: totals are correctly withheld, but the advertised conversation cannot complete. A short explicit `改成200克水煮鸡蛋` worked separately.

Evidence: `http-acceptance.json` → `evidence.corrected`, `evidence.simple_correction`; analysis `1515b34f-6a97-4245-b8be-49b0fcf5c886`.

### F2 — Common “no extra oil” phrase blocks replacement description (P2 functionality)

PATCH the failed meal with `100克水煮鸡蛋，去壳熟重，无额外油`. The saved draft contains the correct egg facts and an extra unknown food named `无额外油`, so replacement still cannot complete. This is a common preparation detail, not an absent catalogue dish.

Evidence: `http-acceptance.json` → `evidence.replacement_recovery`. Source inspection points to bounded text-coverage grammar in `services/common/food_matching.py`; this is distinct from failure to extract the egg.

### F3 — Reloading a conflicted profile leaves stale daily energy calculations (P2)

The independent DOM probe reproduces profile 80→90 kg saved in another tab, conflict then “Load latest profile.” Reference correctly uses resting1,880 while daily baseline remains2,136 instead of2,256; deficit remains136 instead of256. Server computation is correct; dependent UI fails to refresh. See `source-review.md`, S1 and `source-ui-probes.cjs`.

### F4 — Open tab past Hong Kong midnight rejects the new current date (P2)

The independent DOM probe advances mocked server date and sends focus/visibility events. Date input max and local validation remain yesterday, so today's valid daily date is rejected without a request. Refreshing trends/page works around it. This is a mocked-date DOM/source result, not an overnight real-clock browser run. See `source-review.md`, S2.

### F5 — Invalid revisions return 500 instead of safe rejection (P2)

Real PostgreSQL HTTP: `revision=10**100` returns500 for PATCH description and POST mode; `revision=NaN` returns500 for PATCH, mode and reply. Large reply revision returns409. The saved meal was unchanged after all six requests. NaN is invalid JSON-number input; the server still should return a safe client error. See `postgres-invalid-revisions.json` and source review S3/S4.

## Baseline usability

- The first screen at a desktop viewport is occupied by the heading and expanded **optional** profile. The primary meal input is wholly below the fold despite the meal-focused heading. See `baseline-top.png`.
- The app stacks profile, meal, detailed result, conversation, history, diary and trends in one long page without task navigation. Both food evidence disclosures open initially; just the two-item meal's sources/assumptions occupy multiple screenfuls before confirmation and correction. See `baseline-result.png`.
- English switched correctly and remained readable. Model free-form notes retain original wording as documented, although “Please specify the weight” appears inside a Basic estimate that already uses a reference portion; users can read that as a pending requirement.

## Deliberately untested or outside this verdict

No broad model-accuracy corpus, hundreds-of-call evaluation, all-catalogue synonym sweep, nutrition measurement validation, physical mobile/Safari/Firefox test, full accessibility audit, public deployment/security assessment, crash/queue recovery, load test, eight-hour expiry wait, backup/restore or migration downgrade was performed. The fresh database did successfully migrate during startup; historical upgrade compatibility was not independently replayed. The no-key demo and Qwen/Ollama adapters were not separately deployed; controlled tests cover their implemented contracts. Password reset, Google login, account deletion, recipe library and automatic retry are documented as unimplemented and are not silently counted as passing features.

Follow-up fixes and the final interface must be verified separately; this report describes the unmodified pulled snapshot only.
