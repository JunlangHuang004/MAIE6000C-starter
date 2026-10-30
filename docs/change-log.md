# NutriChat change log

## 2026-10-31 — Chinese/English interface and current demo documentation

- Add accessible Chinese/English header controls, a remembered language preference,
  translated questions/status/evidence and English display names for 138 ingredients
  and 250 reference recipes. Preserve current records and unsent form values when switching.
- Serve three allowlisted JavaScript assets with correct MIME/cache behavior;
  include the assets in the Python package. Nutrient data and model matching are unchanged.
- Add 15 frontend regression tests and nine API asset checks. Pass 417 Python tests
  (two smoke tests deselected), all 15 frontend tests and whole-repository Ruff.
- Verify the running Qwen recipe flow: switch languages while queued and editing,
  submit preserved oil/yield values, confirm and reload the same record and totals.
- Enable the existing CI workflow for `nutrichat` pushes and add frontend checks.
  Local success does not by itself establish a successful GitHub Actions run.
- Refresh architecture, operations, TA instructions, scope/risks and concise AI
  assistance disclosure. Separate historical checkpoint evidence from current checks.
- Record 21 English-input Qwen probes: 19 passed, with one failed analysis and
  one incorrect gai-lan/broccoli match. Translation does not fix these recognition limits.
- Rebuild the isolated offline stack and pass its HTTP/PostgreSQL/worker check,
  including correction, confirmation, reload, locked edits and correlated logs;
  both live offline smoke tests also passed.
- See [UI verification](evidence/ui-language-verification.md) and
  [English-input evaluation](evidence/qwen-english-verification.md).

## 2026-10-28 — Self-guided TA demo on the nutrichat branch

- Synchronize operations and the Week 7 status document with the new demo entry
  points, dated test results and observed failures. Distinguish the preserved
  checkpoint tag from later branch-only materials and avoid attributing old CI
  results to new commits.
- Add a dedicated `demo/` entry point with English setup, a six-step screenshot
  guide, Chinese/English control labels and a detailed product/architecture
  walkthrough. Lead with the 138-ingredient/250-recipe Chinese workflow.
- Document direct local access without registration or login. Keep independent
  accounts, personalized targets and trends outside this milestone scope.
- Add isolated local Qwen and offline Compose overlays, plus a key-free launcher
  that verifies HTTP, PostgreSQL, worker logs, correction and durable confirmation.
- Add opt-in varied-food/gram-weight checks and synthetic evidence. No API keys
  or private environment files are included.
- Pass 408 unit/integration tests and Ruff. The 17-case live Qwen matrix passed
  14 checks; 0 g, negative and over-limit weights returned generic failed states
  without totals, leaving their user-facing validation incomplete.
- Observe one failed initial expanded-dialogue attempt and one complete successful
  rerun. Verify the browser's Basic → Advanced → correction → confirmation/reload
  sequence and database retention after stopping/restarting the offline demo.
- Keep application services, migrations, dependencies and base Compose unchanged;
  add demo scripts to the image for their tests. Preserve existing branch/tag
  references and public deployment. See [verification](../demo/VERIFICATION.md)
  for evidence and limits; no new CI or Canvas submission is claimed.

## 2026-10-27 — Midterm scope clarification

- Keep the AI Use Statement brief and record the team's rejection of image-based
  nutrition estimation in favor of the current meal-description workflow.
- Record monthly calorie-intake trends and personalized energy/macronutrient
  estimates as possible future extensions, not implemented or committed features.
- Documentation-only update; existing test evidence retains its original scope.

## 2026-10-27 — Week 7 midterm checkpoint

- Add the milestone README, confirmed team responsibilities, live demo guide,
  realistic Week 7–13 priorities and a truthful AI Use Statement.
- Reproduce and fix the pytest console-entry script-import failure. Keep existing
  workflow triggers; the original `main` CI validates the commit mirrored to the fork.
- Add a host rehearsal script and fresh synthetic HTTP/PostgreSQL/worker evidence
  for queued input, durable output, confirmation, reload and locked corrections.
