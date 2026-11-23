# Same-main-ingredient reference review — 23–24 November 2026

This is the historical audit before the
[CFS prepared-food reference update](../cfs-prepared-food-references.md). Its
ingredient-formula comparisons remain valid for that calculation route; they do
not describe the new source-based default for the ten enriched dish records.

## Scope and independent baseline

An independent agent started without the parent conversation history and inspected
the local `test` application at baseline commit `79062a0`. It used a dedicated
synthetic account and live HTTP workflows, not mocked provider responses. Browser
surfaces were unavailable to that agent, so this is not an independent visual UI
audit. The configured provider was HKUST `gemini-2.5-flash-lite`.

The initial eight cases covered cold chicken/cucumber, fried pork, braised beef,
steamed tilapia, edamame/tofu, asparagus, shrimp/greens/noodle soup and an ambiguous
invented name. Three additional targeted cases covered shrimp/egg, mixed fried rice
and minced pork/tofu to improve prepared-dish reference coverage. This selected
sample cannot establish a population-wide recognition or reliability rate.

The baseline used **29 live model requests**, with no automatic retries. Eleven
synthetic records remained unconfirmed. Five selected reference calculations
matched independent ingredient arithmetic to the displayed 0.1 unit; editing a
tofu recipe also recalculated correctly. Missing acknowledgement, an unoffered
ID, stale revision and an unaccepted recipe were rejected without changing the
record. Correct arithmetic does not validate an illustrative recipe's assumptions.

Material baseline findings:

- Shrimp noodle soup received soup and dumpling references that lacked noodles.
- Edamame/tofu received recipes lacking edamame or adding meat; chicken/cucumber
  could receive noodles. Merely sharing one main ingredient was too permissive.
- Some model explanations claimed ingredients absent from the selected template,
  including ketchup, garlic and scallions, or confused carrot with white radish.
- A cold-chicken name was inferred as stir-fried; a minced-tofu name also needed
  a preparation correction. Inference remains a guess requiring review.
- The mixed-fried-rice description failed initial extraction and returned an
  empty draft. It was preserved as a failure rather than silently retried.
- Steamed tilapia correctly produced no compatible reference; the invented name
  requested clarification without proposing facts or nutrition.

## Required correction

Candidates must have exactly the same set of main ingredient IDs as the reviewed
input, and a compatible cooking method. Missing or additional main ingredients
disqualify a reference; ingredient states and fish/meat species are not collapsed.
Classified seasonings such as oil, salt, ginger and garlic may differ, and their
differences still require review. Only positive recipe quantities count.

The server enforces this rule before model ranking, when validating provider
results and when selecting an issued offer. Previously issued incompatible offers
cannot be selected after the rule changes. Existing accepted recipes and saved
nutrition remain historical records. Displayed reasons and ingredient differences
come from the actual catalogue and reviewed IDs, not free-form model assertions.

## Verification after the correction

- **2,338 unit/integration tests passed**, nine existing warnings; the focused
  302-test reference suite overlaps this full run. **95 frontend tests passed**.
- Twelve changed-source hashes matched the host and rebuilt API, AI and worker
  containers. No catalogue records or database migrations changed.
- The independent agent made 13 additional model requests, bringing its total to
  **42** across both stages. Sixteen synthetic records remained unconfirmed.
  No automatic retries were made.

| Revised live scenario | Observed result |
| --- | --- |
| Select an old incompatible noodle offer | HTTP 409; record unchanged. |
| Shrimp + greens + noodles, boiled | No matching reference, no nutrition total; soup and dumplings removed. |
| Edamame + soft tofu, braised | No matching reference; tomato/meat replacements removed. |
| Beef chunks + carrot, braised | No matching reference; extra potato or substituted radish not allowed. |
| Chicken + cucumber, cold | Only `dish_255` cold shredded chicken; no added noodles or sesame-paste recipe. |
| Asparagus, stir-fried | Only `dish_304`; no added shrimp or egg. |
| Shrimp + egg, stir-fried | Only `dish_012`; no rice. The generated explanation correctly states that the declared scallions are absent. |
| Minced pork + soft tofu, braised | Candidate request returned HTTP 502 and left the record unchanged. No retry. |
| Mixed fried rice description | Extraction failed again with an empty draft; no inference or ranking followed. No retry. |

