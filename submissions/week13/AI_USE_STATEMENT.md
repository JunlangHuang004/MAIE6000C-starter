# AI Use Statement — Week 13

**Team:** NutriChat · **Updated:** 2026-11-27 · **Release:** `w13-final`

This statement covers the application baseline
`1d17a66ffa445a5dc6a4d699e408c6772929ea79` and refreshed final documentation.
Resolve `w13-final^{commit}` for this package's release SHA. The earlier `6b87aef`
checkpoint is preserved at `archive-w13-final-6b87aef`.

OpenAI Codex assisted development and provided advice, including code, debugging, tests,
source/data review, illustrative reference-recipe drafting and documentation.
Ingredient nutrients and CFS prepared-food vectors retain their identified sources;
project recipe amounts and yields remain assumptions, not AI-measured nutrition.

At runtime, the configured model interprets meal text and can suggest editable
ingredients/methods or rank compatible recipe IDs after an explicit user request.
The latest recorded live checks used HKUST `gemini-2.5-flash-lite`; Qwen is a
separately configured alternative. Server checks constrain identities and reference
offers, and the server creates reference explanations. Python calculates nutrients,
profile references and diary summaries. AI does not supply authoritative nutrient
values, approve recipes or confirm meals. The offline demo uses a deterministic
fixture, not a generative model.

Codex-assisted checks are documented in the
[24 November review](../../docs/evidence/name-reference-inference-verification.md#2026-11-24-name-grounding-and-preparation-safeguards)
and separately dated [15 November verification](../../docs/evidence/week13-verification.md).
Reports retain failed attempts and unmet outcomes; the last three targeted checks
do not constitute a complete rerun of the 20-name review. Historical screenshots
are not evidence of a new walkthrough. Assigned team roles do not establish that
each member personally performed these assistant-run checks or an independent
rehearsal.

The team defined the scope and rejected image-based estimation. The team remains
responsible for reviewing, understanding and submitting the final work, including
its source assumptions, AI limitations and exact published version.
