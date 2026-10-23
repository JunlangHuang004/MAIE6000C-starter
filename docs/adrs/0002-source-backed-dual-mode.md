# ADR 0002 — Source-backed nutrition and two estimation modes

## Status

Accepted, 2026-10-17.

## Context

Chinese meal names rarely determine a unique recipe, weight or oil amount. Requiring every detail makes quick estimates cumbersome; silently inventing details makes results appear more certain than they are. A cloud language model can interpret descriptions but is not a verified nutrition database.

## Decision

Use Qwen for structured extraction and catalogue matching, and Python for validation, clarification and nutrient arithmetic. Maintain USDA ingredient records with provenance and project-authored editable recipe templates. The initial catalogue held 116 ingredients and 50 recipes; the 2026-10-19 expansion holds 138 ingredients and 250 recipes, with one home-style reference per dish rather than regional duplicates. Do not fine-tune a model or accept model-generated nutrient numbers.

Provide basic and advanced modes. Basic uses visible reference assumptions on a calculation copy. Advanced requests missing details and explicit recipe approval. Persist only explicit facts in the draft, so switching to advanced does not inherit guesses as user facts. Keep questions, dialogue, assumptions and sources with the saved analysis.

Use revision-checked mutations and require confirmation after review. Confirmed records are locked. Keep the legacy demo provider for tests without cloud credentials, with its narrower parsing capability clearly documented.

## Consequences

Calculations and data updates can be reproduced without retraining Qwen. Structured answers avoid extra model calls. Users can choose convenience or more detailed input while seeing the basis of the result.

Extraction can still be wrong. Default portions and reference recipes are assumptions, advanced mode still depends on input quality, and cooking losses are not modelled. Multi-turn parsing incurs latency and model usage. Catalogue maintenance requires source/state checks; supporting a new dish requires explicit ingredient mapping and recipe review rather than merely adding a name.

## Alternatives considered

- Model-only calorie estimates: easy to prototype, but lack reproducible arithmetic and reliable provenance.
- Always require full details: transparent but unnecessarily burdens quick estimates.
- Save defaults as facts: simpler state management, but hides uncertainty when switching modes.
- Train a custom model now: adds dataset and evaluation work without addressing missing meal weights and recipe details.

See [architecture](../architecture.md), [API contract](../api-contract.md) and [nutrition data](../nutrition-data.md).
