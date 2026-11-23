# CFS prepared-food references

Catalogue `2026-11-24.2` adds attributed prepared-food references from the Hong Kong
Centre for Food Safety (CFS) to sixteen existing dish records. The catalogue still
contains 202 USDA ingredient records and 384 recipe identities. No new aliases,
ingredient nutrient values or illustrative recipe quantities are invented to make
the old formulas reproduce the CFS figures.

## Source and scope

The selected numerical facts come from the current
[CFS Food Research Laboratory workbook](https://www.cfs.gov.hk/resources/Nutrient%20profiles_FRL.xlsx).
The [official guide](https://www.cfs.gov.hk/english/nutrient/searchmenu.php) defines
the figures per 100 g edible portion. These are laboratory-based prepared-food
references, with energy calculated from analytical nutrients; they are not
measurements of the user's meal. A same-named dish can have different ingredients,
oil, sauce, moisture and serving size from the sampled food.

| Dish | Record | kcal | Protein g | Fat g | Available carbohydrate g |
| --- | --- | ---: | ---: | ---: | ---: |
| 麻婆豆腐 / Mapo tofu | `dish_004` | 130 | 7.5 | 9.2 | 3.7 |
| 回锅肉 / Twice-cooked pork | `dish_007` | 200 | 8 | 17 | 4 |
| 虾仁炒蛋 / Scrambled egg with shrimp | `dish_012` | 230 | 13 | 18 | 2.6 |
| 蒜泥白肉 / Sliced pork with garlic | `dish_064` | 310 | 15 | 26 | 3 |
| 口水鸡 / Chicken in chilli sauce | `dish_110` | 250 | 18 | 19 | 1.3 |
| 红烧豆腐 / Braised tofu | `dish_202` | 94 | 6.3 | 6.5 | 2.7 |
| 菠萝咕咾肉 / Pineapple sweet-and-sour pork | `dish_266` | 240 | 7.1 | 15 | 18 |
| 椒盐排骨 / Salt-and-pepper pork ribs | `dish_269` | 290 | 20 | 20 | 6.9 |
| 干炒牛河 / Dry-fried rice noodles with beef | `dish_339` | 140 | 4 | 5.1 | 20 |
| 鸡丝凉面 / Cold noodles with shredded chicken | `dish_341` | 190 | 6.9 | 10 | 16 |
| 白粥 / Plain congee | `dish_047` | 32 | 0.71 | 0.69 | 5.8 |
| 素鱼香茄子 / Vegetarian braised eggplant | `dish_154` | 120 | 1.8 | 10 | 3.8 |
| 酸辣汤 / Hot and sour soup | `dish_222` | 42 | 2.2 | 1.8 | 4.2 |
| 豉油鸡 / Soy-sauce chicken | `dish_251` | 250 | 20 | 18 | 1.7 |
| 叉烧 / Barbecued pork | `dish_267` | 300 | 25 | 17 | 9.4 |
| 星洲炒米粉 / Singapore-style fried rice vermicelli | `dish_340` | 160 | 6.3 | 8.4 | 15 |

All values in this table are per 100 g edible prepared food. The
[source map](evidence/cfs-prepared-food-source-map.json) records the exact workbook
rows, source descriptions, source version, retrieval date and match caveats.
The workbook's last-modified date is 2 October 2026; this is not the collection
date of every food sample.

For the two records covered by the
[2017 savoury-dish study](https://www.cfs.gov.hk/english/programme/programme_rafs/programme_rafs_n_01_23_abstract.html),
ten restaurant samples per dish produced observed energy ranges of 190–280
kcal/100 g for pineapple sweet-and-sour pork and 180–330 for shrimp/egg. These are
observed sample ranges, not confidence intervals or guarantees for an individual
meal. No unverified sample count or date is assigned to other records.

The repository includes this selected factual mapping and attribution, not a
rehosted copy of the full CFS workbook. The
[CFS terms](https://www.cfs.gov.hk/english/notices/notices.html) are recorded;
no open licence is asserted for the CFS source. USDA ingredient data retain their
separate CC0 provenance. Do not describe the combined catalogue as wholly CC0.

## Which calculation is used

- **Basic, ordinary matched dish:** use the full CFS nutrient vector scaled by
  cooked edible portion. Existing labelled reference-portion assumptions can
  still be used where supported; a reliable source does not make an assumed
  portion a measurement.
- **Advanced:** choose the CFS prepared-food reference or the editable ingredient
  recipe. The prepared-food path uses cooked edible grams. The ingredient path
  uses the actual reviewed quantities and finished batch weight.
- **Explicit ingredient, yield or oil details, including zero oil:** calculate
  from ingredients. Do not subtract assumed oil from a CFS average or combine CFS
  calories with the old recipe's macros.
- **Actual-ingredient and similar-reference recipes:** continue calculating from
  the accepted ingredient quantities. A CFS field on the source dish does not
  override user-entered facts or turn an unknown dish into a measured match.
- **Explicit raw or gross bone/shell weights:** ask for a usable cooked edible
  portion before applying prepared-food figures; do not invent a conversion.
- **An explicitly incompatible cooking method:** ask the user to review methods
  compatible with the source record. A steamed or raw preparation must not quietly
  receive the fried-dish reference. Compatibility comes from the source mapping,
  not the separate illustrative recipe's wording.

The displayed basis, source record, version and caveat are saved with each result.
Historical saved nutrition is not recalculated or relabelled when the catalogue
changes. A newly calculated ingredient recipe can legitimately differ from the
CFS reference if its quantities or retained oil differ.

## Carbohydrate definitions

CFS FRL reports **available carbohydrate**. Existing USDA records report **total
carbohydrate by difference**. The source definition travels with each saved food
detail. A meal using one definition can display a corresponding carbohydrate
total. If a meal mixes the definitions, NutriChat shows their separately labelled
subtotals and does not present a combined carbohydrate number. Energy, protein
and fat remain available; the meal can still be reviewed and confirmed.

Fibre reported as `Trace` remains a qualifier in source metadata, not measured
zero. NutriChat does not manufacture a USDA-equivalent total carbohydrate value
by silently adding or dropping fibre. Published source calories are preserved
rather than recomputed from rounded displayed macros.

## Remaining coverage

The other 368 recipe identities have no verified CFS prepared-food reference in
this update and retain their explicitly labelled illustrative ingredient formulas.
The same-name links above do not validate every recipe, every restaurant variant
or a claim of less than 20% actual-meal error. White-cut chicken still uses its
documented cooked-chicken proxy; chicken-with-rice data are not substituted for
standalone chicken. Generic fish-fragrant aubergine is not automatically mapped
to the CFS salted-fish-and-minced-pork casserole. The app's vegetarian reference
uses the explicitly vegetarian CFS row341; versions with meat or salted fish
need actual-ingredient calculation.

See the [initial verification report](evidence/cfs-prepared-reference-verification.md)
for the first ten references and browser workflows, and the
[20-dish pilot review](evidence/cfs-pilot20-review.md) for the six additions.
