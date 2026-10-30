# Local model verification — 2026-10-30

Scope: the experimental `test` branch's HKUST GenAI and Ollama adapters, using the
isolated model lab on local port 8004. Existing Qwen settings, the `nutrichat`
branch and the public deployment are outside this verification scope. All meal
inputs used synthetic examples; this document excludes keys and account IDs.

**Outcome: HKUST GenAI passed all nine final live checks. The local Ollama models
did not pass application acceptance and cannot reliably replace it.** The active
lab provider was verified as `hkust`, using `gemini-2.5-flash-lite`. Ollama and
both downloaded local models remain available for classroom use and experiments.

## Automated checks

The initial offline unit and integration run passed **651 tests**. After the
strict Ollama output schema, compact Chinese prompt and additional fact checks,
**97 targeted tests** passed, and `ruff check services tests` passed. The earlier
full-suite result predates those changes; a new complete run is not yet recorded
here. The recorded Ruff scope is the services and tests directories.

Model-boundary tests use synthetic responses and do not need a real API key.
These checks cover provider selection, request and response validation, failure
handling, clarification and persisted meal state. They do not by themselves
establish live provider availability or extraction quality.

See [the lab guide](../models-local-lab.md) for the isolated environment and the
targeted adapter/flow test command. `LLM_PROVIDER=heuristic` selects the existing
strict English demo parser without model requests.

## HKUST GenAI: nine final live checks passed

Provider: `hkust`. Model: `gemini-2.5-flash-lite`. The results below were transcribed
from the saved live-check JSON. Food descriptions summarize the extracted draft;
they are not claimed to be verbatim copies of every submitted message.
An initial six-check run passed; the final expanded run repeated the full meal
workflow and added missing-mass and unsupported-food cases with semantic checks.

| Check | Mode and meal facts | Observed status | Energy (kcal) | Protein (g) | Fat (g) | Carbohydrates (g) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `basic-rice-egg` | Basic: cooked white rice 100 g + peeled boiled egg 50 g | `completed` | 207.5 | 9.0 | 5.6 | 28.7 |
| `basic-chinese-recipe` | Basic: tomato and egg stir-fry (番茄炒蛋), cooked portion 200 g | `completed` | 210.2 | 10.7 | 14.9 | 8.9 |
| `advanced-asks-weight` | Advanced: peeled boiled egg, cooked weight omitted, no added oil | `needs_input` | — | — | — | — |
| `advanced-125g` | Same Advanced meal: answer the edible-weight question with 125 g | `completed` | 193.8 | 15.7 | 13.3 | 1.4 |
| `corrected-150g` | Correct the boiled-egg portion to 150 g | `completed` | 232.5 | 18.9 | 15.9 | 1.7 |
| `confirmed-after-reload` | Confirm the corrected meal, then reload it | `confirmed` | 232.5 | 18.9 | 15.9 | 1.7 |
| `basic-no-mass` | Basic: `一碗米饭`; no explicit grams, one bowl retained | `completed` | 195.0 | 4.0 | 0.4 | 42.3 |
| `advanced-no-mass` | Advanced: `一碗米饭`; no explicit grams | `needs_input` | — | — | — | — |
| `mixed-unknown` | Basic: `100克白米饭+100克超新星糕点`; unknown pastry retained | `needs_input` | — | — | — | — |

All nine recorded checks matched their expected statuses, passed the checker's
specified semantic conditions and reported no error.
The missing-weight response issued `0.grams` and withheld all four nutrient
totals. Supplying 125 g completed revision 2; correction to 150 g completed
revision 3. Confirmation and reload preserved the 150 g meal and totals at
revision 4. Rows from `advanced-asks-weight` through `confirmed-after-reload` are
consecutive states of one meal, not independent meals or model calls.

For the Basic bowl of rice, the draft retained `grams=null`, `portion_count=1`
and `portion_unit=bowl`; the engine supplied its labelled 150 g reference serving,
producing 195 kcal. Advanced mode retained the missing weight and asked
`0.grams`. In the mixed known/unknown case, the pastry remained present with
`food_id=null`; the app asked `1.food_id` and withheld all four nutrient totals.

The numbers are the application's catalogue-based estimates. The tomato-and-egg
result uses a reference recipe; these tests do not measure the nutrient content
of a real prepared dish. The recorded cases establish this limited live flow,
not accuracy across the full food catalogue or every possible correction.

## Ollama: final application acceptance failed

Native `llama3.2` answered a basic arithmetic prompt, so its classroom installation
check succeeded. An initial application request failed amid resource contention
on an 8 GB Mac running five local Docker stacks. A post-restart application run
still failed all six cases: HTTP 200 responses contained invalid structures such
as `recipe_ingredients: [null, null]`, as well as semantic mistakes. The problem
was not merely connectivity or resource pressure.