The three successful selected references still required acknowledgement, an
unaccepted ingredient draft, explicit ingredient acceptance and separate meal
confirmation. Their calculated values matched independent arithmetic:
`dish_255` 117.5 kcal/100 g, `dish_304` 73.4, and `dish_012` 140.2. Original
unknown names and source provenance persisted. None was confirmed as eaten.

The primary agent separately verified the noodle no-match result in the actual
browser, including English switching and reload. It used one additional meal
interpretation request, then manual ingredient selection; an empty shortlist
required no ranking call. That synthetic record also remains unconfirmed.
This visual check is separate from the independent agent's HTTP audit.

The two remaining live failures are not reported as passes. Narrow service logs
showed successful provider HTTP 200 responses followed by AI-service parsing or
validation rejection (HTTP 502). The exact rejected field or completion reason
cannot be recovered because raw responses and detailed validation errors are not
retained. Offline inspection found the pork/tofu shortlist and generated
explanation valid; rice extraction occurs before reference matching. Both remain
known model-output reliability limitations, with no substitute or calorie total
produced on failure.

## External nutrition screening

A separate reviewer checked actual baseline candidates against the Hong Kong
Centre for Food Safety's [FRL workbook](https://www.cfs.gov.hk/resources/Nutrient%20profiles_FRL.xlsx).
The [official guide](https://www.cfs.gov.hk/english/nutrient/searchmenu.php) defines
these figures per 100 g edible portion. The three same-named prepared-dish matches
below are not identical recipes or measurements of the original synthetic meal.
Other candidates were left unmatched when a defensible comparator was unavailable.

| Actual baseline candidate | App kcal/100 g | CFS kcal/100 g | Energy difference | Protein difference | Fat difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pineapple sweet-and-sour pork (`dish_266`) | 174.21 | 240 | −27.4% | +77.8% | −56.1% |
| Cold noodles with shredded chicken (`dish_341`) | 148.14 | 190 | −22.0% | +34.6% | −48.7% |
| Scrambled egg with shrimp (`dish_012`) | 140.15 | 230 | −39.1% | +0.7% | −49.9% |

Difference = `(app − reference) / reference × 100`. The requested ±20% threshold
is a screening rule, not an established error bound. App values were independently
recomputed from the offered template's ingredient quantities and finished yield;
these three baseline observations were offers, not confirmed eaten meals.

The [CFS/Consumer Council study](https://www.cfs.gov.hk/english/programme/programme_rafs/programme_rafs_n_01_23_abstract.html)
reports measured energy ranges of 190–280 kcal/100 g for pineapple sweet-and-sour
pork and 180–330 for shrimp/egg; the app assumptions are below both ranges.
No corresponding measured range was verified for chicken noodles. These restaurant
sample ranges are not confidence intervals for a specific meal.

Carbohydrate percentages were deliberately excluded: app USDA records use total
carbohydrate, while CFS FRL uses available carbohydrate. Comparing these definitions
as if identical would produce a misleading accuracy verdict.

These discrepancies warrant recipe/yield/retained-oil review. Same-ingredient
filtering does not correct nutrient data or guarantee nutritional equivalence.
This update does not replace catalogue values with the external averages. The
three candidates were observed before the stricter rule; some may no longer be
offered for those original inputs. Full sanitized case evidence and downloaded
source material remain in the local audit output, outside Git.

The strict retest subsequently selected and calculated `dish_012`: its displayed
140.2 kcal/100 g matches the unrounded 140.15 used above, so the −39.1% screening
difference remains after recommendation filtering. No sufficiently close verified
prepared-dish comparator was found for the selected cold chicken or asparagus;
they remain explicitly unvalidated rather than being assigned a passing verdict.
