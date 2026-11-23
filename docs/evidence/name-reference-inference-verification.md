# Name-assisted reference acceptance — 23 November 2026

This report records the initial implementation. The later
[same-main-ingredient audit](strict-reference-verification.md) supersedes its
broader candidate filtering; the earlier observations remain historical evidence.

## Scope

This follow-up applies to `test` and catalogue `2026-11-23.2`. It adds an optional
model-assisted entry into the existing similar-recipe workflow. It does not
change catalogue nutrient values, the historical `nutrichat` branch or the
`w13-final` tag. The local Docker preview used HKUST `gemini-2.5-flash-lite`.
Qwen and Ollama transport behavior has automated coverage; they were not called
in this live browser pass. The public ECS deployment was not updated.

## Automated checks

- Full unit/integration run before the final explanation-validator refinement:
  **2,271 passed**, nine warnings.
- Final overlapping reference suite after the refinement: **256 passed**, two
  warnings. It covers provider responses, supported ingredients, ambiguous names,
  amounts/scores, normal dish-name wording, ownership, revisions and state rules.
- Frontend suite: **95 passed**, including editable guesses, explicit search,
  unsaved-answer preservation, cancellation, errors, language changes, logout and
  stale-record recovery.
- Ruff, JavaScript syntax and whitespace checks passed. Eighteen source hashes
  matched across the host and rebuilt API, AI and worker containers.

These counts overlap and must not be added together. Software tests do not
validate the nutritional accuracy of a real meal or guarantee model reliability.

## Observed browser workflows

The primary agent used the existing local account with two synthetic meals.
Screenshots and account-specific transcripts remain outside Git.

| Step | Observed result |
| --- | --- |
| Enter `蒜香西兰花炒虾仁200g，熟米饭150g` | The unknown dish remained unresolved; no whole-meal nutrition total was shown. |
| Request name inference | The model suggested garlic, shrimp and broccoli plus stir-frying. The interface labelled them as guesses and exposed editable fields; it did not request candidates automatically. |
| Review and request references | `西兰花虾仁` ranked first, followed by cucumber/shrimp and asparagus/shrimp references. Reasons and ingredient differences were shown. No candidate was automatically selected. |
| Select the first reference | Continue stayed disabled until the approximation acknowledgement was checked. Selection opened an unaccepted ingredient draft with the original unknown name and no total. |
| Edit and accept ingredients | Changed oil from 12 g to 8 g; reviewed shrimp 250 g, broccoli 250 g, garlic 10 g, salt 2 g, finished batch 430 g and consumed portion 200 g. The reference item was 161.9 kcal and the preserved 150 g rice was 195 kcal. |
| Review the result | Whole-meal total: **356.9 kcal, 23.4 g protein, 5.8 g fat, 52.6 g carbohydrate**. The original name, approximate-reference label and separate confirmation button remained visible. |
| Switch to English and reload | The same values, original unknown name, 200 g cooked portion, reference label and 150 g rice persisted. |
| Enter `招牌私房菜200g` and request inference | The model said the name was ambiguous and requested ingredients and preparation. No ingredient/method guess, candidate selection or nutrition total was produced. |

Five live model requests completed: two initial meal interpretations, two
name-inference requests and one candidate-ranking request. There were no automatic
retries. Ingredient calculation used the existing local calculator. This small
sample does not establish a reliability rate.

Both synthetic records remain **unconfirmed** and therefore do not contribute to
daily intake. Existing meals, profile and trend data were not edited. Final meal
confirmation was covered by the existing workflow and automated regression tests;
it was deliberately not repeated on these synthetic records.

## Remaining limits

Name inference can be wrong. Users must review the inferred facts, candidate
differences and every ingredient in the selected template, including oil and
seasonings. Candidate explanations are not an exhaustive ingredient audit or an
allergy checker. The available catalogue can miss an otherwise reasonable
reference, and a similar recipe is not evidence of nutritional equivalence.
See [the workflow and limits](../similar-recipe-references.md) and
[nutrition-data assumptions](../nutrition-data.md).
