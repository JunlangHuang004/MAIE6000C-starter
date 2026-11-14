# Fresh review and focused workspace — 14 November 2026

The updated `test` workspace passed **1,144 backend tests, 48 frontend tests and
117 targeted real HTTP assertions**. A separate reviewer was started without the
parent conversation or earlier QA memory. It first tested the pulled GitHub build,
reported failures, then verified the fixes and the revised browser workflows.
This supports the tested paths; it does not promise every possible food, device
or failure condition works.

## Build and independence

- Pulled `fork/test` by fast-forward to
  `254bebfc8fea07830d261adf2def54bc4cb217ed` before making these changes.
- Baseline: a clean detached checkout, isolated PostgreSQL and app at
  `http://localhost:8007/app`. Final: the updated local `test` working tree with
  separate PostgreSQL and app at `http://localhost:8008/app`.
- The fresh reviewer read current source, requirements and setup instructions;
  it did not inherit the parent conversation or read prior QA reports/MEMORY.
  Later fix handoffs and retest coordination were explicit. A second source
  reviewer checked the recovery changes.
- The configured live provider was HKUST. Private configuration was referenced
  outside the checkout; reports contain only synthetic account/meal data.
- The original `nutrichat` branch, public deployment and historical course
  submission were not changed. This report accompanies local work, not a claim
  that a GitHub push or hosted CI run has completed.
- The catalogue remains byte-for-byte unchanged: **200 ingredients and 350
  reference recipes**. SHA256:
  `d9230087a5bd493afbc6d76a5c09e9b549df7746817f55e5ac43d1956a4e9db2`.
- The final relevant-source fingerprint matches API, AI and worker containers:
  `dec7190c2ab087c92020c905137430f4e594be85f53001831a0b09961a7cbfe8`.
  It hashes sorted relative paths and bytes for `.py`, `.json`, `.html` and `.js`
  files under `services`, separated by NUL bytes. See the
  [fingerprint record](../evidence/2026-11-14-fresh-review/runtime-fingerprint.json).

## User-facing changes

The old page stacked all account, profile, meal, evidence, history and tracking
controls together. The revised interface has four persistent panels:

1. **Meals:** describe, review and confirm. Personal-profile entry is optional and
   separate. Source details and record metadata expand on demand; catalogue search
   covers all foods but shows 20 results at a time.
2. **Daily diary:** dated meal totals, weight and exercise. Manual calorie overrides
   and full-day intake coverage are optional disclosures. Balance limitations and
   incomplete-intake status remain discoverable.
3. **Trends:** 30-day calorie/weight charts, recorded-day statistics and daily details.
4. **My goals:** optional profile, goal and approximate nutritional reference.

Panel/language switches preserve drafts without submitting them. Keyboard tabs,
visible recovery messages and narrow-screen layouts were checked. Drafts are not
promised to survive a full page reload. See the
[illustrated walkthrough](../../../demo/INTEGRATED_GUIDE.md).

## Executed verification

| Verification | Baseline | Revised application | Evidence |
| --- | --- | --- | --- |
| Backend suite, controlled external boundaries | 1,069 passed | **1,144 passed**, 2 live smoke tests deselected; 2 dependency warnings | [Final log](../evidence/2026-11-14-fresh-review/backend-tests.log) |
| Frontend DOM suite | 36 passed | **48 passed** | [Final log](../evidence/2026-11-14-fresh-review/frontend-tests.log) |
| Independent real HTTP acceptance, PostgreSQL | 143/145 passed; two Chinese wording failures | **117/117 assertions passed**, including the exact failure replays | [Assertion log](../evidence/2026-11-14-fresh-review/final-acceptance.log), [summary](../evidence/2026-11-14-fresh-review/final-http-acceptance.json) |
| Ruff and whitespace checks | Passed | Passed | [Ruff log](../evidence/2026-11-14-fresh-review/ruff.log) |
| Independent source/DOM regressions | Conflict reload and midnight rollover failed | **2/2 passed** | [Probe log](../evidence/2026-11-14-fresh-review/final-source-ui-probes.log) |
| Concurrent writes | Five races passed | Relevant backend regression suite passed | [Source review](../evidence/2026-11-14-fresh-review/source-review.md) |
| Browser | Initial account/meal/language workflows and clutter observed | Four panels, draft preservation, diary/profile saves, history, custom ingredients, charts and both mobile languages checked | [Independent report](../evidence/2026-11-14-fresh-review/independent-final-report.md) |

