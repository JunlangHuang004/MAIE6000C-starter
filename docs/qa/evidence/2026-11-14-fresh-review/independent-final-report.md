# NutriChat independent final QA — 2026-11-14

**The final targeted HTTP acceptance passed 117/117 checks.** The two live Chinese wording failures found in the fresh baseline now complete correctly, malformed revisions return safe validation errors, and the revised interface separates Meals, Daily diary, Trends and My goals while preserving drafts. This is a verified set of workflows, not a claim that every input, recipe or device works.

## Baseline versus revised application

| | Fresh baseline | Revised application |
|---|---|---|
| Source | Detached `254bebfc8fea07830d261adf2def54bc4cb217ed` | Same base plus the current reviewed changes in `nutrichat-test` |
| Runtime | Isolated `nutrichat-freshqa-20261114`, port 8007, own PostgreSQL | Isolated `nutrichat-ui-20261114`, port 8008, own PostgreSQL |
| HTTP acceptance | 143/145 assertions passed; two live Chinese wording failures | **117/117 assertions passed**, including exact failure replays and six malformed revision requests |
| Full backend suite | 1,069 passed; 2 smoke tests deselected | Implementation agent's final run: **1,144 passed**, 2 smoke tests deselected; logs inspected |
| Frontend suite | 36 passed | Implementation agent's final run: **48/48 passed**, including navigation, draft preservation, conflict recovery, date rollover and late validation/error-display regressions |
| Independent UI regression probes | Profile-conflict balance refresh and overnight current-date refresh failed | **Both probes passed** against revised source |

The reviewer read current documentation/source/tests and tested fresh synthetic accounts. Prior QA reports and `docs/qa/MEMORY.md` were not used to determine the baseline verdict. Baseline app source and runtime remained unchanged. No existing deployment, private account or food-data catalogue was replaced.

## Final functional results

The real HTTP run repeated anonymous/security-header/origin rejection, separate-account ownership, profile persistence/calculations/guards, strict input validation and stale revisions; daily weight/calorie/exercise/completeness saves, zeros versus missing data, 30-day gaps and averages; Basic/Advanced mode changes, structured clarification, unknown foods, batch and consumed custom recipes, confirmation/date locks, manual calorie replacement/clearing, logout and history restoration.

Specific corrections verified:

- From `一份番茄炒蛋，两个水煮鸡蛋`, the longer correction `更正：不要番茄炒蛋了，只吃了100克水煮鸡蛋，去壳后的熟重，没有额外用油。` now completes at **155 kcal**, with the removed dish and instruction/detail text excluded from food items.
- Full-description replacement `100克水煮鸡蛋，去壳熟重，无额外油` now completes at **155 kcal** with one egg item, instead of inventing an unknown “no extra oil” food.
- `revision=10**100` and invalid non-finite revision inputs on description replacement, mode and reply now all return **422**, and the saved record is unchanged.
- Unknown food continues to withhold all nutrient totals. User-reviewed ingredients repair it without silently substituting a catalogue dish. The documented batch-plus-rice example remains **244.8 kcal**; consumed-plus-rice remains **359.5 kcal**.

Five final HTTP extraction attempts were made, plus one additional unknown-food extraction to exercise the browser ingredient builder. Structured answers, mode switches and ingredient calculations did not require broad model evaluation. The earlier baseline used seven live extraction attempts.

## Browser verification

Native Chrome was operated through CUA. Clean final screenshots use a dedicated guest window without unrelated tabs.

- All four sections opened correctly in Chinese and English. Unsaved meal text, profile age and diary exercise survived section switches and language switching.
- The meal form is now the main task on the starting screen. Optional personal details live in My goals. Result evidence is collapsed initially, leaving the summary easier to inspect.
- Diary exercise was edited and saved through the UI (300→350). The displayed expenditure/balance updated. Profile weight was then saved (80→90); the diary immediately changed to baseline 2,256, expenditure 2,606 and deficit 506 for intake 2,100/exercise 350. Daily measured weight remained 80.1, separate from profile weight.
- Populated calorie and weight charts rendered with missing-date gaps. Three recorded calorie days produced 751.7 kcal average; three weight measurements displayed 79→80.1 kg. These synthetic values are test data, not a dietary recommendation.
- Selecting an unknown meal in Diary's recent records and pressing Open record switched to Meals and restored its clarification state.
- The browser ingredient builder searched “米饭”, selected cooked white rice, accepted 100 g and calculated a labelled custom recipe at **130 kcal**. Changing grams cleared acceptance as intended. English switching preserved the selected ingredient/search text; the result exposes an Edit ingredient recipe action and disables free-text modification guidance appropriately.
- At **390×844 responsive viewport**, the Chinese and English meal layouts fit the available width and all four navigation labels remain visible. English Daily diary/My goals wrap over two lines. Chinese diary layout also fit. This is Chrome responsive emulation, not a physical-device or mobile Safari test.
- English sample buttons intentionally retain Chinese meal-description text; they are actual example inputs, not an assertion that every English food synonym is supported.

