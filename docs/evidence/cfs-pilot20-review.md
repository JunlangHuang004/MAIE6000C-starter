# CFS 20-dish pilot — 24 November 2026

## Scope and method

Twenty common, previously unreferenced dishes were selected across categories
before examining source matches. This is a purposive sample, not a random sample
of the remaining catalogue. It cannot establish a database-wide match rate,
nutritional accuracy rate or predictable subscription-usage percentage.

The current [CFS FRL workbook](https://www.cfs.gov.hk/resources/Nutrient%20profiles_FRL.xlsx)
was downloaded again and matched the existing SHA-256
`75c77d304a3d2199a1bac3326e9e0458e798f5519e569f4422556b3104ec475d`.
English and simplified-Chinese cells were compared. Names, major ingredients,
preparation and food-versus-whole-meal identity were reviewed. An independent
agent reviewed ten candidates and then checked all six accepted additions.

Six dishes receive attributed prepared-food vectors in catalogue `2026-11-24.2`.
Fourteen have no sufficiently matching prepared-food vector in the reviewed
workbook and retain their existing ingredient formulas. This does not mean they
are absent from every CFS publication or from other nutrition databases. The
catalogue now has 16 CFS references and 368 illustrative-only recipes; all 202
USDA ingredients, original recipe quantities and earlier ten CFS records remain
unchanged.

## Findings

Energy is per 100 g edible prepared food. The previous column is a calculation
from the app's illustrative formula, not a measurement. The official column is
a CFS sample reference, not the actual user's meal. Protein, fat and available
carbohydrate are updated together; exact cells and reasons are retained in the
[machine-readable review](cfs-pilot20-review.json).

| Existing dish | Previous kcal | CFS kcal | Decision |
| --- | ---: | ---: | --- |
| 番茄炒蛋 | 105.1 | — | No matching stir-fry; a tomato-and-egg sandwich includes bread. |
| 宫保鸡丁 | 167.0 | — | No same-name prepared-food vector found. |
| 红烧肉 | 504.5 | — | No same-name vector; roast pork and pork-over-rice are different foods. |
| 鱼香肉丝 | 103.4 | — | No same-name prepared-food vector found. |
| 蒸水蛋 | 58.7 | — | Steamed egg pudding is a sweet dessert, not this savoury dish. |
| 凉拌黄瓜 | 51.2 | — | Plain cucumber excludes the dressing and oil. |
| 清炒西兰花 | 74.1 | — | Plain broccoli and broccoli with fish/mushrooms are different preparations. |
| 酸辣土豆丝 | 114.9 | — | No same-name prepared-food vector found. |
| 蛋炒饭 | 154.5 | — | Other fried-rice records have additional major ingredients. |
| 白粥 | 45.6 | 32 | Added row327, plain congee; thickness varies. |
| 糖醋排骨 | 298.2 | — | Peking-style ribs and pineapple pork are not a verified match. |
| 黑椒牛柳 | 162.2 | — | Reviewed black-pepper beef records include noodles or rice. |
| 白切鸡 | 219.0 | — | Chicken-with-rice cannot represent standalone chicken. |
| 白灼虾 | 92.1 | — | No standalone poached/boiled shrimp vector found. |
| 鱼香茄子 | 111.9 | 120 | Added row341 for the app's vegetarian reference only; excludes meat and salted fish. |
| 干煸四季豆 | 121.8 | — | The closest row adds minced pork and preserved olive. |
| 酸辣汤 | 44.8 | 42 | Added row640; portion includes consumed broth and solids. |
| 豉油鸡 | 234.4 | 250 | Added row224; edible chicken excludes bones and rice. |
| 叉烧肉 | 185.8 | 300 | Added row124; source pork cut/fat differs from the lean illustrative formula. |
| 星洲炒米粉 | 142.3 | 160 | Added row387; noodle moisture and additions vary. |

For four of the six accepted matches, the previous illustrative energy is within
20% of the source value. Plain congee is 42.58% higher and char siu 38.08% lower.
The denominator is the source value. These comparisons do not establish a
20% error bound for real meals. USDA total and CFS available carbohydrate are
different definitions and are not compared as though interchangeable.

## Calculation and validation

Existing calculation rules apply: Basic uses a matched CFS reference, Advanced
offers a source-versus-ingredient choice, and explicit ingredient/oil/yield
details use ingredient arithmetic. Source-specific preparation constraints,
edible weights, separate carbohydrate definitions and historical snapshots are
preserved. No new model calls or database migration are needed for this data
update. No public ECS deployment is included.

Tests check all 16 source vectors, scaling, source snapshots and the two Advanced
calculation choices. The pilot regression also checks the 14 exclusions, the
vegetarian eggplant identity and trace fibre in hot-and-sour soup. The source
workbook and account usage measurements remain outside the published repository.

Final full-suite results: **2,465 backend tests and 108 frontend tests passed**;
Ruff and whitespace checks passed. An initial run exposed seven assertions tied
to the previous catalogue version and soy-chicken calculation basis. Those
expectations were updated to verify the new source ID, exact energy and required
preparation review, then the complete backend suite was rerun successfully.
