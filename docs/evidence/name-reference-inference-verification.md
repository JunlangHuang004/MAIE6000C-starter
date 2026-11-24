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

## 2026-11-24: name grounding and preparation safeguards

This follow-up covers the local `test` working tree based on `2e4e021`, using
HKUST `gemini-2.5-flash-lite` at `http://localhost:8008`. The food catalogue and
the `nutrichat` branch were not changed by this fix.

The shared inference guard now checks the stored dish name in both the AI service
and API. It rejects unsupported or contradictory ingredient types, unmentioned
main ingredients, omitted named ingredients and ambiguous methods. Longest phrase
matching distinguishes seasoning compounds, ingredient cuts and explicit states;
a single ambiguous noun cannot become multiple ingredient variants. Unexplained
name text produces a clarification question with no proposed facts. Explicit
Chinese, Traditional Chinese and English cooking verbs are supported. Negated
verbs are ignored: `烧（非油炸版）` now matches braising rather than frying.

Final automated verification:

- **2,670 backend unit/integration tests passed**, using
  `NUTRITION_PROVIDER=demo LLM_PROVIDER=heuristic`.
- **108 frontend tests passed**; the public response shape and editable
  clarification interface remain unchanged.
- Ruff and whitespace checks passed. All six changed application modules matched
  the rebuilt API, AI and worker containers by SHA-256.
- An initial backend run inherited the local cloud-provider settings and failed
  eight offline-parser expectations. That run is retained separately; the final
  properly configured run above passed. Automated tests made no intentional live
  provider requests.

An independent agent then entered 20 distinct names as `<name>200g`, with no
ingredient corrections in the initial name-assisted path. The initial batch
produced three exact catalogue matches, three candidate successes, twelve
clarifications, one ranking error and one inference error. It also tested two
explicit manual clarifications: the shrimp example reached an acknowledged
reference selection, while the thigh example returned a ranking error. These
first errors were retained rather than silently retried.

| Case | Observed behavior |
| --- | --- |
| 香煎豆腐 | Suggested tofu/frying and recommended 蒜香煎豆腐. |
| 家常烧豆腐 | Suggested tofu with seasonings, without invented pork; recommended 红烧豆腐. |
| 蒜香炒芦笋 | Recommended 清炒芦笋. |
| 蒜香牛肉粒 / 蚝油杏鲍菇 | Requested clarification; did not retain ground-beef or enoki substitutions. |
| 凉拌手撕鸡 / 蒜香鸡腿 / 番茄牛腩煲 | Requested actual ingredient/cut/method information. |
| 翡翠白玉汤 / 赛螃蟹 / 招牌私房菜 | Requested clarification rather than constructing an assumed recipe. |
| 蚂蚁上树 / 豉油鸡 / 蒜蓉粉丝蒸虾 | Correctly recognized existing catalogue records before inference. |
| 香辣虾, after explicit actual shrimp/chili and frying were supplied | Recommended 椒盐虾仁 and reached an acknowledged, unaccepted ingredient template. |

Three diagnostic provider requests identified two avoidable formatting problems:
the inference prose validator interpreted the English dish title "Three Cup
Chicken" as a quantity, and a completed ranking response was not valid JSON.
The provider wire contract was consequently reduced to facts/IDs only. The
server now creates every displayed question, explanation and difference; the
public schemas retain their existing strict checks. Malformed and incomplete
provider output is still rejected, not repaired.

After rebuilding, an independent agent made exactly three targeted HTTP checks
against the final AI service, without another meal extraction:

| Previously failing path | Final targeted result |
| --- | --- |
| 酱烧茄子 ranking | HTTP 200; 红烧茄子 (`dish_024`) and 鱼香茄子 (`dish_154`), with catalogue-derived explanations. |
| 三杯鸡 inference | HTTP 200; normal clarification, empty ingredients and null method. |
| 蒜香鸡腿 ranking after actual skinless thigh/garlic and frying were supplied | HTTP 200 with no candidates. The response contract passed, but the expectation of a nonempty recovery was **not met**. |

The final three checks resolve the observed transport/format errors for those
requests, but do not demonstrate successful reference recovery for the thigh
example or constitute a rerun of the entire 20-name batch after the last change.
The model may decline a mechanically compatible shortlist; a useful reference
is not guaranteed. No ingredient-equality rule was relaxed to force a result.

There were **49 live model calls** in total: 43 in the independent batch/manual
checks, three diagnostic calls and three post-fix checks. There were no automatic
retries. All three acknowledgement guards rejected selection without acceptance
and allowed it with acceptance, while retaining the unknown identity, missing
totals and an unaccepted ingredient template. All 20 synthetic analyses remained
unconfirmed, with zero confirmed/dated meals and zero daily records. The test
session was revoked. Account-specific evidence remains outside Git in
`outputs/dish-name-fix-2026-11-24/` in the parent workspace.

These checks evaluate software behavior and observed model responses, not the
nutritional accuracy of an actual dish. Catalogue coverage and conservative
name evidence still limit how many dishes receive suggestions.
