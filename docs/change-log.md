# NutriChat change log

## 2026-10-17 — Documentation alignment

- Rewrite the README, current API contract, architecture and operations guide to match the two-mode clarification workflow.
- Explain Qwen extraction versus Python nutrition calculation, disabled deep-thinking mode and the absence of model training.
- Document mode switching, revision conflicts, confirmation locking, recipe assumptions and shared-account limitations.
- Update cloud timeouts, deployment verification, backup and upgrade guidance; distinguish mocked tests from live-provider checks.
- Add ADR 0002 for source-backed nutrition and two estimation modes.
- Preserve the original starter notes and course API evidence in `docs/history/` without changing historical completion claims.
- Use English for maintained documentation and GitHub change descriptions; retain Chinese meal examples for the supported input workflow.
- This follow-up changes documentation only. Validate local links, referenced paths and Git whitespace checks; do not repeat unchanged application tests.

## 2026-10-17 — Chinese catalogue, two estimation modes and clarification dialogue

### User-facing changes

- Add basic mode for quick estimates with visible reference portions, recipes and oil assumptions, including bowl/piece/serving counts.
- Add advanced mode for edible grams, raw/cooked weight, preparation and consumed oil, with editable recipe ingredient quantities and finished batch yield.
- Allow switching modes within an unconfirmed record. Basic-mode defaults are never stored as user-supplied facts.
- Use Qwen to interpret Chinese descriptions, follow-up details and corrections; calculate nutrients through catalogue lookup and Python arithmetic.
- Include 116 USDA SR Legacy ingredient records with CC0 provenance, FDC IDs, weight states and Chinese aliases.
- Include 50 project-authored Chinese reference recipes. These are illustrative formulations, not measured or standardized recipes; nutrients derive from USDA ingredients.
- Persist dialogue, questions, recipes and calculation evidence so reload restores the workflow. Require review before confirmation.
- Ask about unmatched foods and contradictory raw/cooked or preparation facts instead of fabricating nutrient results.

### Earlier work included in the feature commit

- Mainland China Qwen configuration and connection checks, asynchronous analysis, correction/recalculation and revision conflict protection.
- Chinese application UI, HTML login and signed session cookies, with private environment files for credentials.
- ECS / Docker Compose configuration, Nginx HTTPS reverse proxy and certificate renewal script.
- Legacy demo mode without credentials, retaining strict English gram-based input for offline tests.

### Database and operations

- Migration 0003 adds revision, confirmation time and interpreted meal fields.
- Migration 0004 adds dialogue, structured drafts, questions, calculation evidence and user-facing errors.
- Migration 0005 persists basic/advanced mode.
- New fields have defaults for older records; existing meals are not deleted.
- See [nutrition data](nutrition-data.md) for provenance, reproducible import and limitations.
- API keys, login passwords, server environment files, certificates and database backups remain outside Git.

### Validation

- 59 unit/integration tests passed, together with Ruff and the page JavaScript syntax check.
- Real Qwen requests verified basic portion assumptions and advanced clarification.
- Local browser checks covered recipe editing, mode switching, result display and restoration after reload.
- The real-Qwen flow passed on the Hong Kong ECS deployment: basic estimate → advanced clarification → recipe editing → natural-language correction → confirmation and persistence. The synthetic meal changed from a reference 365.2 kcal to 264.7 kcal after supplied details.
- Database backups and previous images were retained before updating the public service; existing login credentials and API keys were preserved.