Two late interface issues were reported to the implementation agent: a recent-record success message using an untranslated fallback, and invalid manual calories hidden inside a collapsed disclosure silently blocking Save. Their final verification is recorded in the addendum below. Failed recent-record loading also received a targeted implementation regression; it was not forced through a real network fault during this browser run.

## Evidence and provenance

- `baseline-report.md`: independent baseline findings and complete advertised-feature coverage map, including untested areas.
- `final-acceptance.log`: all 117 final HTTP assertion outcomes.
- `final-http-acceptance.json`: parsed assertion summary; `final-readbacks.json`: subsequent saved-record readbacks after UI changes. These later readbacks are not represented as original intermediate model responses.
- `final-source-ui-probes.log`: independent conflict-recovery and date-rollover probes, 2/2 passed. Rollover was simulated and asynchronous refresh was allowed to complete; no real overnight wait was performed.
- `final-20261114-meals-desktop-zh.png`, `final-20261114-profile-desktop.png`, `final-20261114-diary-desktop.png`, `final-20261114-trends-desktop.png`, `final-20261114-custom-recipe.png`, `final-20261114-meals-mobile-en.png`, `final-20261114-meals-mobile-zh.png`: clean final screenshots.
- Full final tests and code/runtime hashes are maintained in the sibling `outputs/frontend-refresh-2026-11-14/` directory. The implementation agent's final source/runtime fingerprint is `dec7190c2ab087c92020c905137430f4e594be85f53001831a0b09961a7cbfe8`, reported identical for source, API, AI and worker after the last static fixes. The catalogue's reported SHA256 remains `d9230087a5bd493afbc6d76a5c09e9b549df7746817f55e5ac43d1956a4e9db2` and its 200 ingredient/350 recipe contents are unchanged.

Reports contain no model keys, session tokens or account passwords. Local harness scripts use disposable synthetic-account credentials only; they are not intended to be copied into public documentation.

## Limits of the verdict

The broad baseline feature matrix still applies. No all-catalogue accuracy sweep, public deployment/security audit, physical mobile or non-Chrome browser run, screen-reader audit, queue crash recovery/load test, eight-hour session-expiry wait, historical database upgrade/downgrade rehearsal or broad Qwen/Ollama comparison was performed. First-run database migration succeeded. Controlled tests cover more boundary cases than the live model sample; passing them does not establish measured nutrition accuracy. Password recovery, Google login, personal recipe library, account deletion and automatic retries remain documented non-features.

## Final browser addendum

The original collapsed-invalid-field defect was reproduced in native Chrome: entering −1 manual calories, closing its disclosure and saving blocked submission without showing the invalid field. The implementation agent deployed a capturing invalid-event handler that opens the enclosing disclosure and displays a bilingual range error; its final frontend run passed 48/48 tests and the separate source reviewer found no further issue. The recent-record success translation and failed-load error placement fixes are included in that same final runtime. Root runtime verification (not a new independent browser observation) reports final source/API/AI/worker fingerprint `dec7190c2ab087c92020c905137430f4e594be85f53001831a0b09961a7cbfe8`; root's final frontend suite is **48/48 passed**.

**The late fixes' final real-browser replay is unverified.** During the reload for that replay, CUA stopped producing effective input, returned `noWindowsAvailable`, and showed stale accessibility data with a blank Chrome viewport. Attempts to reopen the Meals URL did not visibly succeed. The browser session was released with an explicit handoff explaining this control failure; the requested final Chinese Meals state could not be restored. This does not invalidate the earlier completed browser workflows/screenshots, but they must not be cited as proof of the final collapsed-field behavior. No remaining product defect was established by this failed automation replay.
