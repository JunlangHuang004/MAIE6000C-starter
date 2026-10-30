# OpenNutriTracker comparison

Research date: 2026-10-31. Scope: design reference and recommendations only; this
note does not implement features or claim deployment changes. The comparison uses
the current `nutrichat` working tree, especially
[food matching](../../services/common/food_matching.py),
[meal calculation](../../services/common/meal_engine.py), and
[nutrition data documentation](../nutrition-data.md).

After this review, the user requested implementation. The resulting
[ingredient-recipe feature](../ingredient-recipes.md) adds explicit per-item
ingredient selection, consumed/batch portions and quantity provenance to the
existing architecture. The comparison below records the research baseline;
personal recipe libraries and label import remain proposals. This implementation
was written independently and does not copy the reference project's source.

## Reference and evidence

Selected project: [OpenNutriTracker](https://github.com/simonoppowa/OpenNutriTracker),
a Flutter nutrition tracker with food search, custom foods and reusable recipes.
Reviewed commit: [`1ab4940a65b5f4f61184175b29e0e83156ea0708`](https://github.com/simonoppowa/OpenNutriTracker/commit/1ab4940a65b5f4f61184175b29e0e83156ea0708),
dated 2026-10-23. Its [license](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/LICENSE)
is GNU GPL version 3. This review copied no third-party source and did not run the
reference application. Code reuse and dataset reuse would need their respective
license requirements checked separately.

The relevant behavior is supported by these pinned sources:

1. [Text interpreter](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/lib/features/add_meal/data/model_meal_text_interpreter.dart#L19-L50):
   optional AI extracts food queries and stated quantities, units and household
   portion words. Its prompt prohibits invented amounts and nutrition estimates.
   The [architecture document](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/docs/ai-architecture.md)
   describes a schema without nutrient fields, local output validation and a
   deterministic parser fallback.
2. [Search composition](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/lib/features/add_meal/domain/usecase/search_products_usecase.dart#L50-L257):
   custom foods, recipes, history and cached results supplement remote sources;
   the search result distinguishes a provider failure from a genuine empty result.
   Remote search uses Open Food Facts and a Supabase reference-food backend. The
   method named FDC searches that backend, not USDA directly.
3. [Resolution](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/lib/features/add_meal/domain/usecase/resolve_parsed_meals_usecase.dart#L25-L155):
   unmatched items survive for review; ranked candidates can be preselected and
   low scores flagged. The 0.45 threshold is a heuristic, not measured accuracy.
4. [Recipe arithmetic](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/lib/core/domain/usecase/compute_recipe_nutrition_usecase.dart#L15-L98):
   ingredient amounts scale per-100g nutrients; an explicit total-weight override
   can replace the summed ingredient weight.
5. [Recipe model](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/lib/core/domain/entity/recipe_entity.dart#L8-L101):
   stores ingredients, total weight and an optional serving count, then derives
   grams per serving from total weight divided by that count.

## Comparison with the NutriChat research baseline

| Area | NutriChat at review time | Useful lesson from the reference |
| --- | --- | --- |
| Model boundary | Qwen extracts facts; Python validates and calculates from versioned data. | Keep this separation. Better quantity interpretation matters more than asking AI for nutrient numbers. |
| Food identity | Complete user mentions must match recorded names or reviewed aliases; 138 USDA ingredients and 250 project-authored recipe templates provide finite coverage. | Candidate search and personal foods can make recovery easier, but candidates must remain suggestions until confirmed. |
| Unknown food | Unresolved items persist with an explicit no-record message. Any pending question suppresses item results and all meal totals. Users can correct a name or describe supported actual ingredients and weights. | Retain unresolved rows and make the next action specific. Preserve NutriChat's stricter no-substitution and no-partial-total boundary. |
| Quantities | Basic uses labelled assumptions on a calculation copy; Advanced asks for explicit facts. A narrow extraction guard catches counts copied into grams. | Preserve original amount/unit and their evidence separately from conversion and defaults. |
| Recipe portions | Editable whole-batch ingredients and finished yield already exist. Advanced requires acceptance; nutrients scale by consumed cooked grams divided by finished batch grams. | Add reusable personal recipes and serving/fraction entry as extensions to existing arithmetic, not as a replacement for it. |

## Recommended priorities

**P0: Make unknown-food recovery a complete interaction.** Keep the known rows and
unresolved original wording while the user repairs only the missing information.
Offer explicit actions: revise the name, inspect candidates, provide labelled
nutrition, or create a reusable custom recipe. The latter two need new data
models and validation; they are recommendations, not existing capabilities.
Distinguish an unsupported identity from a service failure. Do not silently pick
a similar dish or present the known subset as the whole meal.

**P0: Track quantity provenance per ingredient.** Separate user-stated amount and
unit, their source text, catalogue portion conversion, and a Basic-mode assumption.
Keep explicit ingredient grams intact. A count such as two eggs needs a usable
food-specific portion weight or clarification; a bowl is not intrinsically a gram
measurement. Review should identify which amounts were stated, converted or
assumed. Extend the current narrow count-to-grams guard without claiming it already
proves every extracted quantity correct.

**P1: Extend the existing batch-versus-intake model.** A recipe's ingredient list
describes everything cooked; a meal entry describes the amount eaten. Ask for the
finished batch weight or a defined number of servings, then the consumed grams,
servings or fraction. The present grams-based calculation is already:

`consumed nutrients = sum(ingredient grams * nutrients per 100g / 100) * consumed cooked grams / finished batch grams`

For a batch divided into four equal servings, one serving is one quarter of its
nutrients. A whole-pot ingredient list supplied while resolving an unknown dish
must never silently become the amount eaten. Reusable named custom recipes,
serving-count entry and recipe versions would make this flow easier; preserve
historical calculation snapshots when a saved recipe later changes.

**P1: Improve retrieval after the recovery flow is reliable.** Add reviewed
spelling/language aliases and candidate search that preserves preparation and
raw/cooked distinctions. A user's confirmed custom foods or recipes can rank first.
Keep source record IDs, nutrient basis and portion assumptions visible. More
records alone do not establish a correct match.

## Boundaries to retain

Do not copy every reference behavior. Its resolver preselects candidates, whereas
NutriChat should continue requiring grounded identities. Its recipe conversion
uses an explicit `1 ml ≈ 1 g` simplification; this is not a general density rule.
Its nutrient accumulator treats missing ingredient values as zero when another
ingredient has that nutrient, leaving null only when all are missing. NutriChat's
USDA import instead rejects missing required nutrients and should retain that
behavior. These are design observations, not results of running either app's
nutrition estimates against measured meals.

The main opportunity is clearer recovery, quantity evidence and reusable batch
portions. Image analysis, model training and a change of model provider are not
required for these improvements.


## Follow-up: known dishes with weight and preparation qualifiers

Checked again on 2026-10-31 at the same pinned commit; GitHub's latest-commit API
also returned `1ab4940a65b5f4f61184175b29e0e83156ea0708`. This is a source review,
not a live acceptance test of OpenNutriTracker.

The immediate NutriChat case was a known dish written as
`可乐鸡翅75克熟重（已去骨）`. The model retained this entire phrase as the food
mention. NutriChat's exact-name guard understood `去骨` but not `已去骨`, so the
meal safely withheld totals despite the catalogue containing the dish. The
`dae0b946e286736020becf018c49b4e81eb46ec6` correction recognizes the bounded
`已去骨` / `已去壳` / `已去殼` qualifiers; it does not discard arbitrary text
inside parentheses. This is a parsing/identity-validation issue, not a missing
nutrient record.

OpenNutriTracker uses three relevant mechanisms:

- **Separate the search name from the amount.** Its [model prompt](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/lib/features/add_meal/data/model_meal_text_interpreter.dart#L27-L50)
  requests a food-only query and separately stated quantity, unit and portion.
  The [schema](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/lib/features/add_meal/domain/meal_items_api.dart#L76-L135)
  has no dedicated cooked/raw, deboned, shell-removed or edible-weight fields.
  We therefore cannot infer that it reliably preserves those distinctions for
  this Chinese sentence. Its [local parser](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/lib/features/add_meal/util/meal_text_parser.dart#L365-L428)
  extracts leading/trailing quantities; it has no specific rule here for a
  quantity followed by Chinese cooked-weight/deboning text.
- **Use ranked search and review, rather than exact phrase grounding.** Its
  [resolver](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/lib/features/add_meal/domain/usecase/resolve_parsed_meals_usecase.dart#L104-L155)
  searches database candidates and initially selects the top result. The
  [ranking](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/lib/features/add_meal/util/resolver_relevance.dart#L97-L149)
  considers name tokens and named qualifiers. Low-confidence selections are
  marked, but this is not proof of identity. Its [name validator](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/lib/core/utils/food_name_validator.dart#L7-L16)
  checks that a nonblank name contains a letter; it does not establish a match
  to the original whole food mention. It does not contain NutriChat's specific
  wrapper rejection, but that alone does not establish a correct match.
- **Make correction visible.** The [review screen](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/lib/features/add_meal/presentation/screens/bulk_add_screen.dart#L920-L980)
  displays missing/uncertain matches and supports a
  [candidate picker](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/lib/features/add_meal/presentation/screens/bulk_add_screen.dart#L1430-L1465).
  Amount edits remain separate from selection state. Unresolved rows survive
  review, but [logging excludes unresolved or skipped rows](https://github.com/simonoppowa/OpenNutriTracker/blob/1ab4940a65b5f4f61184175b29e0e83156ea0708/lib/features/add_meal/presentation/bloc/bulk_add_bloc.dart#L323-L330).
  That differs from NutriChat's requirement to withhold the whole meal total
  while any item remains unresolved.

The transferable design is the separation of identity, amount and review. For
NutriChat, keep original wording and explicit preparation/edible-weight facts,
normalize only recognized modifiers, and reject unaccounted food text. A future
per-item exact catalogue selection could recover a known-food parsing failure
without forcing users to rebuild its ingredients. Such a selection should be
explicitly confirmed, preserve the other meal items and show the selected record.
Do not adopt automatic fuzzy substitution or silently exclude an unresolved item.
The current structured ingredient editor remains the recovery path when a dish
really has no corresponding record. These recommendations are inferences from the
reviewed design; they do not claim that OpenNutriTracker passed NutriChat's NC-QA-008.
