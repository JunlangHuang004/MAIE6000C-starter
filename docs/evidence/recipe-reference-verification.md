# Similar-recipe and cooked-chicken acceptance — 23 November 2026

## Scope

This follow-up applies to `test`, catalogue `2026-11-23.2`, after the published
`cfa02f0` coverage/parser checkpoint. It does not change the historical
`nutrichat` branch, `w13-final` tag or their evidence. The local Docker preview
used HKUST `gemini-2.5-flash-lite`; these observations are not evidence that a
public deployment has been updated or that every cloud provider was exercised.

## Automated checks

- Full backend run: **2,160 passed**, two HTTP smoke tests skipped because
  `SMOKE_BASE_URL` was unset; nine warnings retained in the local run log.
- Subsequent provider-response hardening: **83 passed**, including additional
  energy/joule wording rejection. This overlaps the full suite.
- Final frontend suite: **82 passed**. Includes stale offers, session changes,
  explicit acknowledgement, language switching, single pending edit action,
  mode controls, ingredient-sum versus cooked-portion labels and historical
  preparation evidence across language changes. The old 568.7 kcal chicken
  fixture keeps its legacy explanation; the current 438 kcal fixture uses the
  cooked proxy explanation. No saved nutrient values are rewritten.
- Independent review: **131 targeted backend tests passed** and no remaining
  concrete high/medium severity findings in the reviewed change. This was a
  separate agent without the parent conversation; it reviewed source/tests,
  not a separate live browser session.
- Ruff, JavaScript syntax and whitespace checks passed. Tests validate software
  behavior and reproducible arithmetic, not nutritional accuracy of a real dish.

## Observed browser workflows

The existing local account was used with synthetic test meals. The primary agent
operated the browser; browser screenshots and account-specific transcripts remain
outside Git. Existing user meals were not rewritten.

| Scenario | Observed result |
| --- | --- |
| New `200g白切鸡` | 438 kcal, 49.4 g protein, 25.1 g fat, 0 g carbohydrate; expanded details state cooked, skin-on, boneless proxy, no default sauce and not measured white-cut chicken. Historical saved estimates remain unchanged. |
| Unknown `酸甜娃娃菜` in a three-item meal | Still unresolved with no whole-meal total before explicit review. Oil alone plus stir-frying returned no suitable reference. |
| Declared napa cabbage plus stir-frying | Three existing candidates with reasons/differences; no automatic selection. One candidate added pork and another added fungus, demonstrating why ingredient differences require review. This is not an allergy/dietary-exclusion checker. |
| Select vinegar-fried cabbage | Continue remained disabled until acknowledgement. Selection opened an unaccepted ingredient draft with the original dish name; it did not calculate nutrition. |
| Accept edited reference | Change reference oil from 15 g to 5 g, review a 340 g finished batch and 200 g consumed portion. The approximate item was 93 kcal; the other items remained 200 g beef-and-potato stew and 300 g rice. Whole-meal result: 649.8 kcal, 26.8 g protein, 9.5 g fat and 114.3 g carbohydrate. |
| Confirm and reload in English | Original unknown name and selected source persisted, with an explicit reference-estimate label. Confirmed state was read-only; the chosen consumed date contained one meal totaling 649.8 kcal. |
| `200g水煮鱼300g米饭` | Correct two-item split and reviewed fish alias: 200 g fish reference plus 300 g rice, 560.8 kcal total under the catalogue recipe assumptions. |
| Daily manual zero | Explicit zero replaced, rather than added to, the 847.4 kcal test-meal sum. Clearing the manual field restored 847.4 kcal. Completeness checks remained separate. |
| Trends with gaps | With three recorded calorie dates (649.8, 847.4, 0), the average was 499.1 kcal; missing dates stayed blank and were not counted. One synthetic weight entry displayed one point and no weight-change value. |

Temporary manual totals, synthetic weight/exercise entries and coverage selections
were cleared after the diary test. The two explicitly confirmed synthetic test
meals remain as reviewable records. No personal profile was created or overwritten
in this browser pass; personal-goal rules and account isolation were covered by
automated tests, not a new exhaustive live-account test.

Three live model requests were made in this follow-up (new chicken estimate,
candidate ranking and compact fish/rice); all completed. The earlier six-call
checkpoint sample included one initial failed call and is preserved in its
[original acceptance report](home-recipe-expansion-2026-11-23/README.md).
These small samples do not establish a reliability rate.

## Nutrition limits

The [source review](../white-chicken-reference.md) verifies two USDA cooked
chicken records, not a measured standalone white-cut-chicken sample. The other
383 recipe formulas were not nutritionally validated in this correction. Raw and
cooked weight, skin, bones, discarded liquid and actually consumed sauce remain
material sources of error. A model-ranked reference is optional and can still be
unsuitable; the original unknown dish never becomes an exact catalogue match.
