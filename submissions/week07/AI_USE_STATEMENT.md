# AI Use Statement — Week 7

**Team:** NutriChat

**Date:** 2026-10-27

## Tools and uses

- **OpenAI Codex:** assisted with project planning, implementation and modification
  of application code, tests, catalogue tooling, deployment configuration,
  debugging, documentation and milestone preparation. It also executed automated
  checks and the synthetic rehearsal reported in the verification record.
- **Alibaba Qwen (configured through Model Studio):** used by the application to
  extract structured food facts from Chinese descriptions and corrections.
  Qwen is a runtime dependency, not the authoritative source of nutrient values.
  Model selection is configurable; the adapter defaults to `qwen-plus`.

## Decisions, verification and limits

The team representative specified the product direction, basic/advanced modes,
mainstream Chinese-food coverage, follow-up questions, English documentation,
team name and member responsibilities. They requested additional tests and
retained final approval of the Canvas submission.

The automated checks were run by the coding assistant, not independently by every
team member. Evidence records distinguish deterministic tests, real PostgreSQL
rehearsal and live-provider observations. They do not establish clinical accuracy,
complete model reliability or independent human review of every generated line.

During development, live checks exposed recipe-correction extraction problems,
piece-count/gram confusion and gross/edible-weight ambiguity. Prompt/validation
changes and regression tests addressed observed cases; invalid outputs can still
fail. The implementation rejects unsupported or invalid structured results rather
than accepting model-generated nutrient totals. These are software validation
behaviors, not a claim that the team manually rejected every such output.

Independent team review and presentation rehearsal have not yet been recorded for
this milestone. Before submission/presentation, Junlang and Jiacheng should review
implementation choices, Yixing should rerun acceptance checks, and Zhou Ran should
review documentation and deployment readiness. Any completed human checks should
be added with their actual date and outcome. The team remains responsible for the
submitted work and for explaining its behavior and limitations.