- Pass 359 unit/integration tests, whole-repository Ruff and two isolated-stack
  smoke tests. Complete the expanded real-Qwen dialogue script in one run; record
  provider validation separately from deterministic checks and retain reliability limits.
- Refresh README, architecture, operations and ownership notes. Public ECS remains
  an older deployment; no public upgrade or Canvas submission is included.
- See [Week 7 verification](evidence/week07-verification.md) for commands and evidence.

## 2026-10-19 — 250 home-style reference dishes

- Expand the catalogue from 50 to 250 editable recipes and from 116 to 138 USDA SR Legacy ingredients.
- Keep one reference formulation per dish, group alternative names under one ID and disclose simplified methods. Amounts and cooked yields remain project-authored assumptions, not imported measurements.
- Add whole beef, boneless edible rib meat, skin-on chicken and missing pantry ingredients with original FDC IDs and CC0 provenance. Preserve the existing 116 ingredient records.
- Correct the two existing whole-beef recipes that previously used ground beef, while retaining their dish IDs and historical saved results.
- Distinguish reference piece and serving weights for dumplings, wontons, buns and selected other foods. Preserve explicit grams and ask for actual details in advanced mode.
- Preserve explicit ingredient exclusions and whole-batch oil corrections in structured recipe fields. For explicit gross bone/shell weights, basic mode shows a coarse 60% edible-weight assumption; advanced mode asks for edible grams without carrying the assumption into user facts.
- Guard against copying a piece count into an unsupported gram value, and constrain model output to concise structured facts. Live checks exposed both missing recipe corrections and a count-as-weight error.
- Reject invalid catalogue references, duplicate IDs/aliases and invalid yields or portions during import. Exercise all 250 recipes through basic estimation and advanced approval.
- Add an English coverage policy and a complete dish index. No model retraining or database migration is required.

### Validation

- Pass 359 unit/integration tests and Ruff. Exercise every recipe in both calculation modes, plus eight category-level API dialogue flows; these automated tests do not measure Qwen extraction accuracy.
- Regenerate the runtime catalogue from the cached official USDA archive and verify byte-identical output. Confirm that the original 116 ingredient records remain unchanged.
- Verify real Qwen extraction and the local API/worker/PostgreSQL flow for new dishes, piece weights, mode switching, recipe edits, natural-language corrections, confirmation, reload and locking.
- Separately pass the real-provider gross-weight flow after the prompt correction: retain 200g gross weight in the draft, calculate a labelled 120g edible-weight estimate in basic mode, then request net grams without totals in advanced mode. The full live script did not complete without interruption across these checks; successful subflows and intermittent failures are reported separately.
- Earlier live runs exposed missing structured recipe corrections, a piece-count/gram mix-up and confusion between gross weight and weight state; add prompt guidance and a narrow explicit-weight guard with regression tests. Correct the live test's assumption that every recipe contains the same oil ingredient.
- Live calls also intermittently returned invalid provider data and were rejected without nutrition totals. A successful synthetic flow is not a guarantee of provider reliability; no automatic retry or recovery was added.
- Perform the validation above on local service images. Public ECS deployment is separate from this source update.

## 2026-10-17 — Week 6 worker lifecycle evidence and test plan

- Extend architecture documentation with the worker sequence, state ownership, service boundaries, timeout policy and Week 7 demo/test plan.
- Add an Activities A–G workflow guide, actual HTTP/PostgreSQL/log evidence and verification notes.
- Add six lifecycle test cases covering claim metadata, success, timeout, HTTP errors, malformed results and duplicate POST behavior.
- Add an isolated demo-only Compose overlay for reproducing the lab without stopping existing application services or using model credentials.
- Verify 65 unit/integration tests, two isolated-stack smoke tests and Ruff. Document SQLite/concurrency limits and unimplemented retry/recovery/idempotency behavior.
- Add README and operations links. Team role assignments and the AI Use Statement remain pending; no AI Use Statement file is included in this update.


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
