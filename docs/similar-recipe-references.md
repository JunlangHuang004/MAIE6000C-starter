# Optional similar-recipe references

An unknown dish remains unknown. NutriChat can now help the user find an existing
recipe to use as an **explicit approximate reference**, after the user supplies
the main ingredients and cooking method. This does not add a new measured dish
to the catalogue or relax exact-name recognition.

## User workflow

1. Enter a meal. If a dish has no matching record, the usual message and missing
   totals remain visible. Correcting the name or entering actual ingredients
   remain available.
2. Expand **Find a similar recipe** for that unresolved item. Select its main
   ingredients from the supported ingredient list and choose the cooking method.
   Exact ingredient amounts are not required at this search stage.
3. Request suggestions. Review up to three existing recipes, their preparation,
   the reason for suggesting each one, and differences that need checking.
   A result with no suitable match is valid; no recipe is selected automatically.
4. Select one candidate and explicitly acknowledge that it is an approximate
   reference. This only opens an ingredient draft; it still does not calculate
   the meal or count it in the diary.
5. Review the existing actual-ingredient form. Check every ingredient, its state
   and grams, the finished batch weight and the cooked edible portion consumed.
   Edit the reference as needed and accept the ingredient recipe.
6. Review the calculated result and confirm the meal separately. The original
   unknown name, selected source recipe and **similar-recipe reference** label
   remain visible in the saved result.

The original food description and other items in a mixed meal are retained.
Missing facts for another item still prevent a partial whole-meal total.
Selecting a reference is not confirmation that the two dishes have identical
nutrition. The [data-quality limits](white-chicken-reference.md) also apply to
reference recipes that have a familiar name.

## Responsibilities and boundaries

The server builds a bounded shortlist from the declared ingredients and cooking
method. Common seasonings alone cannot establish similarity. Cloud providers
(Qwen or HKUST) and the configured local Ollama provider can rank that shortlist
and provide short bilingual explanations. Offline demo mode uses explicitly
labelled deterministic rules. The model never supplies nutrient values or recipe
weights on this path.

Every returned ID must belong to the compatible server shortlist. Unknown IDs,
duplicate IDs, malformed responses, unexpected fields and incomplete output are
rejected. A provider failure leaves the original meal unresolved. The server
stores each issued offer against the record revision and catalogue version;
the user can select only a candidate from that offer. Both mutation endpoints
require the signed-in owner and the application's normal CSRF protection.
Confirmed meals and stale revisions cannot be edited.

The selected template is copied from the catalogue into the existing ingredient
editor. Its amounts are reference assumptions until explicitly reviewed. The
Python ingredient calculator produces nutrition from the accepted ingredient
records; it does not ask a model to calculate calories. Reference provenance is
stored with the draft and calculation details. Conversational re-interpretation
is rejected for these custom ingredient meals. The interface also hides the
mode-switch control, following the existing actual-ingredient workflow.

## API contract

- `POST /analyses/{id}/reference-candidates`: `revision`, `item_index`, up to eight
  supported `ingredient_ids`, and `preparation`. Returns an updated `AnalysisRead`.
  Missing facts produce a clarification state. Suggestions are stored in
  `draft[item_index].reference_suggestions` and do not produce meal totals.
- `POST /analyses/{id}/reference-selection`: `revision`, `item_index`, `offer_id`,
  `food_id`, `accepted: true`. Stores reference provenance and an unaccepted
  `reference_template`; it does not calculate nutrition.
- The existing `POST /analyses/{id}/ingredients` endpoint accepts the reviewed
  ingredient amounts and preserves server-controlled reference provenance.
  The existing worker calculation and meal confirmation flow then apply.

No new database table or migration is required; the existing draft and detail
JSON fields retain the offer and provenance. API keys remain on the AI service.

## Limits

Coverage still depends on the maintained catalogue. Exact ingredient IDs and
simple cooking-method filters are conservative; they may miss a reasonable
reference, especially across raw/cooked ingredient records. The user must know
at least the main ingredients and cooking style. A plausible model explanation
is not evidence of nutritional equivalence, and a reference recipe's quantities,
cooked yield and retained oil may differ substantially from the actual dish.

This feature does not provide allergy checks, laboratory accuracy, automatic
portion recognition, automatic unknown-food substitution or a personal recipe
library. When the reference is unsuitable, cancel and use the actual ingredients
or leave the item unresolved.
