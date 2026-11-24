# Optional similar-recipe references

An unknown dish remains unknown. NutriChat can now help the user find an existing
recipe to use as an **explicit approximate reference**, after the user reviews
the main ingredients and cooking method. An optional AI step suggests these facts
from the unknown name; they remain guesses until reviewed. This does not add a new measured dish
to the catalogue or relax exact-name recognition.

## User workflow

1. Enter a meal. If a dish has no matching record, the usual message and missing
   totals remain visible. Correcting the name or entering actual ingredients
   remain available.
2. Expand **Find a similar recipe** for that unresolved item. Either select its
   main ingredients and cooking method manually, or ask AI to suggest them from
   the stored unknown dish name. The interface labels inferred values and lets
   the user correct them. If the name is ambiguous, supply the missing details.
   Exact ingredient amounts are not required at this search stage.
3. After checking all selected main ingredients and the method, request suggestions.
   A candidate must have exactly the same main ingredients and a compatible
   cooking method. Missing or additional main ingredients disqualify it; no
   alternative is offered if none qualifies. Seasonings can still differ.
   Inference alone never triggers this search. Review up to three existing recipes, their preparation,
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

The server builds a bounded shortlist using equality of the declared and recipe
main-ingredient sets, plus compatible cooking methods. Only positive ingredient
amounts belong to a recipe's set. Classified seasonings such as oil, salt, ginger
and garlic are excluded from this equality test; common seasonings alone cannot
establish a match. Raw/cooked and different species IDs are not interchangeable.
For example, shrimp soup cannot stand in for shrimp noodles, and a chicken and
cucumber dish cannot gain noodles merely to obtain a candidate. Cloud providers
(Qwen or HKUST) and the configured local Ollama provider can rank that shortlist.
User-visible reasons and seasoning differences are derived from the actual
catalogue and reviewed ingredients, rather than free-form model claims about
recipe contents. Offline demo mode uses explicitly labelled deterministic rules.
The model never supplies nutrient values or recipe
weights on this path.

The optional inference request sends only the stored unknown name and a bounded
list of supported ingredient names/IDs/states and cooking-method choices to the
configured model. Personal profile information, meal weights and nutrient numbers
are not included. Suggested ingredient IDs and method must pass schema and
catalogue checks. A successful suggestion contains a non-seasoning main ingredient
and a concrete method; an ambiguous result contains no proposed facts and asks
for manual clarification. Offline demo mode requests clarification without
pretending that a model inferred the name.

Both the AI service and public API also check the suggestion against the stored
dish name. Ingredient phrases are matched longest first, so peanut oil does not
establish peanuts and a specific tofu type takes precedence over generic tofu.
The check rejects extra or omitted main ingredients, incompatible ingredient
types, unexplained name text and cooking methods not explicitly supported by the
name. It does not repair a mismatch by substituting another ingredient ID.
For example, beef cubes cannot become ground beef, king oyster mushrooms cannot
become enoki, and home-style tofu cannot silently gain pork. Garlic or spicy
flavour descriptions alone do not establish roasting or frying. These semantic
uncertainties produce a normal clarification response with empty proposed facts
and a bilingual question; users can select the actual facts in the same panel.
The model returns only status/ingredient IDs/preparation for inference and
candidate IDs for ranking. Bilingual display explanations and questions are
generated by the server. This keeps unused model prose out of the parsing path
(including dish titles such as "Three Cup Chicken", which are not ingredient
amounts). Malformed or unavailable provider responses still produce a controlled
error; incomplete JSON is never repaired or accepted silently.

Cooking-method matching recognizes Chinese and English cooking verbs and ignores
negated verbs. In particular, `烧（非油炸版）` is compatible with braising, not
frying. A recipe explicitly requiring frying before braising is excluded from a
plain-braised reference. Explicit catalogue preparation metadata takes precedence.

Inference is saved separately from exact identity and ingredient recipes. It
does not populate `food_id`, calculate a total, select a reference, or confirm a
meal. Requesting a new inference invalidates older candidate offers and pending
reference templates. The existing candidate request uses the user's reviewed,
editable fields, including corrections to the inferred values.

Every returned ID must belong to the compatible server shortlist. Unknown IDs,
duplicate IDs, malformed responses, unexpected fields and incomplete output are
rejected. A provider failure leaves the original meal unresolved. The server
stores each issued offer against the record revision and catalogue version;
the user can select only a candidate from that offer. All three reference endpoints
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

- `POST /analyses/{id}/reference-inference`: `revision` and `item_index`.
  Uses the stored unknown name and returns an updated `AnalysisRead` with
  `draft[item_index].reference_inference`. The persisted object records provider,
  catalogue version, revision, inferred status, proposed ingredients/method and
  bilingual explanation. Ownership, confirmed-state and revision checks apply.
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

Coverage still depends on the maintained catalogue. Exact main-ingredient set
equality and cooking-method filters are conservative; they may miss a reasonable
reference, especially across raw/cooked ingredient records. The user must be able
to review at least the main ingredients and cooking style; a dish name alone may
be ambiguous, and inferred fields can be wrong. Users must include every actual
main ingredient; the filter can only check the reviewed list it receives.
The name-evidence vocabulary is deliberately conservative, separate from exact
food aliases, and is not a complete natural-language parser. Regional names,
metaphorical dish names, unsupported cuts/species and unfamiliar wording may need
manual clarification even when a person could suggest a plausible recipe.
Generic supported types (for example tofu) still need the user's review of the
specific ingredient record and state. The guard does not verify what was eaten.
Identical main ingredients do not establish nutritional equivalence: quantities,
cooked yield and retained oil may differ substantially from the actual dish.

This feature does not provide allergy checks, laboratory accuracy, automatic
portion recognition, automatic unknown-food substitution or a personal recipe
library. When the reference is unsuitable, cancel and use the actual ingredients
or leave the item unresolved.

See the [name-assisted acceptance report](evidence/name-reference-inference-verification.md)
for the initial automated checks and observed live-model workflow, and the
[same-main-ingredient audit](evidence/strict-reference-verification.md) for the
subsequent stricter filtering, independent retests and external nutrition findings.
