# Unsupported-food verification — 31 October 2026

Initial matching source: `224502091bdf1b60635f13c854db93863501b153` on `nutrichat`.
Correction follow-up: `a9843debc3bd25244145d8fdcb0f78b696307e5d`.
The subsequent `7c841b1` update also normalizes a single verified name inside
quantity/detail wrappers and adds structured ingredient recovery; its dated
checks are recorded in [ingredient verification](ingredient-recipe-verification.md).
This follow-up addresses a user-reported unsupported soy-sauce chicken
(`豉油鸡`) being estimated as steamed carp (`清蒸鲤鱼`). Neither `豉油鸡` nor
`酱油鸡` had a catalogue record in that tested snapshot. The later 550-record
catalogue adds an explicit soy-sauce-chicken recipe; use a verified absent name
for current unsupported-food tests. This document does not relabel earlier tests as
checks of this correction.

## Behavior

- Qwen copies the complete original food mention into `source_text` and extracts
  quantities, preparation and recipe facts. Backend lookup resolves identity
  using one exact normalized catalogue name or reviewed alias. It does not use
  a similar-food fallback or trust the model's proposed ID.
- User evidence excludes assistant suggestions and the copied draft/catalogue
  labels embedded in structured-answer history. Ingredient substrings inside
  a different dish do not prove a match.
- Unsupported or unverified names remain visible with a no-corresponding-record
  message in Chinese or English. Both modes withhold all four meal totals and
  details; the unknown item cannot be replaced through a forged answer slot.
- A mixed meal also withholds totals. Residual user clauses are checked so a
  model omitting an unsupported item cannot present only the supported portion
  as the whole meal. Whole-batch details use bounded recognized forms, not broad
  prefix rules that discard arbitrary dish names.
- Text correction remains available. Known food/recipe inputs can still ask for
  details, calculate, confirm and reload. Historical saved estimates are not
  silently recalculated by this change; start a new meal or explicitly correct
  an unconfirmed record to run the new extraction checks.

## Deterministic checks

The initial matching suite passed **454 Python tests**. After the independent
baseline exposed correction and recovery problems, the follow-up passed **469
Python tests**, with two live smoke tests deselected and two existing dependency
warnings. The initial **17 frontend DOM tests** and whole-repository Ruff also
passed; the follow-up changes only backend matching/aliases and tests, and its
changed Python files passed Ruff. These are controlled tests, not claims
of universal live-model recognition or measured nutrition accuracy.

Regression coverage includes:

- Soy-sauce chicken with a real but unrelated ID, invented ID, fabricated canonical
  name or absent source evidence, in both modes: no estimate.
- Soy sauce inside soy-sauce-chicken, raw tomato inside tomato-and-egg stir-fry,
  and raw gai lan inside a garlic-gai-lan dish: no substring substitution.
- An exact reviewed garlic-gai-lan name resolves to its correct catalogue record
  even if the model proposes the broccoli ID.
- Known rice plus unsupported chicken, omitted unknown items, later unknown
  additions and misleading `整锅` / `不加` prefixes: no partial totals.
- Existing Chinese aliases, English names and bounded weight/cooking descriptors;
  quantity-only correction, explicit identity replacement and recipe oil/exclusion
  changes.
- API/worker persistence, reload, mode changes, blocked confirmation and forged
  replacement answers, followed by explicit correction to a supported recipe and
  confirmation.
- Bilingual unsupported notices and conversation history, hidden empty form
  submission, preserved valid recipe answers and available text correction.
- Follow-up: `熟白米饭` / `熟白米飯` aliases, natural consumed-weight corrections,
  explicit consumed-ingredient replacement, whole-pot/intake distinction,
  multiline unknown additions and later corrections after replacing a dish.
  Replacement matching retains all subsequent user turns, rather than silently
  discarding unknown food on a later line or resurrecting an obsolete dish.

## Runtime provenance

The local Qwen project was rebuilt and its final service source copied into all
three application images after the last matching changes. API readiness passed.
The [runtime record](food-matching-runtime.json) records image IDs and matching
SHA-256 fingerprints for all 29 service Python/JSON/HTML/JavaScript files in the
checkout, API, AI and worker containers. The runtime exposes the Qwen provider
and 388 catalogue entries at port 8003. No public ECS deployment was performed.

The [follow-up runtime record](food-matching-runtime-followup.json) separately
records `a9843de`, its fingerprint algorithm and the rebuilt application images.
All 29 service source files matched the committed checkout and all three running
containers; readiness passed. The initial browser run used `2245020`, not this
later runtime.

## Independent browser acceptance

The separately instructed `nutrichat-qa` reviewer uses synthetic meals and a
bounded live-request plan. Its [baseline report](../qa/reports/2026-10-31-independent-browser.md)
records 12 scenarios on `2245020`: no sampled wrong-food substitutions or partial
meal totals, but five workflow/recognition/validation failures. The correction and
explicit-ingredient failures motivated `a9843de`; English recognition and invalid
weight feedback must remain open unless specifically retested. Dated follow-up
findings and retained issues are maintained in [QA memory](../qa/MEMORY.md).
Passing controlled tests alone does not close a live browser failure.

## Limits

Coverage in these dated matching runs was 138 ingredients and 250 reference recipes. Unlisted synonyms,
unrecognized phrasing or incomplete food identity can require rephrasing rather
than an estimate. The bounded text checks are not a general natural-language
parser or a proof that every extraction is correct. Quantity and recipe facts
still need review; recipe-based nutrients remain estimates. Earlier invalid-weight
usability and provider reliability findings are retained until specifically retested.
At the time of these runs, `w07-midterm` still pointed to `5bf6146`. The
[final expansion checks](chinese-expansion-verification.md) document the later
source used for the refreshed submission checkpoint. No Canvas submission was
performed by these checks.
