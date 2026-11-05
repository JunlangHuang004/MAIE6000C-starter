# Chinese meal evaluation

`evaluation/chinese_meals.json` is a fixed, synthetic regression corpus. Its cases
cover explicit grams, piece counts, a reference recipe, gross bone weight and an
unsupported food. Expected food IDs and quantities test Qwen extraction; the two
explicit calorie references test arithmetic against this repository's catalogue.
They are **not measured real-meal calorie truth**. A passing run does not establish
that a restaurant or home-cooked dish contains the reported calories.

Validate the corpus without an API key or saved records:

```sh
docker compose run --rm --no-deps api python scripts/evaluate_chinese_meals.py
```

For an optional live run, start a private Qwen-enabled stack and use an existing
dedicated test account. The command refuses a demo-mode stack. It consumes model
quota and creates seven unconfirmed synthetic meal records in that account; use a
disposable database or clear those records through an operator procedure later.
Supply credentials privately, as described in [account checks](accounts.md):

```sh
docker compose exec -T -e NUTRICHAT_CHECK_USERNAME -e NUTRICHAT_CHECK_PASSWORD api \
  python scripts/evaluate_chinese_meals.py --live --base-url http://api:8000 \
  --output /tmp/chinese-meal-evaluation.json
```

The JSON report contains case IDs, analysis IDs, observed food IDs and quantities,
status, calories, catalogue-reference error where applicable, duration, outcome and
concrete mismatches. It does not contain credentials or meal
descriptions. Copy the report out of the container if you want to preserve it;
`docker compose exec` writes `/tmp` inside the container. Use a host-mounted path
when running the script on the host. The command exits nonzero if any case fails.

Outcome meanings:

| Outcome | Meaning |
| --- | --- |
| `pass` | Fixed extraction/status and any catalogue-calorie expectations matched |
| `mismatch` | Completed response disagreed with an expected food, quantity, status or calorie value |
| `processing_failure` | Worker marked the analysis failed; inspect job and service logs |
| `timeout` | Analysis remained queued past the case deadline; inspect worker/job state |
| `transport_or_response_failure` | HTTP call or response parsing failed |
| `invalid_response` | API returned an unexpected state or draft shape |

For a real-world accuracy study, independently weigh edible ingredients and oil,
record the cooked yield and consumed portion, document each food-data source, and
compare the calculated reference with NutriChat's estimate. Keep those measured
cases separate from this synthetic corpus. Report sample size, absolute kcal error,
food-identification failures and cases where the system asked instead of guessing.
Do not label an unmeasured menu calorie or a project-authored recipe as ground truth.
