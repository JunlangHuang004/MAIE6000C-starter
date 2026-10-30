# Independent browser acceptance: structured ingredient recipes

The sampled structured recovery flow passed on `7c841b1`: an unsupported item
was explicitly replaced with reviewed ingredients, the other item remained, both
quantity bases calculated correctly, and confirmation survived reload. Both exact
rice inputs that failed earlier now passed. No new product defect was observed
in this bounded run. This does not close the retained free-text recovery,
Advanced correction, gai-lan recognition or invalid-weight issues.

## Scope and runtime

- Date: 31 October 2026, approximately 01:38–01:45 Asia/Hong_Kong.
- Target: `http://localhost:8003/app`, native Safari controlled only through CUA.
- Branch: `nutrichat`; frozen runtime source
  `7c841b15231cc3372bed571efb3b9335751db3f1`.
- Compared with [baseline](2026-10-31-independent-browser.md) on `2245020` and
  [targeted follow-up](2026-10-31-targeted-followup.md) on `a9843de`.
- At start, HEAD matched the intended source and changes were documentation only.
  The reviewer independently recomputed the local 30-service-file digest:
  `d5f20d72d70f1ebc4811f09f8d3c3ac6711a869e31948c59290cc8957f1b0b01`.
  It matched the copied [runtime manifest](2026-10-31-ingredient-form/runtime-handoff.json).
  Matching API/AI/worker container digests and healthy readiness are parent-supplied
  manifest evidence, not separately recomputed by this reviewer.
- Qwen provider is recorded in that manifest; `qwen-plus` was specified in READY,
  not exposed by the UI. These are real browser submissions to the handed-off
  provider runtime, with no fixtures or mocks used by the reviewer.
- The running catalogue was 138 ingredients plus 250 reference recipes. Parent
  announced later local catalogue work while keeping this runtime frozen. This
  report does not assess that later source or a later expanded catalogue.

The [feature contract](../../ingredient-recipes.md) was read before testing.
The reviewer changed only QA documentation/evidence and reviewer-created
synthetic records. Parent's separate HTTP integration used another record and
is not counted here. Parent-reported 545 Python/26 DOM checks are also separate
from these browser observations.

## Execution and results

The fresh model-action cap was **3**, and exactly **3 initial meal estimates**
were submitted. No text replies, mode switches or retries were made. Two valid
structured calculations and one confirmation used the normal application flow;
the feature contract says these do not call Qwen. Two deliberately invalid form
submissions are recorded separately. This is an action ledger, not network tracing.

| Case | Exact action and required behavior | Observed result | Outcome |
| --- | --- | --- | --- |
| S01 | Basic Chinese `100克米饭和200克豉油鸡`; unsupported item must prevent all meal totals | Only 豉油鸡 was reported as having no corresponding record. No substituted dish or partial rice total. Per-item ingredient builder was available. [Text](2026-10-31-ingredient-form/00-mixed-meal-no-totals.txt) | Pass |
| S02 | Build item 2 as `QA chicken ingredients`; explicitly select raw skinless chicken breast 150 g, soybean cooking oil 5 g, regular soy sauce 10 g; require review and preserve unsent state across language switch | Calculate without acceptance showed a specific review-required message. After acceptance, Chinese→English retained the recipe name, all selected records, 150/5/10 g and checked acceptance. [Text](2026-10-31-ingredient-form/01-unsent-language-values.txt) | Pass |
| S03 | Calculate amounts actually consumed, preserving rice | Custom recipe 229.5 kcal plus rice 100 g/130 kcal = **359.5 kcal**, 37.3 g protein, 9.3 g fat, 28.7 g carbohydrate. The 165 g ingredient sum was explicitly not a finished cooked weight. Source/provenance and custom-recipe status were shown. Revision 2. [Image](2026-10-31-ingredient-form/02-consumed-result.png), [text](2026-10-31-ingredient-form/02-consumed-result.txt) | Pass |
| S04 | Edit to batch 300/10/20 g, finished 600 g, eaten 601 g; block invalid allocation | Opening editor reset acceptance and disabled confirmation. Eaten > finished showed a specific validation error immediately, with no processing transition. Previous saved 359.5 kcal/revision 2 remained, with confirmation disabled; no invalid replacement estimate appeared. Changing eaten to 150 reset acceptance again. [Text](2026-10-31-ingredient-form/03-invalid-batch.txt) | Pass, UI scope |
| S05 | Accept batch 300/10/20 g, finished 600 g, eaten 150 g | 25% batch allocation, custom **114.8 kcal**, retained rice **130 kcal**, total **244.8 kcal**, 20 g protein, 4.8 g fat, 28.4 g carbohydrate. Original batch grams and raw/as-sold states remained visible. Revision 3. | Pass |
| S06 | Confirm batch meal and reload; preserve identity/totals and lock editing | Same record `28493775-f12d-42c0-a62e-faad4cd4c894`, revision 4, confirmed and saved, **244.8 kcal** after reload. Ingredient editor, free-text correction and mode-switch action absent. New-meal action remained. [Image](2026-10-31-ingredient-form/04-confirmed-batch-reload.png), [text](2026-10-31-ingredient-form/04-confirmed-batch-reload.txt) | Pass |
| S07 | New Basic meal, Chinese UI: `100克熟白米饭` | White rice 100 g, **130 kcal**, 2.7 g protein, 0.3 g fat, 28.2 g carbohydrate; source #168878, 0 g added oil, extracted-weight provenance. Saved for review as `59e482e6-85e1-44b9-b7c9-0e890018acc8`, revision 1. [Text](2026-10-31-ingredient-form/05-chinese-rice-result.txt) | Pass |
| S08 | New Basic meal, English UI: `200 g cooked white rice, no added oil` | Cooked white rice 200 g, **260 kcal**, 5.4 g protein, 0.6 g fat, 56.3 g carbohydrate; source #168878, 0 g added oil, extracted-weight provenance. Saved for review as `99d16800-d663-41e3-bf19-8b24ad575b86`, revision 1. [Image](2026-10-31-ingredient-form/06-english-rice-result.png), [text](2026-10-31-ingredient-form/06-english-rice-result.txt) | Pass |

