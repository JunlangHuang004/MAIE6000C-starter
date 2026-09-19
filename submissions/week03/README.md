# Week 3 Submission — Individual Readiness Lab

## Student information

- Name: Junlang Huang
- Student ID: 21343405
- Repository: https://github.com/JunlangHuang004/Maie-6000c-starter-Junlang-Huang
- Checkpoint tag: `w03-readiness`
- Commit SHA: TO_BE_ADDED

## 1. What I changed

I added an integration test for the API `/health/live` endpoint. The test verifies that the endpoint returns HTTP status code 200 and that the response status is `"ok"`.

## 2. Files touched

- `tests/integration/test_health.py`
- `submissions/week03/README.md`

## 3. How I verified it

- Rebuilt the API Docker image using `docker compose build api`.
- Ran `docker compose run --rm --no-deps api pytest -q tests/integration/test_health.py`.
- Confirmed that the integration test passed successfully (`1 passed`).

## 4. Known limitations or notes

This change only verifies the API liveness endpoint. It does not test the readiness endpoint or dependency availability.

## 5. AI Use Statement

ChatGPT was used to help interpret the lab instructions, explain Git and Docker commands, and assist with drafting the integration test and submission documentation. I ran the commands myself, reviewed the test behavior, observed the intentional failing test, corrected the expected value from `"okay"` to `"ok"`, and verified that the final test passed.
