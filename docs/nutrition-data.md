# Chinese food catalogue and clarification dialogue

Version 2026-10-16.1 contains 116 ingredient records and 50 editable Chinese recipe
reference templates. No model training is required. Qwen extracts explicit facts
and catalogue IDs; Python calculates nutrients. Missing facts create `needs_input`,
not a failed job or a partial calorie total.

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

The 50 recipe templates in `recipes.json` are **project-authored illustrative
formulations**, not measurements, authentic standardized recipes, or imports of
HowToCook/Figshare. Some use simplified ingredients, clearly described by `method`.
Their nutrient numbers are computed from USDA ingredients; every assumed ingredient
amount and finished batch weight must be explicitly reviewed/accepted by the user.
The user can change every amount, set omitted ingredients to zero, or describe
additional ingredients in conversation. Recipe weights refer to the whole batch;
the meal weight refers to the cooked edible portion consumed.

Recipe total = sum(ingredient grams × nutrient per 100g / 100).
Eaten portion = recipe total × consumed cooked grams / cooked batch grams.
Water contributes no macros but affects the finished batch weight. No universal
raw-to-cooked conversion, frying multiplier, or automatic bowl-to-gram conversion
is used. Consumed additional oil is a separate gram quantity for ingredient meals.
Cooking losses, nutrient retention and drained fat are not modelled; estimates are
not laboratory measurements. Generic ingredients may differ from local brands.

Figshare Chinese dish datasets remain research candidates: their serving/whole-
recipe bases and source ingredient details need further normalization before import.
Open Food Facts has not been mixed into this CC0 ingredient snapshot.

## Dialogue contract

- POST `/analyses`: enqueue description. Demo mode retains the original strict parser;
  set `NUTRITION_PROVIDER=qwen` for the Chinese dialogue workflow.
- Worker calls internal AI service; extracted IDs are validated against the catalogue.
- `needs_input` persists `draft`, `questions`, `conversation`; all totals are null.
- POST `/analyses/{id}/reply`: `{revision, answers}` for server-issued slots OR
  `{revision, message}` for natural language. Structured answers are validated and
  evaluated without another model call. Natural language is parsed with prior dialogue.
- A recipe never receives automatic approval from model output. Its editable batch
  recipe must be explicitly accepted through the question form.
- `completed` persists per-item calculations, assumptions and source references.
- Corrections clear old totals; natural-language changes require fresh recipe approval.
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