Eight requirement checks passed within three model requests. The Chinese and
English standalone rice records were saved for review, **not confirmed** in this
run. Confirmation/reload was tested on the structured mixed meal in S06.

For S04, no network instrumentation was used. The specific inline error, lack of
processing, unchanged saved revision and disabled confirmation support client
validation and no false result; this reviewer does **not** independently assert
that zero API requests were sent. Server rejection, concurrent stale revisions
and confirmed-record API rejection require separate evidence.

The source display distinguished user-entered recipes from measured database
dishes. It explained the raw/cooked/as-sold bases, even-mixture batch assumption,
and lack of automatic cooking-loss or discarded-oil/broth deductions. After a
custom recipe was saved, free-text input was replaced by guidance to use the
structured editor. S03/S05 used source IDs #171077, #171411 and #174277.

Safari accessibility snapshots briefly omitted the lower result after dynamic
updates. Screenshots showed the result, and a normal page reload exposed the
complete saved result in the accessibility tree. No duplicate calculation was
submitted. This was handled as an observation limitation, not inferred to be a
product failure.

## Defect disposition and limits

- **NC-QA-005:** the two exact standalone rice regressions and the sampled mixed
  rice wording passed on `7c841b1`. Close those reproduced variants with this
  report, retaining earlier failed records and inputs as history. This is not a
  guarantee for all rice paraphrases or provider outputs.
- **NC-QA-007:** free-text ingredient recovery remains open, last reproduced on
  `a9843de`. The new explicit ingredient form now provides a tested alternative;
  its success must not be described as a free-text fix.
- **NC-QA-006:** prior Basic correction passed; original Advanced correction with
  edited recipe/oil values was not repeated here and remains open.
- **NC-QA-002/003/004:** gai-lan recognition, generic invalid-weight failures and
  historical reliability concerns were not retested or closed.
- **NC-QA-001:** S01 again protected this sampled mixed meal on this catalogue.
  The parent plans to add a soy-sauce-chicken reference recipe later. Future
  unsupported-food checks must select an actually absent food; this dated result
  must not be rewritten when coverage changes.

No new P1/P2 failure was observed in this bounded feature run. It supports the
tested structured workflow and the two exact rice fixes, not full product
acceptance or measured nutrition accuracy. Multiple unresolved items, duplicate
ingredient handling, new-record/raw-cooked variations, Advanced custom-recipe
clarifications, mobile layout and stale edits were not exercised. Individual
accounts are absent locally and were not tested. No historical records were
repaired by this reviewer.

Three page-only screenshots were retained; browser chrome/unrelated tabs were
cropped. The final Safari tab remains on the useful English rice result. Native
Safari has no `markDeliverable` API in the enabled CUA surface. Runtime was
released to the parent after the final rice result; no further model actions remain
in this budget. Any later expanded build requires a new READY and new budget.
