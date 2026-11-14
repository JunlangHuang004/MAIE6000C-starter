# Backend revision-validation fix — 2026-11-14

Applied only in `/Users/jadenhuang/Documents/Codex/2026-10-16/d/worktrees/nutrichat-test`, based on `254bebfc8fea07830d261adf2def54bc4cb217ed`. The separate baseline QA checkout remains unchanged. No commit or push was performed.

## Changes

- `services/common/schemas.py`: meal correction, mode switch, reply, and ingredient-recipe revision fields now require strict integers from 1 through 2147483646, matching the existing confirmation contract. Oversized integers and coercible values are rejected before database access.
- `services/api/app/main.py`: all `/analyses/{id}` validation failures use the existing safe error format, excluding rejected input values. NaN/Infinity revisions now produce 422 instead of crashing response serialization.
- `tests/integration/test_analysis_validation.py` (new): 55 request-level regression cases spanning all five mutation routes and 11 invalid revision inputs. Each case requires a safe 422 containing only the revision-field error and verifies that the meal and queued jobs remain unchanged.

No food data, formulas, authentication behavior, frontend source, or unrelated files were changed by this subagent. Other agents' frontend edits were present and were left intact.

## Verification

The existing fresh API image supplied dependencies; the development checkout was mounted read-only over `/app`, so these tests ran the modified source without rebuilding or changing the baseline image.

```text
pytest -q -o cache_dir=/tmp/pytest-cache
  tests/integration/test_analysis_validation.py
  tests/integration/test_analysis_review.py
  tests/integration/test_meal_dialogue.py
  tests/integration/test_ingredient_recipe_api.py
  tests/integration/test_daily_tracking.py

197 passed, 2 dependency deprecation warnings in 72.06s
```

The test environment set `LLM_PROVIDER=heuristic` and `NUTRITION_PROVIDER=demo`; no model or network service was used. Existing valid correction, dialogue, mode switch, ingredient replacement, confirmation, and diary flows passed alongside the new invalid-input tests.

`ruff check --no-cache services/common/schemas.py services/api/app/main.py tests/integration/test_analysis_validation.py`: all checks passed. `git diff --check`: passed.

The original finding also has PostgreSQL HTTP evidence supplied by the parent audit in `postgres-invalid-revisions.json`. The parent owns the final rebuilt PostgreSQL HTTP acceptance check after these modifications and the final combined frontend/backend checks.
