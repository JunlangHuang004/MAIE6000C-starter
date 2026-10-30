# Estimate an unsupported dish from actual ingredients

This `nutrichat` feature follows the separation studied in the
[OpenNutriTracker comparison](research/opennutritracker-comparison.md): explicit
food selection, reviewed quantities and database-backed arithmetic. The code was
written for this project's existing API/worker architecture; no third-party
source code was copied.

An unsupported dish remains unsupported as a catalogue identity. The user can
instead supply a **custom ingredient recipe** for that meal item. This does not
add the dish to the catalogue or make the result measured nutrition.

## Use the form

1. Enter a meal normally. If an item has no corresponding record, choose
   **按实际食材估算 / Build from actual ingredients** under that item.
2. Check the item being replaced and give this meal's recipe a name. Other meal
   items remain in the record; another unresolved item still blocks all totals.
3. Choose what the amounts describe:
   - **Ingredient amounts actually consumed:** enter only the ingredient amounts
     belonging to your eaten portion. Their sum is not a finished cooked weight.
   - **Whole-batch ingredients:** enter everything used in the batch, its finished
     cooked weight and the cooked edible weight you ate.
4. Search and explicitly select each ingredient from the catalogue. Check its
   raw, cooked or as-sold weight basis; there is no automatic raw/cooked conversion.
   Enter grams and add oil, sugar and sauces as separate rows. Do not replace a
   missing ingredient with a different food. Combine duplicate ingredients.
5. Check the acceptance box after reviewing the ingredients, states and amounts.
   Click **按这些食材计算 / Calculate from these ingredients**.
6. Review the custom-recipe label, input quantities, portion fraction, nutrient
   totals and source records. Use **Edit ingredient recipe** to make corrections.
   **Confirm and save** locks the meal; reloading retains the saved result.

Language switching keeps the unsent form values. Changing a quantity or selection
requires acceptance again. A stale record produces a conflict instead of
overwriting someone else's revision; the form keeps its unsent values so they can
be noted before refreshing.

## Check the calculation with synthetic numbers

Select the catalogue's raw chicken breast, cooking oil and soy sauce records.

| Basis | Ingredient grams | Finished batch / eaten | Expected calories |
| --- | --- | --- | --- |
| Actually consumed | Chicken 150 g, oil 5 g, soy sauce 10 g | Not applicable | 229.5 kcal |
| Whole batch | Chicken 300 g, oil 10 g, soy sauce 20 g | 600 g / 150 g | 114.8 kcal after rounding |

These examples use the project's ingredient snapshot. If the same meal also has
100 g of cooked white rice, its 130 kcal remains included: the two meal totals
are respectively 359.5 kcal and 244.8 kcal. They are calculation checks, not claims
about an arbitrary real chicken dish.

`intake nutrients = sum(ingredient grams × nutrients per 100 g ÷ 100) × eaten cooked grams ÷ finished batch grams`

The last fraction is 1 for the actually-consumed mode. Batch calculation assumes
an even distribution of ingredients. It does not infer discarded oil/broth or
nutrient losses. The eaten amount cannot exceed the finished batch weight.

## What is saved and what remains limited

The selected records, original ingredient grams, basis, batch/portion weights and
acceptance are persisted in this meal's draft. The result stores calculated
details and source references. Ordinary estimates separately label quantities
extracted from a description, portion-reference conversions, default portions or
the Basic edible-weight assumption. A displayed numeric value does not establish
that the input or recipe is accurate.

The form uses the existing asynchronous API → worker → calculation service path,
with no new Qwen request. Once a meal contains a custom ingredient recipe, use its
structured editor for changes; free-text replies are disabled to avoid silently
discarding the accepted ingredients. Other issued clarification questions and
mode changes remain available. A replacement of the entire description starts
the extraction process again.

This feature does not provide a reusable personal recipe library, new food
records, user accounts or nutritional-label import. Ingredient coverage remains
200 records. Names/quantities supplied in free text can still be misread or
rejected. Consult [QA memory](qa/MEMORY.md) for dated browser findings, including
failures that a passing controlled test does not close.
