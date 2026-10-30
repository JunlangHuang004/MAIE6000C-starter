# Chinese catalogue expansion verification — 31 October 2026

Initial expansion source: `71a0ecd56f2de09460ce899b1b183f723ab45b0e`.
Final product source: `dae0b946e286736020becf018c49b4e81eb46ec6`, branch `nutrichat`.
Documentation and fresh screenshots are added in a later commit without changing
the tested service files. Resolve the pushed `w07-midterm` tag for the exact final
submission commit; the product-source SHA above identifies what was executed.

## Data and identity checks

- **200 ingredients and 350 reference recipes**, catalogue version `2026-10-31.1`.
  All original 138 ingredient source records, 250 recipe objects and 388 runtime
  food objects compare equal to the preceding committed snapshot.
- The 62 new ingredients use the official USDA SR Legacy 2018 CSV archive. The
  [source map](ingredient-expansion-source-map.json) records the archive checksum,
  FDC identifiers, descriptions, states and all four per-100g nutrient values.
  Each new value was checked against the archive; missing values were not set to
  zero. Source data are CC0; Chinese names/selection are curated by this project.
- The [recipe manifest](recipe-expansion-manifest.json) identifies 100 added,
  project-authored editable reference recipes. Their amounts, retained oil and
  finished yields are assumptions, not a measured Chinese nutrition dataset.
- All IDs and normalized names/aliases are unique. Every recipe ingredient
  reference exists, and all 350 recipes pass controlled Basic and Advanced
  calculations. The [dish index](../recipe-catalogue.md) contains all 350 entries.
- Soy-sauce chicken now has its own recipe `dish_251`. Four simplified/traditional
  aliases resolve to that identity even when a mocked model proposes the former
  incorrect fish ID. Unknown-food tests now use genuinely absent synthetic names;
  they continue to require no substitution and no partial meal totals.
- New data prioritize Chinese. Existing 388 English display mappings remain;
  added entries fall back to their Chinese names in the English interface.
  There are still deliberate gaps, including Chinese garlic chives, garlic
  shoots, preserved eggs, dried lily flowers, pressed dried tofu and Chinese
  fermented cabbage where no suitable source record was selected.

## Controlled tests

The initial expansion passed **654 Python tests and 26 frontend DOM tests**.
The final narrow wrapper fix passed **664 Python tests** and Ruff; its ten new
regressions cover explicit deboned/shelled annotations and unknown text that must
remain rejected. The final change does not modify the tested interface assets.
Whole-repository Ruff and
`git diff --check` passed. The Python run reports two existing dependency
deprecation warnings. These are controlled tests, not live model accuracy scores.

The Python suite must run with `NUTRITION_PROVIDER=demo`, matching the CI/default
fixture. An initial local container run inherited the private `.env` provider and
produced eight fixture-prevalidation failures; explicitly selecting `demo` restored
the intended test environment and all 654 tests passed. No test assertions were
weakened to make that run pass.

The expansion adds bounded prompt retrieval: up to 60 primary matches and 120
total records including recipe ingredients. It only uses user-originated text;
assistant suggestions and server-copied draft text cannot supply matching evidence.
An independent read-only review additionally checked all 550 canonical names
with a 100 g prefix: every name retrieved and grounded to its own unique ID.
Related candidates are context, not permission to replace a food. The independent
exact-name grounding guard still determines accepted catalogue identities.

## Executed runtime and browser evidence

The API, AI and worker images were rebuilt from the committed service files.
All **31** Python/JSON/HTML/JavaScript source files match the local commit and all
three running containers. API/PostgreSQL readiness passed; `/foods` returned
provider `qwen` and 550 catalogue records. The
[runtime manifest](chinese-expansion-runtime.json) records image IDs and the
source fingerprint without credentials. The
[final runtime manifest](chinese-expansion-final-runtime.json) records the later
`dae0b94` build separately; earlier captures and the offline check remain tied to
`71a0ecd`.

The [independent browser report](../qa/reports/2026-10-31-expanded-demo.md) records
actual inputs, model-action count, outcomes and remaining issues on this runtime.
The [fresh screenshot walkthrough](../../demo/SCREENSHOT_GUIDE.md) shows the
observed workflow and is the TA's visual guide. Historical reports remain dated
and are not relabelled as tests of this expanded source.

## Browser-discovered wrapper correction

On `71a0ecd`, the live description
`豉油鸡200克熟重、可乐鸡翅75克熟重（已去骨）、蒜蓉空心菜150克熟重。`
incorrectly rejected the known cola-wing record and withheld the meal totals.
The original failed synthetic record is `f3732899-2c63-4c26-8301-2d165fc4683d`.
A separate plain-name/weight sample resolved all three new dishes correctly.

The identity guard accepted `去骨` but not the explicit marker `已去骨`.
`dae0b94` adds only the bounded `已去骨` / `已去壳` / `已去殼` suffixes.
It does not discard arbitrary text in parentheses or change catalogue/nutrient/UI
assets. The independent report retains the failure and records the targeted
post-fix live result separately. The exact phrase passed on `dae0b94`, with IDs
`dish_251`, `dish_252`, `dish_298`, quantities 200 / 75 / 150 g and a 743.8 kcal
reference estimate. Record `ed30cc68-d1bb-4441-8d66-b60c8395c546` is distinct
from the failed attempt. Historical saved results are not rewritten.

A [read-only HTTP readback](expanded-demo-http-readback.json) corroborates the
new three-dish result and the persisted confirmed main (312.7 kcal) and custom
recipe (244.8 kcal) records on the final runtime. The browser report distinguishes
which actions/captures occurred before and after the narrow backend-only fix.

## Offline vertical-slice check

A rebuilt, separate key-free stack passed `python3 demo/run.py check` on the initial expansion
31 service files (`71a0ecd`). The [saved report](../../demo/evidence/offline-expanded-check-2026-10-31.json)
records source `71a0ecd` and `dirty: true` because documentation/screenshots were
being prepared. A paused worker left input/job persisted with zero attempts;
resumed processing produced 155 kcal, correction produced 310 kcal, confirmation
and reload agreed, and editing a confirmed result returned HTTP 409. Two worker
claims, correlated logs, PostgreSQL values and the increased internal AI request
counter demonstrate the required asynchronous boundary. The two HTTP smoke tests
also passed separately against this rebuilt offline stack. This fixture is separate
from Qwen and is not evidence of Chinese-language model extraction.

## Limits

This is finite catalogue coverage, not universal food recognition. The model can
still reject a known name or misinterpret quantities and conversation. Users must
review identity, weights, states and recipe assumptions. Free-text multi-ingredient
recovery and invalid-weight feedback have unresolved historical QA findings;
the structured ingredient form is the supported explicit recovery path.

No public ECS deployment or Canvas submission was performed by these local
checks. GitHub CI must be inspected for the exact pushed final commit.
