# Chinese food catalogue and clarification dialogue

Version **2026-11-23.2** contains **202 ingredient records and 384 editable Chinese
recipe reference templates**, 586 records in total. All records have English names,
and all recipes have English methods. No model training is required.
Qwen extracts explicit facts
and catalogue IDs; Python calculates nutrients. Advanced mode asks about missing
facts; basic mode uses visible reference assumptions where supported. Unresolved
questions create `needs_input`, not a failed job or a partial calorie total.

## Data provenance

Ingredient numbers come directly from USDA FoodData Central SR Legacy (April 2018),
using nutrient IDs 1008 (kcal), 1003 (protein g), 1004 (fat g), 1005 (carbohydrate g).
They are per 100 g of the edible portion in the documented raw/cooked/as-sold state.
Each record retains the FDC ID, original English description, source URL and CC0
licence. Missing nutrients abort import; they are never replaced with zero.
Chinese labels and aliases are project-maintained mappings and may be refined.

- Official download: https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip
- Documentation/licence: https://fdc.nal.usda.gov/api-guide/
- Selection manifest: `services/common/data/usda_selection.json`
- Reproduce: `python scripts/import_usda.py /path/to/official-sr-legacy.zip`
- Runtime snapshot: `services/common/data/catalogue.json` (included in Python package)

The 384 recipe templates in `recipes.json` are **project-authored illustrative
formulations**, not measurements, authentic standardized recipes, or imports of
HowToCook/Figshare. Some use simplified ingredients, clearly described by `method`.
Their nutrient numbers are computed from USDA ingredients; every assumed ingredient
amount and finished batch weight must be explicitly reviewed/accepted in advanced
mode. Basic mode uses these reference values as labelled, unconfirmed assumptions.
The user can change every existing ingredient amount or set omitted ingredients
to zero. A custom ingredient recipe provides explicit selection and quantities
when the reference dish does not describe the meal. Recipe weights refer to the whole batch;
the meal weight refers to the cooked edible portion consumed.

Recipe total = sum(ingredient grams × nutrient per 100g / 100).
Eaten portion = recipe total × consumed cooked grams / cooked batch grams.
Water contributes no macros but affects the finished batch weight. No universal
raw-to-cooked conversion or frying multiplier is used. Advanced mode requires
explicit gram weights; basic mode can use labelled reference bowl/portion weights,
which are project assumptions rather than measured conversions. Consumed additional
oil is a separate gram quantity for ingredient meals.
Cooking losses, nutrient retention and drained fat are not modelled; estimates are
not laboratory measurements. Generic ingredients may differ from local brands.

Figshare Chinese dish datasets remain research candidates: their serving/whole-
recipe bases and source ingredient details need further normalization before import.
Open Food Facts has not been mixed into this CC0 ingredient snapshot.

The 31 October expansion added 62 ingredient records and 100 recipes while preserving
the original 138 ingredient records and 250 recipes. The
[ingredient source map](evidence/ingredient-expansion-source-map.json) records the
new USDA selections; the [recipe expansion manifest](evidence/recipe-expansion-manifest.json)
records the new templates. Codex assisted with drafting mappings, illustrative
recipes and validation code. Ingredient nutrients come from the identified USDA
records; generated recipe quantities, yields, names and methods remain project
assumptions requiring user review. Independent team review and rehearsal remain
pending. See the [expansion verification](evidence/chinese-expansion-verification.md)
for checks and unresolved limits rather than treating a larger catalogue as
measured nutrition or validated model recognition.

The [23 November home-recipe expansion](home-recipe-expansion.md) adds 34 recipes
without changing the then-existing 200 ingredient nutrient records or the preceding 350 recipe
formulations. Meishichina supplies observed dish names and cooking-style evidence;
it does not supply these recipes' quantities, cooked yields or nutrient values.
The new formulas are project-authored assumptions calculated with existing USDA
records. The [public evidence](evidence/home-recipe-expansion-2026-11-23/README.md)
separates included, already-covered and deferred entries. This is a first batch,
not complete coverage of the site's menu. Salt-poached duck was withdrawn before
publication because the raw skin-on duck and assumed cooked yield did not support
a useful estimate without a drained-fat model.

