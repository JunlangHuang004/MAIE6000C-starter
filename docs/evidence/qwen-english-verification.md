# English meal recognition verification — 31 October 2026

**Result: 19 of 21 sampled scenarios passed.** Among the 11 English names for
Chinese dishes, nine matched the expected catalogue item and workflow state.
One request failed without an estimate; one returned the wrong vegetable dish.
This sample demonstrates useful English recognition, not universal coverage.

## Source and method

- Branch: `nutrichat`; commit `6219a782bb8fd28fd5747ecf2de9d44606889270`.
- Provider/model: Qwen / `qwen-plus`; local API on port 8003, real queued jobs,
  worker and internal AI service. The running source was checked against the branch.
- Recorded UTC interval: 2026-10-30 16:17:18 to 16:20:50, corresponding to
  2026-10-31 00:17:18 to 00:20:50 in Hong Kong.
- Two runs: 13 original scenarios, then eight additional dish-name scenarios.
  There were no retries or confirmations. All inputs were synthetic.
- Checks compared expected food IDs and gram values, appropriate clarification
  states, finite nonnegative totals, per-food sums and catalogue arithmetic.
  Expected clarification with no totals counted as a pass.
- The [compact evidence](../../demo/evidence/qwen-english-check.json) preserves
  all 21 inputs, expected/observed matches, states, totals, questions and failure
  messages. It also records the original report filenames and SHA-256 hashes.
  The source files were summarized without making additional model requests.

## Chinese dishes requested in English

All weights below are cooked edible weights. These are recipe-based estimates,
not measured values for any restaurant or home-cooked dish.

| English input | Expected catalogue item | Observed outcome |
| --- | --- | --- |
| Tomato-and-egg stir-fry, 200 g | `dish_001` — 番茄炒蛋 | Passed; 210.2 kcal |
| Kung Pao chicken, 250 g | `dish_003` — 宫保鸡丁 | Passed; 417.6 kcal |
| Mapo tofu, 180 g, Advanced | `dish_004` — 麻婆豆腐 | Passed; recipe confirmation requested, no totals |
| Egg fried rice, 200 g | `dish_041` — 蛋炒饭 | Passed; 309.0 kcal |
| Chinese red-braised pork belly, 200 g | `dish_005` — 红烧肉 | Passed; 1009.1 kcal for the reference recipe |
| Sweet and sour pork ribs, 200 g, bones removed | `dish_069` — 糖醋排骨 | Passed; 596.5 kcal |
| Sichuan twice-cooked pork, 200 g | `dish_007` — 回锅肉 | **Failed**; failed state, empty draft and no totals |
| Fish-fragrant shredded pork, 200 g | `dish_006` — 鱼香肉丝 | Passed; 206.8 kcal |
| Chinese hot and sour soup, 200 g | `dish_222` — 酸辣汤 | Passed; 89.7 kcal |
| Beef and broccoli stir-fry, 200 g | `dish_088` — 西兰花牛肉 | Passed; 274.5 kcal |
| Garlic stir-fried Chinese broccoli (gai lan), 200 g | `dish_144` — 蒜蓉芥蓝 | **Failed**; mapped to `dish_017` 清炒西兰花 and returned 148.2 kcal |

## Other ten scenarios

Seven individual-ingredient cases passed: raw and roasted chicken breast,
raw and hard-boiled egg, steamed white rice, and raw and boiled broccoli.
The raw/cooked variants mapped to different intended catalogue records.
A mixed rice/egg/broccoli meal passed with 337.5 kcal. Rice without a known gram
weight correctly triggered a weight question in Advanced mode. A known rice
portion plus a fictional unknown food retained both items and requested food
clarification without generating totals.

## Limits and implications

The twice-cooked-pork case produced a generic service-unavailable message. Its
saved application response does not establish the underlying cause, so it is
recorded as a failed request rather than a proven name-matching error.

For gai lan, the model's uncertainty note acknowledged the distinction from
broccoli, but Basic mode still computed the broccoli reference dish. This is a
real extraction/clarification limitation: a plausible numeric estimate is not
proof that the intended food was recognized. Review the mapped food and correct
it before confirming. A catalogue entry existing does not guarantee recognition.

The mixed-meal case did not retain explicit zero added oil in every draft field;
the steamed/boiled reference arithmetic remained correct. Passing these checks
does not establish perfect preservation of every semantic detail.

The later [Chinese/English interface update](ui-language-verification.md) changes
display labels, catalogue names and recipe explanations. It does not change the
Qwen extraction prompt, add model-matching aliases or fix these two failures.
The 417 passing Python tests and 15 passing frontend tests in that report assess
separate deterministic/UI behavior. No claim is made that all 250 recipes were
successfully recognized by the live model in English.
