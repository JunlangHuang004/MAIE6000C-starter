# Midterm runnable demo and rehearsal

For the TA's self-guided review, begin with [the dedicated demo folder](../../demo/README.md).
Its primary product demo shows Chinese meal estimation with 200 ingredients and
350 reference recipes on port 8003. Use the setup guide's `w07-midterm` checkout
for the submitted version. Once Qwen is configured on the server, users
open `/app` directly without registration or login. The English walkthrough covers
Basic/Advanced modes, clarification, correction, confirmation and reload. The
header’s **中文 / English** buttons switch interface language while preserving
entered values and the current record.

Unsupported foods must remain unresolved rather than receive a different dish's
estimate. The structured ingredient builder accepts explicitly reviewed food
records and quantities for a custom meal item; see the
[ingredient guide](../../docs/ingredient-recipes.md). The 162 newly added catalogue
entries prioritize Chinese, with Chinese fallback where English translations are
absent.

A separate no-key check on port 8002 provides repeatable HTTP/database/worker
evidence. Its small English fixture catalogue is not the full product demo.
A screen recording or in-person presentation is not required. The commands below
retain the earlier terminal-only worker rehearsal for deeper inspection; that
stack intentionally has no host ports. These instructions concern the meal
estimation and review workflow on `nutrichat`.

## Prepare the isolated worker demonstration

From the repository root, with Docker Compose and host Python 3 installed:

```sh
docker compose -p nutrichat-week07 --env-file .env.example -f compose.yaml -f compose.week06.yaml build api ai worker
docker compose -p nutrichat-week07 --env-file .env.example -f compose.yaml -f compose.week06.yaml up -d --wait db ai api
python3 scripts/rehearse_midterm.py --output /tmp/nutrichat-week07-rehearsal.json
```

The reused overlay explicitly selects the offline demo provider, clears model
credentials, removes host ports and gives this project its own database volume.
It does not stop the regular local or public application. The rehearsal creates
one synthetic meal. It stops this isolated worker, checks saved queued state,
starts the worker, waits up to 60 seconds, verifies saved nutrition, confirms,
reloads and checks that an edit is rejected. It captures actual HTTP/DB/log evidence.

For a fresh rehearsal, use `/tmp/` as above rather than overwriting the committed
historical evidence. Re-running adds another synthetic meal; it is not idempotent.

## Show the five required boundaries live

Use the same Compose prefix for all commands. You can run the script once as a
preflight and then walk through the following steps in the terminal.

1. **Input:** stop the isolated worker, then create a meal from inside the API container:

```sh
docker compose -p nutrichat-week07 --env-file .env.example -f compose.yaml -f compose.week06.yaml stop worker
docker compose -p nutrichat-week07 --env-file .env.example -f compose.yaml -f compose.week06.yaml exec -T api python -c 'import httpx; r=httpx.post("http://api:8000/analyses",json={"food_text":"100g egg"}); print(r.status_code); print(r.text)'
```

2. **Persisted input:** copy the returned job ID into this query and show `pending`,
   attempts 0, `queued` and null calories. Replace `JOB_ID` with that numeric ID.

```sh
docker compose -p nutrichat-week07 --env-file .env.example -f compose.yaml -f compose.week06.yaml exec -T db psql -U postgres -d maie6000c -c 'SELECT j.id,j.status,j.attempts,a.id AS analysis_id,a.status AS meal_status,a.calories FROM jobs j JOIN analyses a ON a.id=j.analysis_id WHERE j.id=JOB_ID;'
```

3. **Async work:** start the worker and show the matching job ID in the logs:

```sh
docker compose -p nutrichat-week07 --env-file .env.example -f compose.yaml -f compose.week06.yaml up -d --no-build worker
docker compose -p nutrichat-week07 --env-file .env.example -f compose.yaml -f compose.week06.yaml logs --no-color --tail=30 worker
```

4. **Persisted output:** repeat the SQL query; read `GET /analyses/ANALYSIS_ID`
   using the returned analysis ID. The demo catalogue yields 155 kcal, 13 g protein,
   11 g fat and 1.1 g carbohydrates. These are legacy fixture values, not the Qwen
   USDA mapping. Show the rehearsal's `confirmed`, `reloaded`, `after_confirmation`
   and `locked_edit` evidence, or repeat confirmation through the API with its
   current revision.

5. **Operational signal:** show readiness and the claim/completion timestamps:

```sh
docker compose -p nutrichat-week07 --env-file .env.example -f compose.yaml -f compose.week06.yaml exec -T api python -c 'import httpx; r=httpx.get("http://api:8000/health/ready"); print(r.status_code,r.text)'
```

## Chinese user experience, when Qwen is configured

On the regular Qwen stack, open `/app`, select Basic and enter
`十个白菜猪肉饺子，另外200克青椒牛肉熟重。` Review the displayed assumptions,
switch to Advanced, answer the generated questions and edit recipe/oil/yield
values. Review, confirm and reload. Do not say that unanswered questions are a failure.

For an automated, quota-consuming check that creates synthetic records:

```sh
docker compose exec -T api python scripts/check_expanded_dialogue.py --base-url http://api:8000 --live
```

If the provider fails, show the error state and explain the dependency. Use the
isolated worker demonstration to show the engineering contract, clearly labelled
as the offline provider. Do not claim it proves Chinese extraction. The public ECS
is an older deployment and should not be used to represent this tagged release.

## Finish

```sh
docker compose -p nutrichat-week07 --env-file .env.example -f compose.yaml -f compose.week06.yaml down
```

Do not add `-v`: the synthetic database remains available for inspection. Keep
team-rehearsal observations separate from the assistant-run evidence record.
