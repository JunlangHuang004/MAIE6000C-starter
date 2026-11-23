# CFS reference verification — 24 November 2026

## Scope

This update applies to `test`, catalogue `2026-11-24.1`. It adds ten attributed
prepared-food references from the Hong Kong Centre for Food Safety (CFS), while
retaining 202 USDA ingredient records and 384 recipe identities. The other 374
recipes remain illustrative ingredient calculations. See the
[source and behavior guide](../cfs-prepared-food-references.md) and
[row-level source map](cfs-prepared-food-source-map.json).

The local Docker preview used HKUST `gemini-2.5-flash-lite`. The historical
`nutrichat` branch, `w13-final` tag and public ECS deployment were not updated.
Qwen and Ollama were not called during this browser pass.

## Automated checks and independent review

- Full backend unit/integration suite: **2,446 passed**, nine existing warnings.
- Full frontend suite after the final disclosure improvement: **108 passed**.
- Independent review: all ten nutrient vectors matched the official workbook;
  **108 overlapping focused tests passed**. The review identified a preparation
  mismatch risk, which was fixed before the full suite and live acceptance.
- Source tests cover workbook mappings, source-specific cooking methods, trace
  fibre, carbohydrate definitions, data regeneration and unmodified ingredient
  values. Runtime tests cover quantity scaling, explicit raw/gross-weight
  clarification, zero oil, ingredient overrides, historical snapshots and
  confirmation/reload with mixed carbohydrate definitions.
- Ruff, JavaScript syntax and whitespace checks passed. Seventeen changed files
  matched the host in each rebuilt API, AI and worker image (51 hash matches).
  The database container and provider configuration were preserved.

Focused tests overlap the full run and should not be added to its count.
Software tests do not demonstrate nutritional accuracy for an individual meal.

## Observed browser workflows

Two synthetic meal descriptions were interpreted by the configured live model.
Subsequent structured choices used the local calculation workflow. Account-specific
transcripts and screenshots are retained locally outside the published repository.

| Action | Observed result |
| --- | --- |
| Basic: `虾仁炒蛋100g` | 230 kcal, 13 g protein, 18 g fat and 2.6 g available carbohydrate. The CFS reference badge and sample-versus-actual-meal caveat were visible. |
| Switch to Advanced and choose ingredient calculation | The editable recipe required review. After setting batch oil to 0 g, accepting shrimp 200 g, egg 200 g, salt 2 g and finished yield 400 g, the 100 g portion became 107 kcal, 13.1 g protein, 5.3 g fat and 0.8 g total carbohydrate. It was labelled a reviewed recipe, not CFS data. |
| Basic: `虾仁炒蛋100g，熟米饭150g` | 425 kcal, 17 g protein and 18.4 g fat. Carbohydrates displayed “Not combined”, with separate available-carbohydrate 2.6 g and total-carbohydrate 42.3 g subtotals. Confirmation remained enabled. |
| Switch the mixed meal to English and reload | Values, source labels and both carbohydrate subtotals persisted. |
| Switch the mixed meal to Advanced | The calculation-basis dropdown was prominent; its longer source explanation defaulted to a closed disclosure. Selecting CFS and switching back to Chinese preserved the answer. |
| Submit the CFS choice | The same 425 kcal result and separate carbohydrate subtotals returned, ready for review. |

Both synthetic records remain **unconfirmed**, so they do not count toward daily
intake. Existing meals, profiles and trends were not edited. Final confirmation,
immutability and snapshot readback were covered by automated API regressions.

## Limits

Only the ten mapped dishes have a verified CFS prepared-food vector in this
update. Same-name samples can differ from a user's recipe, oil retention and
water content. The update does not establish an error bound of 20%, validate all
384 recipes, or fix the historical model-output failures documented in the
[independent reference audit](strict-reference-verification.md).
