# White-cut chicken reference correction

## What was wrong

The `2026-11-23.1` reference for `dish_109` (白切鸡 / white-cut chicken) used
400 g raw boneless chicken with skin, 10 g oil, ginger and scallion, divided by
an assumed 340 g finished batch. This produced **568.7 kcal per 200 g**.
The arithmetic was consistent with that formula, but the formula retained all
raw-meat fat despite discarding the cooking liquid and included unreported
dipping oil. Its cooked yield was a project assumption. Passing calculation
tests did not establish nutritional accuracy.

## Verified source and revised scope

The official [USDA SR Legacy CSV archive](https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip)
contains these **cooked, stewed chicken** records. The values below were checked
against `food.csv` and `food_nutrient.csv`, using nutrient IDs 1008, 1003, 1004
and 1005. They describe the edible portion, not bone-in serving weight.

| FDC ID | Original description | kcal/100 g | Protein g | Fat g | Carbohydrate g |
| --- | --- | ---: | ---: | ---: | ---: |
| 171051 | Chicken, broilers or fryers, meat and skin, cooked, stewed | 219 | 24.68 | 12.56 | 0 |
| 171451 | Chicken, broilers or fryers, meat only, cooked, stewed | 177 | 27.29 | 6.71 | 0 |

These are **not measured white-cut chicken records**. Chicken breed, cut, skin
proportion and cooking method can differ. They provide an explicitly labelled
cooked-state proxy, not a claim that a lower number is necessarily correct.

Catalogue `2026-11-23.2` adds `chicken_skin_stewed` and `chicken_meat_stewed`
without changing the original raw chicken data. The white-cut chicken reference
now contains 400 g cooked boneless chicken with skin and a 400 g reference batch.
Dipping sauce is excluded by default; editable oil, ginger, scallion and salt
amounts start at zero. The method states that the reference is a proxy, uses
cooked weights and excludes sauce. Users should add what they actually ate.
For skinless meat, the actual-ingredient form can use the separate cooked
skinless record; the dish name alone does not prove that the skin was removed.

Consequently the plain 200 g reference is **438 kcal** with skin. An explicit
200 g skinless cooked-meat ingredient recipe is **354 kcal**. Neither figure
includes unreported sauce. An explicitly consumed 5 g of the catalogue soybean
oil adds 44.2 kcal. These are reproducible calculations under stated assumptions,
not an exact measurement of the user's meal.

Saved historical estimates are not silently recalculated. A new estimate uses
the updated catalogue after deployment; the earlier checkpoint and its evidence
retain their original version.
Preparation translations also respect the saved source text. Switching an old
estimate to English must not replace its legacy sauce/formula explanation with
the new proxy explanation. Unknown historical method text is retained rather
than silently described using the latest recipe.

## Other official sources checked

- [Hong Kong CFS Nutrient Information Inquiry System](https://www.cfs.gov.hk/english/nutrient/searchmenu.php)
  contains multiple sources, including its Food Research Laboratory. Source and
  edible-portion definitions must be read per entry. The downloaded
  [FRL nutrient profiles](https://www.cfs.gov.hk/resources/Nutrient%20profiles_FRL.xlsx)
  contained **rice with white-cut chicken**, not a directly usable standalone
  white-cut chicken record. Chicken-and-rice data must not replace chicken data.
- [Taiwan FDA food nutrient open dataset](https://data.gov.tw/dataset/8543)
  provides sample descriptions, per-100-g amounts and discard rates under the
  Government Open Data License, version 1. The 230,152-row CSV checked on
  23 November contained no verified directly corresponding white-cut chicken
  sample. This does not prove no such record exists elsewhere.
- [China CDC / Chinese Nutrition Society food query platform](https://nlc.chinanutri.cn/fq/)
  is a relevant official reference for Chinese foods. Its public query page does
  not establish an open bulk-redistribution licence; no database copy was imported.

No direct official white-cut chicken measurement was verified in this review.
No unrelated dish, skinless preparation or raw ingredient is silently substituted
to obtain a more appealing calorie number.

## Remaining limits

All 384 dishes remain project-maintained reference recipes. The other 383 formulas
have not been validated against measured finished-dish samples in this correction.
Some can overestimate retained fat or misrepresent cooked yield. More food names
and successful parsing tests improve coverage, not nutritional accuracy.

Prioritize records that match the food, cooking state and edible portion, with
traceable sources. Where no appropriate measured record exists, retain the
reference label and state missing details; do not describe generated quantities
or yields as official data. Raw weights, cooked weights, bones, skin and separately
consumed sauces must not be treated as interchangeable.
