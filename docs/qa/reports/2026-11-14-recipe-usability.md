# Meal usability review — 14 November 2026 follow-up

This review used ordinary meal descriptions and real browser interactions to find
friction before refining the interface. **Eight exact post-fix recipe replays
reached their expected outcomes**, and a fresh edit/review/confirm journey completed.
Several language/model cases remain unresolved below; this is not an all-food
accuracy claim or an external human-user study.

## Scope and build

- Starting local `test` commit: `0c9f57380164e0c576616bde69457cff7e8f685a`.
- Isolated application: [localhost:8008/app](http://localhost:8008/app), HKUST
  provider, separate PostgreSQL, synthetic accounts and meals only.
- An independent reviewer started without inherited conversation or old QA memory.
  It tested the live API; the implementing reviewer separately operated the real
  browser through the visible controls. Neither activity is labelled as the other.
- `nutrichat` and the public deployment were not changed. The catalogue still has
  200 ingredients and 350 recipes. Nutrient values/food identities are unchanged;
  only an explicit large peeled boiled-egg 50 g/piece reference and its source were
  added to portion metadata. See [data notes](../../nutrition-data.md).
- Runtime/source identity is recorded in the
  [fingerprint](../evidence/2026-11-14-recipe-usability/runtime-fingerprint.json).
  API, AI and worker code matched after rebuilding and the last static UI sync.

## What changed because of the review

1. **The result comes first after submission.** The large disabled text area becomes
   a compact original-description summary. On mobile, secondary controls remain
   compact instead of taking two full-width rows. Four workspace panels are retained.
2. **Assumptions are visible before confirmation.** Food rows show entered grams,
   reference portions/recipes, reviewed recipes or entered ingredients. A reference
   estimate banner explains what remains unverified; full provenance stays expandable.
3. **Correction is an intentional action.** Select Edit this meal to open the editor.
   Closing it or switching language preserves an unsent reply. Unsubmitted changes
   block confirmation of the old result and show a recovery hint. Offline replacements
   must be submitted or restored to the original text. Confirmed records keep their
   history without an empty correction card.
4. **Recipe review is readable before it is editable.** A compact whole-batch preview
   precedes optional quantity controls. Acceptance stays explicit. Editing any
   ingredient or finished weight updates the preview and clears acceptance; language
   changes preserve the draft. Custom-recipe instructions point to the structured
   editor, not a hidden conversation form.
5. **Known explanatory phrases no longer become fake foods.** Bounded cooked-weight,
   net-weight, bone and no-oil clauses were added without dropping unknown additions.
6. **Unsupported count conversions no longer inflate portions.** A piece, bowl or
   cup without an explicit reference asks for edible grams. Three pieces of pork
   cannot become three default 200 g servings. Supported references remain labelled
   assumptions; explicit grams take precedence.
7. **Zero oil applies to the recipe's cooking oils.** Sesame and other known cooking
   oils are zeroed when the extracted oil amount is explicitly zero, while other
   ingredients remain. The catalogue's nutrient values are not altered.

## Independent live recipe checks

The first pass submitted **20 diverse meal inputs once each**: one completed,
16 requested input and three failed. These are states, not pass/fail percentages.
They include correctly unsupported dishes and legitimate Advanced review alongside
false extra-food questions. The complete inputs and assessments are in the
[independent report](../evidence/2026-11-14-recipe-usability/independent-report.txt)
and [case matrix](../evidence/2026-11-14-recipe-usability/case_matrix.json).

After fixes, these exact inputs were replayed against the rebuilt application:

| Original input | Observed final outcome |
| --- | --- |
| `晚饭吃了三块红烧肉。` | Recognized pork dish; only an edible-grams question, no invented 600 g estimate |
| `吃了4个可乐鸡翅，骨头没有吃。` | Recognized wings; only an edible-grams question, no invented 800 g estimate |
| `青椒肉丝150克，称的是炒熟后实际吃下的净重。` | Completed: 150 g, 149.1 kcal; no phantom weighing phrase |
| `清蒸鳕鱼200克，熟鱼肉净重，没有骨头。` | Completed: 200 g, 222.5 kcal; no phantom bone/weight phrases |
| `麻婆豆腐80克，白米饭100克，都已经煮熟了。` | Completed: 212.5 kcal; both foods retained |
| `一小碟拍黄瓜，没有加香油，也没加其他油。` | Completed using a labelled 200 g reference portion: 51.9 kcal; recipe cooking oil and sesame oil both zero |
| `番茄炒蛋200克，是实际吃下的熟食净重。` (Advanced) | Recipe review completed: 210.2 kcal; weight phrase no longer adds a fake food |
| `咖喱鸡150克和白米饭100克，都是煮熟后吃下的重量。` (Advanced) | Recipe review completed: 295.0 kcal; both foods retained |

See [before/after evidence](../evidence/2026-11-14-recipe-usability/post_rebuild_comparison.json).
These numbers verify the project's reference arithmetic, not measured nutrients.

A separate fresh Advanced flow reviewed a 200 g tomato/egg dish with zero oil in
its batch, then naturally corrected it to 150 g. It required renewed recipe review
and an additional explicit zero-oil confirmation. The final **107.9 kcal** estimate
was confirmed and read back successfully. See the
[complete journey](../evidence/2026-11-14-recipe-usability/32_finished_correction_journey.json).
An earlier equivalent flow stopped before its extra confirmation because its test
process discarded its session. That record is preserved as incomplete; it is not
represented as the completed record.

The independent reviewer made **32 model-triggering requests**, with deliberate
phase caps expanded from 24 to 30 and then 32 for specific replays/completion.
There were no automatic retries. Structured review, polling and confirmation did
not consume model requests. The browser reviewer separately made four model-backed
submissions and one diagnostic replay, for **37 model calls across this review**.

## Browser walkthrough and layout checks

The real in-app browser exercised these visible workflows with a synthetic account:

- Register/sign in, enter a mixed meal, inspect result and reference badges, and
  reopen the meal from account history after restarting services.
- Basic Kung Pao chicken 200 g plus cooked rice 150 g produced 529.1 kcal. Switching
  to Advanced exposed its batch review; changing oil from 15 g to 5 g per 400 g
  batch cleared acceptance. After explicit acceptance, the result was 484.9 kcal.
- A Mapo tofu input initially failed at the model-response boundary. A deliberate
  user-style clarification succeeded. In the browser, oil was changed from 15 g to
  5 g per 620 g batch. Language switching preserved the value and unchecked review
  state. The 200 g result was 177.8 kcal, confirmed and observed in the daily total.
- Correction drafts survived closing/reopening the editor and language changes.
  The final unsent-change confirmation guard was checked separately before saving.
- A negative manual calorie value inside a closed disclosure caused it to reopen,
  focus the invalid field, and show the allowed-range message. No invalid daily
  record was saved. This closes the browser-check gap noted in the prior review.
- The Chinese result was inspected at **390 × 844**. Four tabs, wrapping actions,
  two-column metrics and reference labels fit. The viewport override was reset.
  This is browser emulation, not a physical-device or full accessibility study.

Current screenshots are in the [illustrated guide](../../../demo/INTEGRATED_GUIDE.md):
[Basic result](../../../demo/images/2026-11-14-recipe-usability/01-basic-result.png),
[recipe review](../../../demo/images/2026-11-14-recipe-usability/02-recipe-review.png),
[edited recipe](../../../demo/images/2026-11-14-recipe-usability/03-edited-recipe.png),
[confirmed meal](../../../demo/images/2026-11-14-recipe-usability/04-confirmed-meal.png),
[mobile](../../../demo/images/2026-11-14-recipe-usability/05-mobile-result.png).

## Automated verification

- **1,208 backend tests passed**, two live smoke tests deselected; two dependency
  deprecation warnings. [Log](../evidence/2026-11-14-recipe-usability/backend-tests.log).
  An earlier run exposed an old test that expected an unrecorded bowl conversion;
  its provenance case now uses a serving, and a new regression asserts that bowls
  without explicit conversions withhold totals and ask for grams.
- **56 frontend tests passed**. Coverage includes stage visibility, draft
  preservation, reference labels, explicit recipe acceptance, custom-recipe guidance
  and confirmation guards. [Log](../evidence/2026-11-14-recipe-usability/frontend-tests.log).
- Ruff and whitespace checks passed. [Ruff log](../evidence/2026-11-14-recipe-usability/ruff.log).

## Remaining limitations and unresolved observations

The initial shrimp-count, selective rib-soup and no-meat eggplant attempts failed.
Relevant logs show successful upstream HTTP 200 responses followed by internal
response-validation errors; the exact malformed fields were not recorded, so they
are not attributed to a confirmed network outage. These three original inputs were
not independently replayed. The browser's noodle/vegetable input also failed; an
unsupported noodle name alone does not explain the model-response failure.

A direct diagnostic replay of the initial Mapo input succeeded, illustrating that
one retry can succeed without establishing general reliability. Failures never
produced fabricated totals. [Diagnostic evidence](../evidence/2026-11-14-recipe-usability/mapo-diagnostic-replay.json).

Cantonese phrasing, large-bowl noodles, mixed milk volume and some household wording
remain uneven or unreplayed. Selective broth-only consumption remains unresolved;
a full reference recipe must not stand in for only its broth. Generic no-oil
language still depends on correct model extraction; precise ingredient edits in
Advanced provide the reviewable path. Repeated recipe/zero-oil confirmation can
still be verbose. None of these are counted as fixed merely because unit tests pass.

There was no all-350-recipe accuracy sweep, nutrition measurement validation,
public deployment/load/security audit, or new provider comparison. Account,
profile and tracking regression tests ran, but this follow-up's manual emphasis
was the meal workflow. Historical reports and screenshots retain their original
scope and results.
