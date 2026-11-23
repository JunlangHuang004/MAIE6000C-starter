# Home-recipe expansion evidence — 23 November 2026

This directory records catalogue `2026-11-23.1`: 200 ingredients, 384 reference
recipes and English names for all 584 records. There are 34 new formulas; all
preceding ingredient nutrients and 350 recipe formulations remain unchanged.
See [the maintained explanation](../../home-recipe-expansion.md).

## Files and their roles

| File | What it establishes |
| --- | --- |
| [Observed menu labels](observed-menu-names.json) | 364 actual dish labels and the 13 excluded navigation labels |
| [Final gap classification](index-gap-classification.json) | 93 existing-covered labels, 35 labels for 34 new formulas, 235 pending labels and one fat-retention deferral |
| [Initial recipe evidence](meishichina-gap-evidence.json) | Observed source recipe titles/URLs, project English translations, ingredient limitations and final dispositions |
| [Supplemental recipe evidence](supplemental-recipe-evidence.json) | Additional observed source links and dispositions |
| [Last candidate evidence](last-three-candidate-evidence.json) | Potato/pepper, radish-soup and winter-melon-soup source boundaries |
| [Simple-recipe source notes](additional-simple-recipe-evidence.json) | Explicit differences between selected website examples and project formulas |
| [Nutrition source review](nutrition-source-review.json) | Why third-party finished-dish values were not adopted and how ingredient calculation is sourced |
| [Data validation summary](data-validation-summary.json) | Final data checks; `previous_validation` is an explicitly earlier pre-deferral run |
| [Checkpoint validation](checkpoint-validation.json) | Current automated totals and sampled runtime acceptance scope |
| [Runtime acceptance](runtime-acceptance-summary.json) | Public food-only browser outcomes, including the initial model failure and saved oil-edit check |
| [Implementation manifest](implementation-manifest.json) | New IDs, preserved-data hashes, reviewed aliases and calculation limits |
| [New formulas](new-recipes.json) | The 34 project-authored reference formulas, amounts, cooked yields and discovery URLs |
| [New English labels](new-recipe-english.json) | English names and methods for those formulas |
| [Calculated reference values](computed-reference-nutrition.json) | Approximate per-100-g cooked-edible results and their ingredient source data |

Recipe pages provide dish-name and style evidence only. Quantities, retained oil,
sugar and cooked yields are project assumptions; nutrient values are calculated
from the unchanged USDA CC0 ingredient records. These are not Meishichina-provided
or measured finished-dish values. A recipe example may differ from the chosen
project formula, and those differences must remain visible.

The unpublished salt-poached-duck trial (`dish_373`) is absent from active formulas
and calculated values. Its raw skin-on duck and assumed yield did not account for
fat discarded with poaching liquid. Further cooked-food or retention evidence is
needed before providing a useful reference. Later IDs are not renumbered.

The evidence contains public food/source facts, project reference data and
food-only test inputs/results. Private accounts, personal conversations,
credentials, runtime logs and rejected numerical trials are not included.
Historical evidence directories are unchanged.

## Validation status

Current checks pass 2,031 backend tests, 62 frontend tests and Ruff. Two HTTP smoke
tests were skipped because `SMOKE_BASE_URL` was unset. All-record normalized
English retrieval/grounding checks are included in the backend total. The earlier
236 compact-parser checks are a subset. Sampled browser acceptance of the rebuilt
local HKUST runtime covers compact Chinese quantities, a new English dish,
unknown-food withholding and a persisted Advanced recipe oil edit. Six model
calls include one initial failure, retained in the runtime summary. The later
confirmed-meal banner correction has frontend test coverage; no later browser
retest of that text change is claimed here. No historical screenshot is claimed
as validation of these changes; reproducible arithmetic is not a laboratory-
accuracy claim.