## Cooked chicken correction and evidence quality

The [white-cut chicken correction](white-chicken-reference.md) replaces one
raw-meat/yield formula with an explicitly labelled cooked-chicken proxy and adds
two cooked-state USDA ingredients. The other 383 recipe formulas are unchanged.
Authority applies to the cited ingredient record, not to a project-authored dish.
Automated tests verify arithmetic and behavior; they cannot validate a recipe
against laboratory food measurements. Other formulas remain subject to cooking-
loss and yield review.

## Dish coverage policy

Coverage is finite: **202 ingredient records and 384 reference recipes**. The
catalogue does not include every common Chinese dish, regional name, restaurant
recipe or branded ingredient. Soy-sauce chicken (`豉油鸡` / `酱油鸡`) is now
recorded as `dish_251`; it must resolve to its own reviewed reference recipe,
never steamed carp. Synthetic unknown names such as `月球紫晶兽肉` remain
unsupported rather than being mapped to a familiar dish.

Reviewed matching names are stored in `services/common/data/matching_aliases.json`,
separately from nutrient data. All 586 records have English display names and
reviewed English matching names; all 384 recipes have English reference methods.
The previous 162 missing translations are now present. Additional Chinese aliases
share existing IDs instead of creating duplicate recipes. Matching aliases do not
train model weights or change ingredient nutrient values.

Food identity must be grounded in the user's complete food mention and an exact
normalized recorded name or reviewed alias. A model-selected ID being present
in the catalogue is insufficient. Short ingredient substrings inside a dish name
must not authorize a match; for example, the soy sauce inside a soy-sauce-chicken
name does not identify the whole meal as soy sauce. Unknown names, unsupported
foods and unverified matches are retained and reported with no meal totals in
both modes. Users can correct the name or explicitly select supported actual
ingredients and their weights in the ingredient builder. Unlisted synonyms or spelling variants may need
rephrasing; this restriction does not establish perfect extraction accuracy.
An optional [similar-recipe workflow](similar-recipe-references.md) keeps the
original dish unresolved until the user explicitly selects a reference and
reviews an ingredient recipe. It never turns a recommendation into an exact
identity match.

For a replacement ingredient list, explicitly identify whether the quantities
describe the consumed ingredients or a whole batch. A whole-pot list for an
unsupported dish must not silently become personal intake. The structured
[ingredient recipe form](ingredient-recipes.md) is the reference recovery path:
explicitly select ingredient records, review grams and specify
consumed amounts or whole-batch yield plus consumed cooked weight. It saves a
user-defined recipe in the meal without adding a catalogue dish. A reusable
personal recipe library is not provided. Existing supported recipe templates also
scale whole-batch nutrition by consumed cooked weight.
Live language extraction can still fail; see [QA memory](qa/MEMORY.md).

Maintain one home-style reference formulation per dish. Alternative names share
one ID, rather than adding regional editions of the same dish. Distinct preparations
such as steamed versus braised fish can remain separate dishes. This is a curated
coverage list, not a measured ranking of the most popular Chinese dishes. See the
[dish index](recipe-catalogue.md) for all 384 Chinese/English names and reference methods.

Existing ingredient and dish IDs remain stable; historical saved totals and
evidence are not recalculated by a catalogue update. Earlier expansion decisions
are recorded separately in the [change log](change-log.md).

Weights for ribs, fish, shellfish and bone-in chicken dishes refer to edible flesh,
excluding bones, shells and other discarded parts. If the user explicitly supplies
bone-in or shell-on gross weight, extraction records `weight_includes_inedible`.
Basic mode uses a visibly labelled 60% edible-weight convenience assumption to
avoid an extra question. This is a coarse project default, not a USDA conversion,
and can be inaccurate for particular foods, especially shellfish. Advanced mode
asks for actual edible grams. The original gross grams and flag remain in the draft,
so switching modes never treats the rough conversion as a measured net weight.
Dry noodles and wood ear are
explicitly labelled by their dry ingredient weights, while finished recipe yields
include retained water. Fried recipes use an assumed amount of oil retained in the
food, not the entire frying bath. Soup estimates assume the specified share of both
solids and broth is eaten; users who leave broth should edit the reference mixture
and amount. These assumptions are not measured cooking conversion factors.

