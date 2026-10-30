# Independent browser review: expanded Chinese catalogue and refreshed demo

The six-step demo passed on the expanded `nutrichat` runtime: Basic assumptions,
Advanced recipe review, the exact natural-language portion correction,
confirmation and reload all worked on one record. The expanded plain-name dish
sample and structured ingredient recovery also passed. One separate rich-input
case falsely rejected supported cola chicken wings when the text included
`（已去骨）`; it withheld all totals rather than substituting another dish.
The exact failed input passed in the targeted follow-up on `dae0b94`.
The original failure remains recorded rather than being replaced with the pass.

## Runtime and evidence provenance

- Date: 31 October 2026, approximately 02:00–02:06 Asia/Hong_Kong for the first phase.
- Target: `http://localhost:8003/app`, native Safari controlled through CUA.
- Frozen runtime source: `71a0ecd56f2de09460ce899b1b183f723ab45b0e`.
- Reviewer independently matched HEAD and the 31-service-file local digest to the
  [parent's runtime manifest](2026-10-31-expanded-demo/runtime-handoff.json):
  `8ed7db5c4268bbe9b6a534027a1fc7861b4a14b3fc2230453db5d1ccc1ecf0b3`.
  Container hashes, health and provider in that manifest are parent-supplied
  evidence; they were not recomputed by this browser reviewer.
- Provider: Qwen; the handoff specifies Qwen Plus. Real browser submissions were
  used, with no fixtures or mocked responses.
- The UI visibly showed **200 ingredients and 350 reference recipes**. New
  Chinese-first records retain Chinese names/method notes in the English UI;
  the interface displays this limitation.
- Parent subsequently prepared a wrapper fix while keeping this runtime frozen.
  Screenshots 01–11 are genuine captures of the stated `71a0ecd` runtime, not
  evidence that the later code was already running.
- Compare the [prior structured-ingredient review](2026-10-31-ingredient-form.md)
  and earlier linked reports. Their recorded failures remain historical evidence.

The refreshed [TA screenshot guide](../../../demo/SCREENSHOT_GUIDE.md) uses
page-only crops from these observations. Safari zoom and scrolling were used to
frame relevant controls. No page content or numbers were painted, reconstructed
or replaced. Old screenshot files remain historical assets but are no longer
referenced by the current guide.

## First-phase action ledger and outcomes

The cap was eight model-triggering actions. This phase used **five actual
model-facing submissions** (four initial estimates and one natural-language
reply), plus one mode switch counted conservatively: **six of eight** budgeted
actions. There were no automatic retries. Structured answers, one ingredient
calculation, language switches and confirmation/reloads are listed separately.
Provider request counts were not network-traced by the reviewer.

| Case | Exact action / expectation | Observed result | Outcome |
| --- | --- | --- | --- |
| E01 | New Basic meal: `一份番茄炒蛋，两个水煮鸡蛋` | Correct dish 200 g + edible boiled eggs 100 g; explicit reference portions and recipe assumptions. 365.2 kcal, 23.3 g protein, 25.5 g fat, 10 g carbohydrate. Record `80afe1a8-a493-44b7-a096-4234d78547f0`, revision 1. Guide images 01–02. | Pass |
| E02 | Switch same record to Advanced; require facts and recipe review | Totals absent pending clarification. Entered dish 200 g, eggs 100 g, cooked edible bases, reviewed uncertainty boxes and recipe tomato 300 / raw egg 150 / oil 15 / sugar 5 / salt 2 g, finished batch 400 g. [Reviewed form](2026-10-31-expanded-demo/02-advanced-reviewed.txt), guide image 03. | Pass |
| E03 | Submit reviewed Advanced answers | Same foods and 365.2 kcal at revision 3; reference recipe explicitly user-approved. | Pass |
| E04 | Exact correction: `番茄炒蛋实际吃了150克熟重，水煮鸡蛋可食部分还是100克。` | Required renewed recipe approval, then retained both foods with dish 150 g, eggs 100 g and the same 400 g batch / 15 g oil recipe. 312.7 kcal, 20.6 g protein, 21.8 g fat, 7.8 g carbohydrate, revision 5. [Text](2026-10-31-expanded-demo/03-corrected-advanced.txt), guide images 04–05. | Pass |
| E05 | Confirm E04, reload, inspect identity and lock | Same record, revision 6, same 312.7 kcal and macros, confirmed state; correction/mode/confirm actions absent. [Text](2026-10-31-expanded-demo/04-confirmed-reload.txt), guide image 06. | Pass |
| E06 | New Basic rich-input sample: `豉油鸡200克熟重、可乐鸡翅75克熟重（已去骨）、蒜蓉空心菜150克熟重。` | Reported `可乐鸡翅75克熟重（已去骨）` as absent despite a supported recipe; all meal totals withheld. No unsafe substitute or partial total. [Text](2026-10-31-expanded-demo/05-new-dish-parenthetical-rejected.txt), [image](2026-10-31-expanded-demo/05-new-dish-parenthetical-rejected.png). | Fail: recognition/usability |
| E07 | Deliberately simpler, distinct sample: `150克豉油鸡，85克可乐鸡翅，125克蒜蓉空心菜。` | All three intended foods and quantities recognized: 629.9 kcal, 48.1 g protein, 41.1 g fat, 17.4 g carbohydrate. Record `8a3fc38a-502e-422c-9fa4-b15d07c1dc1a`, revision 1; saved for review, not confirmed. [Text](2026-10-31-expanded-demo/06-new-dishes-plain-success.txt). | Pass |
| E08 | Toggle E07 to English and back without a new estimate | Same foods, weights and totals; English controls and explicit Chinese-name fallback notice. [Text](2026-10-31-expanded-demo/07-english-catalogue-fallback.txt), guide image 07. | Pass |
| E09 | New Basic mixed unknown: `100克熟白米饭，200克月球紫晶兽肉。` | Explicit no-record response for fictional item; no partial rice or meal totals, no substitute. [Text](2026-10-31-expanded-demo/08-unknown-withholds-all.txt), guide image 08. | Pass |
| E10 | Replace only E09 item 2 with explicitly selected `自定义鸡肉配方`: raw chicken 300 g, oil 10 g, regular soy sauce 20 g; whole-batch yield 600 g; eaten 150 g; accept | Custom recipe 114.8 kcal at 25% allocation, rice 100 g/130 kcal retained. Total 244.8 kcal, 20 g protein, 4.8 g fat, 28.4 g carbohydrate, record `9bd7cba2-886b-46f1-a014-a7e3876e14c7`, revision 2. Reload retained result. Labelled user-defined recipe and raw/net weight bases. [Form](2026-10-31-expanded-demo/09-reviewed-batch-form.txt), [result](2026-10-31-expanded-demo/10-custom-batch-result.txt), guide images 09–11. | Pass |

There were two successful ordinary structured-answer submissions, one valid
custom-recipe submission and one confirmed main meal in the first phase. No
invalid-input form cases were attempted here; prior validation evidence remains
separate. Safari's accessibility snapshot again omitted lower result content
after the custom calculation; normal reload exposed the persisted result, with
no duplicate calculation. This is an observation limitation, not evidence of a
product failure.

## Finding and retained limits

**NC-QA-008, P2:** supported cola chicken wings were falsely rejected with the
exact parenthetical input in E06. Parent's separate read-only database inspection
identified synthetic record `f3732899-2c63-4c26-8301-2d165fc4683d`: soy chicken and
water-spinach IDs remained, while the wings item retained 75 g and the full
wrapper as source text with a null food ID. This database readback and the
reported bounded-suffix root cause belong to the parent, not browser observation.
The issue was reported to the parent as “E07” during progress; the final table
numbers it E06. The successful plain-name variant does not close the rich-input
failure.

- **NC-QA-006:** the exact original Advanced correction phrase now passes with
  the explicitly reviewed reference batch, followed by confirmation/reload.
  Non-reference oil edits were not exercised in this phase; do not generalize to
  all edited recipes or dialogue variants.
- **NC-QA-001:** soy-sauce chicken is now a supported reference recipe. E07 shows
  the correct chicken dish rather than the old wrong fish. E09 covers a genuinely
  absent synthetic food and no partial totals on the new catalogue.
- **NC-QA-002/003/004:** English gai-lan recognition, zero-gram generic errors
  and general provider reliability were not retested. Keep their prior evidence.
- **NC-QA-007:** free-text multi-ingredient recovery remains a limitation. E10
  verifies its structured alternative; it does not prove free-text recovery fixed.
- No local individual accounts or personal history list. The visible Log out
  control is for the optional shared public gateway, not independent accounts.
- All food weights and recipes are synthetic. Successful arithmetic and named
  samples do not establish measured nutritional accuracy or universal recognition.

## Targeted follow-up

At approximately 02:08–02:09 HKT, the parent supplied a new READY for source
`dae0b946e286736020becf018c49b4e81eb46ec6`. Reviewer independently matched HEAD
and the 31-service-file local digest
`dfd857332551291c3920fed0005a63dac9fdc5255d3ee9f9fdba9f05e80484fb` to the
[final runtime manifest](2026-10-31-expanded-demo/final-runtime-handoff.json).
Container hashes and healthy provider configuration remain parent-supplied
evidence. Read-only Git comparison confirmed that the UI/static and catalogue
files did not change between the two sources; only matching code and its tests
changed. Thus images 01–11 remain accurate UI illustrations with their original
capture provenance; images 12–13 were taken on the final runtime.

The fresh follow-up cap was **two** model submissions. **One** exact regression
retest was made after the fix; no automatic retry was needed. This is a deliberate
post-fix retest of the previously failed case. The other action below is a
confirmation/reload, not a new model estimate.

| Case | Action | Observed result | Outcome |
| --- | --- | --- | --- |
| F01 | Reload E10, confirm, reload again on final build | Same custom record `9bd7cba2-886b-46f1-a014-a7e3876e14c7`, revision 3, 244.8 kcal / 20 g protein / 4.8 g fat / 28.4 g carbohydrate; confirmed and editing controls absent. [Text](2026-10-31-expanded-demo/11-final-build-custom-confirmed.txt), guide image 13. | Pass |
| F02 | New Basic meal with the exact E06 rich input, including `（已去骨）` | Correct soy chicken 200 g, cola wings 75 g and garlic water spinach 150 g. Total 743.8 kcal, 56.9 g protein, 48.5 g fat, 20.4 g carbohydrate; record `ed30cc68-d1bb-4441-8d66-b60c8395c546`, revision 1. Saved for review, not confirmed. [Text](2026-10-31-expanded-demo/12-parenthetical-regression-passed.txt), guide image 12. | Pass |

**NC-QA-008 is closed for this exact reproduced input** on `dae0b94`; preserve
E06 as failed history. Other qualifiers and phrasing are not universally proven.
The earlier confirmed main record was not reopened after the final rebuild: the
UI has no record-ID picker/history list. Its full flow remains directly observed
on `71a0ecd`; F01 supplies final-build confirmation/reload evidence.

Across both phases there were **six model-facing submissions** plus one
conservatively counted mode switch. Source claims, deterministic test counts and
read-only database checks from the parent are separate from browser acceptance.
No further live actions were performed. The browser was released to the parent
with normal zoom restored and the successful final dish sample visible.

The refreshed guide has 13 real page-only screenshots and an updated Mermaid
flow covering supported foods, missing records, structured recovery, review and
confirmation. It is instructional evidence alongside a runnable app; screenshots
alone do not prove all catalogue or provider cases work.
