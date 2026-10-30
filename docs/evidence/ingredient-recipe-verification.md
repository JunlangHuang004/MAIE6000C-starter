# Ingredient recipe verification — 31 October 2026

Product source: `7c841b15231cc3372bed571efb3b9335751db3f1` on `nutrichat`.
This dated report precedes the final catalogue expansion and tag refresh. See
[the final expansion checks](chinese-expansion-verification.md) for the later
source. No public ECS deployment or Canvas submission is implied by these local results.

## Scope

The user requested improvements based on the reviewed OpenNutriTracker code.
This implementation adds an independently written, structured ingredient recipe
path within NutriChat's existing API/job/worker architecture. It does not copy the
other project's code or replace the course service framework.

- Explicit per-item ingredient selection and positive gram inputs; unknown
  ingredient IDs, dish-template IDs, duplicates and forged nutrients are rejected.
- Actually-consumed ingredient quantities or whole-batch quantities with finished
  yield and eaten cooked weight. The latter cannot exceed the whole batch.
- Other meal items are preserved. A remaining unresolved food blocks all totals.
- Custom recipes are labelled separately from catalogue dishes, with source
  records and input/portion evidence. Ordinary results expose quantity provenance.
- Structured edits use the validated draft, without a Qwen request. Mode changes,
  clarification answers and final confirmation preserve the facts and revision
  locks. Free-text replies are disabled while custom recipes exist.
- Bilingual form controls, preserved unsent entries, explicit acceptance, stale
  conflict handling and locked confirmed records.
- A narrow matching fix accepts a single reviewed name with only known quantity
  or preparation wrappers when Qwen includes those wrappers in `source_text`.
  Multiple foods, unknown tails, repeated portions and fabricated source spans
  remain rejected.

## Controlled checks

The complete local Python run passed **545 tests**, with two live smoke tests
deselected and two pre-existing dependency warnings. The frontend suite passed
**26 DOM tests**; whole-repository Ruff and whitespace checks passed.

New coverage includes 56 ingredient arithmetic/API/worker/provenance cases,
20 wrapped-source matching cases and nine ingredient-editor DOM cases. API tests
use SQLite and a controlled internal AI-service boundary; they do not claim live
Qwen recognition or concurrent PostgreSQL correctness.

The arithmetic tests independently check raw chicken breast, cooking oil and soy
sauce against their recorded nutrient values. Consumed quantities 150/5/10 g give
229.5 kcal. A 300/10/20 g batch with 600 g finished yield and 150 g eaten gives
114.8 kcal after rounding. An additional 100 g cooked rice remains included in
the meal totals. Protein, fat and carbohydrate values are checked separately.

The integration checks cover queueing with cleared totals, worker completion,
unchanged other items, unresolved-item total suppression, persisted reload,
structured edits, mode changes, stale revisions, queued/confirmed locks and
blocked free-text edits. The frontend checks cover exact request payloads, batch
validation, search selection, state labels, translation preservation, stale input
preservation, explicit acceptance and confirmation controls.

## Live runtime and independent review

See the [runtime manifest](ingredient-recipe-runtime.json) for the application
source fingerprint and running image IDs. All 30 service source files matched
the committed checkout and the API, AI and worker containers; readiness passed.
The [real HTTP integration record](ingredient-recipe-http-check.json) covers
API → worker → calculation service → PostgreSQL using a previously created
synthetic unresolved rice record. Explicitly replacing it with the quarter-batch
recipe yielded 114.8 kcal, 17.3 g protein, 4.5 g fat and 0.2 g carbohydrate.
Confirmation and GET reload matched; an edit to the confirmed record returned
409. This structured check did not request another model extraction. Earlier
browser observations of that record remain dated evidence of its prior revision.

Browser observations, exact inputs and
screenshots are maintained separately in [QA memory](../qa/MEMORY.md). Older
failed rice/correction/recovery observations remain in their original reports;
controlled passing tests do not retroactively turn them into live passes.

## Limits

The form needs actual ingredient information from the user. It does not infer a
missing recipe, add unsupported ingredients, automatically convert raw/cooked
weights, deduct discarded oil/broth or measure cooking losses. Batch portions
assume an even mixture. Saved recipes belong to the meal record; a reusable
personal recipe library and individual account ownership are not implemented.
Live free-text extraction, invalid-weight error clarity and catalogue coverage
remain separate concerns.