Some dishes use simplified or substitute seasonings, disclosed in `method` (for
example, hoisin in the illustrative sauce for Jingjiang shredded pork). The recipe
amounts and batch yields are project-authored assumptions, not quantities imported
from an external recipe collection. No claim of a universal or regionally authentic
recipe is made. Missing brand-specific ingredients should be clarified, not silently
treated as nutritionally equivalent.

Basic mode can use distinct labelled `portion_weights_g` for pieces, bowls and
servings where defined. For example, a reference dumpling is 20g, whereas a serving
is 200g. Explicit user grams always take precedence. These weights remain assumptions
on the calculation copy; switching to advanced still asks for actual weights.
An explicit piece, bowl or cup count without a matching unit reference asks for
edible grams; it cannot borrow the generic serving weight. A default serving can
still be used when no more specific unit was supplied.

The boiled-egg record has an explicit 50g-per-piece reference for a **large,
hard-cooked egg with its shell removed**, matching [USDA ARS, *Nutritive Value of
Foods* (2002), Table 9, food 146, page 22](https://www.ars.usda.gov/ARSUserFiles/oc/np/NutritiveValueofFoods/NutritiveValueofFoods.pdf).
This is a labelled reference estimate, not the measured weight of the user's egg.
The source and portion metadata are stored in both the ingredient selection
manifest and runtime catalogue. Nutrient values are unchanged; no piece weights
have been inferred for meat chunks or chicken wings.

Qwen receives a bounded shortlist of catalogue candidates and proposes existing
IDs. Retrieval uses recorded name/alias spans in user input, with up to 60 primary
records and recipe ingredient context up to a total of 120 records. The matching
follow-up validates each identity against its original user food mention and
recorded names/reviewed aliases before calculation; it does not use similarity
or a nearest-food fallback. A recognized alias shares the recorded recipe ID.
Explicit differences in preparation, ingredients or quantities must remain
available for clarification and editing. A shortlist candidate is not permission
to substitute that food for an unsupported complete dish name. Retrieval bounds
prompt size; it does not establish perfect extraction or a measured latency target.

The reviewed names `水煮鱼`, `水煮魚` and `水煮魚片` resolve to the existing
`dish_126` fish-in-broth reference. Its method and ingredients remain unchanged;
the alias does not claim every restaurant fish broth uses that formulation.
Explicit gram amounts remain grounded in their adjacent complete food names,
including compact comma-separated, space-separated and unpunctuated input such
as `米饭100克,番茄炒蛋150克`, `米饭100克 番茄炒蛋150克` and
`米饭100克番茄炒蛋150克`. Unsupported names still prevent totals; the separator
handling does not authorize substring matching or an inferred portion weight.

Explicit changes such as no peanuts or 5g oil for the whole batch must populate
`recipe_ingredients`, not only an uncertainty message. Batch oil is distinct from
the consumed serving's additional `oil_g`. Qualitative wording such as "less oil"
does not establish a gram value: basic mode can retain labelled reference values,
while advanced mode presents the recipe for review.

A small extraction guard rejects the obvious mistake of copying a piece/serving
count into `grams` when that gram value has no explicit mass-unit evidence in user
text. Basic mode then uses the visible reference portion. Assistant suggestions do
not count as user evidence. This catches the observed "10 dumplings = 10 grams"
error; it is not a complete proof that every model-extracted quantity is correct.

## Dialogue contract

- POST `/analyses`: enqueue description. Demo mode retains the original strict parser;
  set `NUTRITION_PROVIDER=qwen` for the Chinese dialogue workflow.
- Worker calls the internal AI service. Food identity must be grounded in a
  supported name/alias as well as a valid catalogue ID; unsupported food returns
  an explicit no-record message rather than a substitute estimate.
- `needs_input` persists `draft`, `questions`, `conversation`; all totals are null.
- POST `/analyses/{id}/reply`: `{revision, answers}` for server-issued slots OR
  `{revision, message}` for natural language. Structured answers are validated and
  evaluated without another model call. Natural language is parsed with prior dialogue.
- A recipe never receives automatic approval from model output. In advanced mode,
  its editable batch must be explicitly accepted through the question form; basic
  mode labels it as an unconfirmed reference assumption.
- `completed` persists per-item calculations, assumptions and source references.
- Corrections clear old totals; advanced-mode natural-language changes require fresh recipe approval.
- Confirmation only accepts `completed` at the current revision and locks the record.
- Dialogue, evidence and accepted recipe are stored in PostgreSQL; reload restores them.
- 30 items per meal, 10,000g max per food/ingredient, bounded dialogue history.

## Validation

Tests cover recipe yield/oil sensitivity, raw/cooked ambiguity, unknown foods,
missing method followed by an oil question, partial-answer persistence, stale revisions,
confirmation locking, invalid/nonnumeric answers, forged nutrient fields, model failure,
source metadata and recipe references. Real-provider checks use synthetic meals only.
No API key or password is included in the data files or conversation prompts.


## Basic and advanced modes

UI defaults to basic; API clients can set `mode` to `basic` or `advanced` on creation
(the API default remains advanced for compatibility). Basic uses labelled default
portion weights, recipe batches and, for explicit cooking that needs oil, 10g of
consumed oil when unspecified. Explicit piece/portion counts multiply the labelled
reference portion. These are estimates, never measured portion conversions.
Unknown catalogue IDs and contradictory raw/cooked or preparation states still
need clarification: basic mode does not invent nutrient data for unknown foods.

Defaulted facts exist only on a calculation copy. The saved draft retains nulls for
facts the user did not supply. `/analyses/{id}/mode` accepts `{revision, mode}` and
requeues the same record, clears old totals and keeps explicit facts. Switching to
advanced reopens missing-detail questions and requires recipe acceptance. Confirmed
records cannot switch mode. Migration `20261017_0005` persists the chosen mode.

## Extending the catalogue

For a new ingredient, select a compatible USDA SR Legacy record and add its source
ID, Chinese label/aliases, state and preparation mapping to
`services/common/data/usda_selection.json`. Re-run the importer against the official
ZIP, review nutrient values and source metadata, and rebuild the service images.
Keep missing nutrients as an import error rather than filling them with zero.

For a dish, add an illustrative template to `services/common/data/recipes.json`
using supported ingredient IDs, whole-batch ingredient grams, finished cooked batch
weight and a clear method description. Re-run the importer to regenerate the runtime
catalogue. Review the assumed formula and exercise both basic and advanced flows;
adding a dish name alone does not establish its nutrition.

The importer validates unique IDs and recipe aliases, supported ingredient-only
references, finite nonnegative ingredient weights, positive finished yields and
valid reference portion weights before writing the runtime snapshot. It rejects
duplicate FDC selections instead of silently dropping them. To check the expanded
catalogue and both calculation modes without model credentials, run
`pytest -q tests/unit/test_expanded_catalogue.py`.

For an opt-in real-provider test through the running API, worker and database, run
`python scripts/check_expanded_dialogue.py --base-url http://localhost:8000 --live`.
It consumes model quota and creates synthetic records. The check covers new dishes,
piece weights, mode switching, recipe changes, dialogue corrections, saving,
reload, confirmation locking and coarse gross-weight estimates.

Reference portion weights and the default extra oil quantity are project
assumptions, not USDA-measured serving sizes. More detailed input can improve an
estimate's relevance but does not guarantee laboratory accuracy. Neither catalogue
updates nor user corrections retrain the cloud model.