The baseline and final HTTP runs have different scopes; their assertion counts
are not distinct scenario counts. Seven live extraction attempts were made for
the baseline; five for final HTTP acceptance and one for the final browser recipe
builder. This was a bounded workflow check, not a broad model evaluation.

The final HTTP log retains the original 117 assertion outcomes. A later browser
seed overwrote an intermediate JSON ledger, so the JSON summary was reconstructed
from that log. [Subsequent saved-record readbacks](../evidence/2026-11-14-fresh-review/final-readbacks.json)
are explicitly labelled as after UI modifications, not original intermediate
model responses. The [baseline report](../evidence/2026-11-14-fresh-review/baseline-report.md)
contains the detailed advertised-feature coverage matrix and original failures.

## Problems found and repaired

| Problem | Correction and verification |
| --- | --- |
| A longer Chinese whole-meal correction retained removed foods and treated preparation notes as unknown food | Narrow replacement/detail grammar now handles the tested sentence. `更正：不要番茄炒蛋了，只吃了100克水煮鸡蛋，去壳后的熟重，没有额外用油。` yields the intended egg, **155 kcal**. Unit cases protect additions, multiple foods and unknown-food rejection. |
| `无额外油` blocked an otherwise valid replacement description | The tested no-extra-oil and peeled-weight details no longer become food names; exact live replay passed. |
| Reloading a conflicted profile left the displayed diary balance stale | Reload refreshes dependent saved diary/trend data while preserving unsaved daily edits; independent DOM probe passed. |
| A page left open across Hong Kong midnight retained yesterday's maximum date | Focus/visibility refresh updates date bounds while preserving drafts; simulated rollover probe passed. |
| Oversized/non-finite meal revisions could return server errors | Strict integer revision validation and safe error serialization return **422** without record/job mutation; 55 new negative integration cases and real PostgreSQL replays passed. |
| Opening recent history could hide a load failure and clear the current meal too soon | Loading errors remain visible in Diary, and current meal/reply drafts remain until a successful load. Frontend regression includes translated errors and retry. |
| Invalid manual calories inside a collapsed disclosure silently blocked Save | Invalid inputs reveal their enclosing disclosure, with visible bilingual guidance, before native validation focuses the field. DOM regression and independent source review passed. The last browser replay was blocked by loss of CUA browser control and remains unverified. |

Unknown foods still withhold all nutrient totals; there is no similar-dish
substitution. Actual supported ingredients can repair an unknown dish. The real
batch-plus-rice case returned **244.8 kcal**, consumed-ingredients-plus-rice
**359.5 kcal**, and the browser's rice-only custom recipe **130 kcal**. These are
checks against the project's reference data, not measured nutritional accuracy.

## Current screenshots

All captures use synthetic data and a dedicated Chrome guest window. Phone-sized
captures use Chrome responsive emulation at **390 × 844**, not a physical device.

| View | Screenshot |
| --- | --- |
| Meals, Chinese desktop | [Open](../../../demo/images/2026-11-14/01-meals-desktop-zh.png) |
| Saved daily totals and balance | [Open](../../../demo/images/2026-11-14/02-diary-desktop.png) |
| Populated 30-day charts | [Open](../../../demo/images/2026-11-14/03-trends-desktop.png) |
| Personal reference | [Open](../../../demo/images/2026-11-14/04-profile-desktop.png) |
| Actual-ingredient recipe | [Open](../../../demo/images/2026-11-14/05-custom-recipe.png) |
| Meals, Chinese mobile | [Open](../../../demo/images/2026-11-14/06-meals-mobile-zh.png) |
| Meals, English mobile | [Open](../../../demo/images/2026-11-14/07-meals-mobile-en.png) |

## Practical limits

The last browser replay of collapsed-input validation and the late recent-record
success-message translation was not completed: CUA reported no available windows
and stopped responding to navigation. These final fixes passed the 48-test DOM
suite and source review; earlier main-workflow browser checks and clean captures
remain valid. The browser was not confirmed restored to Meals after that tool
failure. The local app remains available at port 8008.

No all-catalogue/synonym accuracy sweep, public deployment or security audit,
physical mobile/non-Chrome test, full screen-reader audit, queue crash/load test,
eight-hour session-expiry wait, historical database upgrade/downgrade rehearsal,
or broad Qwen/Ollama comparison was performed. The fresh database migrated
successfully; controlled tests cover more edge cases than the live sample.
Password recovery, Google login, account deletion, personal recipe library and
automatic retries remain documented non-features. Limited catalogue coverage,
reference-recipe assumptions and uncertain user portions remain product limits.