The official [`qwen2.5:1.5b`](https://ollama.com/library/qwen2.5:1.5b) model
(approximately 986 MB download) was installed as a smaller local experiment.
Its initial strict-schema/English-prompt run produced usable JSON but invented
weights and assigned an unsupported pastry to rice. Its earlier four-of-six
status count was not a semantic pass rate and is not treated as successful
application verification.

The final run used `qwen2.5:1.5b`, a compact Chinese prompt, a strict JSON schema,
selected food-ID allowlists and the additional no-mass/name checks. The shared
validator was not weakened. Exact synthetic inputs and observed outcomes follow:

| Check and input | Expected outcome | Observed outcome | Acceptance |
| --- | --- | --- | --- |
| `basic-rice-egg`: `白米饭100克，去壳水煮鸡蛋50克，均为熟重` (Basic) | Both foods retained; 207.5 kcal | `completed`, 130 kcal; the egg was omitted entirely. | Failed |
| `basic-chinese-recipe`: `番茄炒蛋200克，熟重` (Basic) | Reference dish portion; 210.2 kcal | `completed`, 492 kcal; invented 200 g raw egg and 200 g whole-pot yield overrode recipe facts. | Failed |
| `advanced-asks-weight`: `去壳水煮鸡蛋，熟重，没有额外用油` (Advanced) | Egg with unknown grams; ask weight and withhold totals | `needs_input`, no totals; asked `0.grams` plus an unnecessary `0.resolved` question. | Passed limited check |
| `advanced-125g`: answer `0.grams=125` for that meal | `completed`, 193.8 kcal | `needs_input`, no totals; an extra uncertainty question remained unresolved. | Failed |
| `basic-no-mass`: `一碗米饭` (Basic) | Rice with no explicit grams; labelled reference estimate | `completed`, 195 kcal from the engine's 150 g serving assumption; model draft grams stayed null. | Passed limited check |
| `advanced-no-mass`: `一碗米饭` (Advanced) | Ask for grams; no nutrient totals | `needs_input`, no totals; asked `0.grams`. | Passed limited check |
| `mixed-unknown`: `100克白米饭+100克超新星糕点` (Basic) | Preserve the unknown pastry, ask for clarification and withhold totals | `completed`, 130 kcal; the unknown pastry was silently omitted. | Failed |

Only **3 of 7 executed checks** met both their expected status and the checker’s
specified semantic conditions. These are limited assertions, not a general
accuracy score: for example, the Basic bowl case still contained an unsupported
100 g suggestion in its uncertainty text, while the engine used its own labelled
150 g reference. The Advanced egg draft had the requested weight after the reply,
but failed completion because of the additional unresolved question.

The planned nine-check flow stopped its correction/confirmation sequence after
the 125 g reply remained `needs_input`. Therefore, the later 150 g correction and
confirm/reload checks were not executed for this model. **No acceptable complete
Ollama meal workflow was established.** Silent food omission and invented recipe
facts remain observed, unresolved failures. These local models are retained for
experiments, not selected as the reliable application provider.

## Environment restoration

After the resource troubleshooting, all 16 previously running local containers
were restored and reported healthy. The isolated model lab was returned to HKUST
before its final nine-check run. Container health is a readiness check, not a new
end-to-end verification of every other local application.

## Interpretation and remaining limits

- Ollama uses a small local model and a bounded candidate catalogue selected from
  user text. Retrieval can miss unfamiliar wording or return ambiguous candidates;
  it does not guarantee the extracted food identity or portion is correct.
- The no-mass check examines the entire user text/history, not the provenance of
  each item's weight. A mass elsewhere in the dialogue, or an English unit word
  treated as possible mass evidence, can leave an invented weight undetected.
  The food-name check uses lexical matching; an ingredient name inside a dish can
  still be confused with the dish itself. These checks cannot detect foods the
  model silently omitted.
- The deterministic engine calculates nutrients from validated catalogue records.
  A valid calculation can still describe the wrong food if the user does not
  review the extracted facts and assumptions.
- Structurally invalid model output and provider errors fail the request instead
  of producing fallback nutrients. Structurally valid but wrong facts can still
  reach the engine and produce misleading totals, as the local tests demonstrate.
- Automated checks and the nine HKUST checks are not evidence that all Chinese
  recipes, long conversations, concurrent requests or low-memory environments
  work reliably. The final Ollama application run failed acceptance; no additional
  tuning or successful retest is claimed here.
- This is local verification, not a remote CI result or public deployment test.
