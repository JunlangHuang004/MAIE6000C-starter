# Home-recipe catalogue expansion — 23 November 2026

Catalogue `2026-11-23.1` contains **584 records: 200 ingredients and 384 reference
recipes**. This follow-up adds **34 recipes**, reviewed Chinese aliases and English
names for every record. All 384 recipes have English reference methods, including
the 100 older recipes whose English methods were previously absent. The earlier
162 untranslated records now have English names.

The 200 ingredient nutrient records and preceding 350 recipe formulations are
unchanged. Existing food IDs and saved historical estimates remain stable. The
unpublished `dish_373` salt-poached-duck trial was withdrawn; the remaining new IDs
run from `dish_351` to `dish_385` with that gap retained.

This document covers the catalogue, English coverage and compact-input matching
follow-up. The historical `nutrichat` branch and `w07-midterm` / `w13-final` tags
remain unchanged. Publishing a Git checkpoint does not update a running deployment.
Historical submissions, screenshots and verification reports retain their original
scope. No model retraining or account-data migration is required by this expansion.

## What the sources establish

The [Meishichina home-recipe menu](https://home.meishichina.com/recipe-menu.html)
and linked recipes establish observed Chinese dish names and cooking styles.
Direct requests to the menu returned HTTP 403 during research; its public search
index supplied the observed menu labels and original recipe links. No access
controls were bypassed. Only factual names, links and ingredient-style notes are
retained; recipe prose and images are not reproduced. English names are project
translations, not labels supplied by Meishichina.

The source does **not** supply the new records' nutrient values, ingredient amounts
or cooked batch yields. Those are explicitly labelled project-authored reference
assumptions. Nutrient arithmetic uses existing
[USDA FoodData Central](https://fdc.nal.usda.gov/) SR Legacy ingredient records,
whose FDC IDs, edible states, per-100-g values and CC0 provenance remain attached.
The [CFS indirect-analysis guidance](https://www.cfs.gov.hk/english/food_leg/files/nl_technical_guidance_e.pdf)
explains the need for edible ingredient weights, cooking adjustments and prepared
food weight; it does not validate these particular project formulas.

For each nutrient:

```text
batch nutrient = sum(ingredient grams × ingredient nutrient per 100 g / 100)
reference nutrient per 100 g = batch nutrient × 100 / cooked edible batch grams
consumed nutrient = batch nutrient × consumed cooked grams / cooked edible batch grams
```

These are approximate reference estimates, not published or laboratory-measured
finished-dish nutrition. Oil retention, water uptake, sugar retention and cooked
yields can differ substantially between kitchens. Cooking nutrient losses, drained
fat and alcohol retention are not modelled. Advanced mode therefore requires users
to review the reference ingredients and cooked yield explicitly; Basic mode retains
visible assumption labels. The [calculated values and ingredient sources](evidence/home-recipe-expansion-2026-11-23/computed-reference-nutrition.json)
are reproducible from the [34 added formulas](evidence/home-recipe-expansion-2026-11-23/new-recipes.json),
not from a claim that Meishichina measured them.

## Menu comparison and scope

The observed menu contains **364 dish labels**, after excluding 13 navigation
labels such as 首页, 热菜 and 全部菜谱分类. These are labels, not 364 distinct dishes:
synonyms can share an ID. The
[final comparison](evidence/home-recipe-expansion-2026-11-23/index-gap-classification.json)
records:

- 93 labels covered by existing records or reviewed aliases.
- 35 menu labels covered by the 34 added recipes, including the shared
  珍珠丸子 / 珍珠圆子 record.
- 235 labels awaiting further scope, synonym, ingredient or formula review.
- Salt-poached duck (盐水鸭) deferred after reviewing fat retention.

Unreviewed labels are not all new dishes. This is a first batch of supported
reference formulas, not complete coverage of the site or a popularity ranking.
Related preparations such as 炸茄盒 and the existing pan-fried eggplant reference
were reviewed without creating an automatic synonym. Broad menu names also require
care before being mapped to one specific formula.

Several common gaps require essential ingredient data first: century egg for
皮蛋瘦肉粥 / 皮蛋豆腐; pressed tofu and garlic chives for 香干 dishes; dried laver for
紫菜蛋花汤; Chinese yam for 山药排骨汤; garlic scapes for 蒜薹炒肉; preserved mustard
greens for 梅菜扣肉 / 酸菜鱼; and suitable fish-head, chicken-feet, rice-cake and
salted-egg-yolk records for other candidates. Hard tofu is not pressed tofu, a raw
duck egg is not a century egg, and fresh corn is not cornmeal. Those differences
must not be hidden behind aliases or unlabelled nutrient substitutions.

The discarded salt-poached-duck trial combined raw skin-on duck with an assumed
cooked yield, while the application does not account for fat discarded in the
poaching liquid. That produced an unsuitable reference estimate. No nutrient value
from that unpublished trial is available in the active catalogue or this public
value table. It can be reconsidered when suitable cooked-duck composition or
explicit retention evidence is available.

## Matching and English behavior

Names copied from the catalogue are supported in both Chinese and English through
reviewed matching aliases. All 584 records have English display names, and all
384 recipes have English methods. Interface language still does not change stored
nutrients or translate arbitrary user text, and unlisted names remain unsupported.

The reviewed aliases `水煮鱼`, `水煮魚` and `水煮魚片` resolve to existing `dish_126`.
That reference uses boneless tilapia, bean sprouts and chili broth, with its listed
oil and broth counted as eaten. Its formula is unchanged. Users must review that
assumption if their fish, sauce or broth consumption differs; the alias is not a
claim that every version of the dish has those nutrient values.

Explicit weights stay associated with their adjacent complete food mention in
compact comma-separated, space-separated or unpunctuated input, for example
`米饭100克,番茄炒蛋150克`, `米饭100克 番茄炒蛋150克` and
`米饭100克番茄炒蛋150克`. The fallback can recover those explicit grams when model
extraction omits them. It does not invent weights, turn a piece count into grams,
or match an unknown whole dish by a known ingredient substring. Unknown foods
still require correction or explicit actual ingredients, with all meal totals
withheld while unresolved.

## Added reference recipes

The [complete index](recipe-catalogue.md) includes all 384 recipes with Chinese and
English names and methods. The new subset is:

| ID | Chinese name | English name |
| --- | --- | --- |
| dish_351 | 锅包肉 | Guo bao rou (crispy sweet and sour pork) |
| dish_352 | 罗宋汤 | Chinese-style beef and vegetable borscht |
| dish_353 | 麻酱豆角 | Long beans with sesame dressing |
| dish_354 | 锅塌豆腐 | Egg-coated pan-fried tofu in sauce |
| dish_355 | 粉蒸排骨 | Steamed pork ribs coated in rice meal |
| dish_356 | 宫保虾球 | Kung Pao shrimp |
| dish_357 | 宫保豆腐 | Kung Pao tofu |
| dish_358 | 珍珠丸子 | Steamed pork meatballs coated in glutinous rice |
| dish_359 | 千层肉饼 | Layered pork-filled flatbread |
| dish_360 | 卤肉饭 | Braised pork belly over rice |
| dish_361 | 拔丝地瓜 | Caramel-coated sweet potatoes |
| dish_362 | 西湖牛肉羹 | West Lake beef and egg-white soup |
| dish_363 | 盐水花生 | Salt-boiled peanuts |
| dish_364 | 苦瓜炒肉片 | Pork slices stir-fried with bitter melon |
| dish_365 | 木耳炒肉 | Pork stir-fried with wood ear mushrooms |
| dish_366 | 糯米藕 | Lotus root stuffed with sweet glutinous rice |
| dish_367 | 疙瘩汤 | Tomato and egg dough-drop soup |
| dish_368 | 牛奶炖蛋 | Steamed milk and egg custard |
| dish_369 | 荷塘小炒 | Lotus root and mixed vegetable stir-fry |
| dish_370 | 炒饼 | Flatbread strips stir-fried with vegetables |
| dish_371 | 腐乳烧鸡翅 | Chicken wings braised with fermented tofu |
| dish_372 | 盐焗鸡 | Salt-baked chicken |
| dish_374 | 棒棒鸡 | Bang bang chicken with sesame sauce |
| dish_375 | 荷叶饼 | Steamed folded buns |
| dish_376 | 奶香馒头 | Steamed milk buns |
| dish_377 | 糖三角 | Steamed triangular sugar buns |
| dish_378 | 肉龙 | Steamed pork-filled bread roll |
| dish_379 | 鸡蛋灌饼 | Egg-filled flatbread |
| dish_380 | 拔丝苹果 | Caramel-coated apples |
| dish_381 | 糖炒栗子 | Sugar-roasted chestnuts |
| dish_382 | 东北乱炖 | Northeastern pork and vegetable stew |
| dish_383 | 青椒土豆丝 | Shredded potato and green pepper stir-fry |
| dish_384 | 冬瓜汤 | Winter melon soup |
| dish_385 | 萝卜汤 | White radish soup |

## Evidence and validation

The [public evidence directory](evidence/home-recipe-expansion-2026-11-23/README.md)
contains the menu comparison, observed source links, source-quality review,
implementation manifest and reproducible reference values. It contains food data
and public-source facts, not private account records, conversations or credentials.

Current automated checks pass **2,031 backend tests**, **62 frontend tests** and
Ruff. Two HTTP smoke tests are skipped because `SMOKE_BASE_URL` was unset in that
run. The backend total includes normalized English retrieval/grounding checks for
all 584 records; the earlier 236-test compact-parser run is a subset, not an
additional full-suite total. See the [checkpoint summary](evidence/home-recipe-expansion-2026-11-23/checkpoint-validation.json).

Sampled browser acceptance used the rebuilt local runtime with HKUST
`gemini-2.5-flash-lite`. Compact Chinese quantities, the spaced equivalent, a new
English recipe name and mixed known/unknown foods behaved as expected. Advanced
recipe review accepted an explicit cooked-weight retry for 锅包肉; changing its
batch oil from 35 g to 25 g recalculated the result and persisted after reopening.
The structured recipe edit made no additional model request.

The six model calls include one initial failure for `锅包肉150g`: the AI service
returned HTTP 502 after the upstream service returned HTTP 200. The exact rejected
field was not established, so the successful retry does not erase that failure.
The [runtime summary](evidence/home-recipe-expansion-2026-11-23/runtime-acceptance-summary.json)
records the inputs, displayed results and limits without private account records.
After the final API rebuild, browser checks also verified the corrected confirmed-
meal banner in both languages, English preparation and ingredient details for the
new recipe, and one confirmed meal counted once on its selected date.
Earlier dated screenshots and checks remain historical. Successful arithmetic or
matching checks do not establish laboratory accuracy or universal model recognition.
