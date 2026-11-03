# HKUST GenAI setup for the merged application

The `test` branch combines accounts, personal references and
tracking with the `nutrichat` catalogue: **200 ingredients and 350 reference
recipes**. HKUST supplies meal-fact extraction. Python calculates nutrients from
that catalogue; profiles and daily records do not require model calls.

Use the [integration guide](integration.md) for the current verification record.
The live HKUST checks in [the earlier model report](evidence/local-model-verification.md)
were performed on 2026-10-30 against the earlier account preview. They are
historical evidence, not proof that the merged build or every description passes.
Ollama remains experimental; its previously tested models failed full application
acceptance.

## Configure your private model access

From the merged checkout, create `.env` only if it does not already exist:

```sh
test -f .env || cp .env.example .env
```

Set these values in that private file, preserving unrelated settings:

```dotenv
LLM_PROVIDER=hkust
LLM_BASE_URL=https://hkust.azure-api.net/hkust-genai/v1
LLM_MODEL=gemini-2.5-flash-lite
LLM_API_KEY=replace_with_your_own_hkust_key
LLM_API_KEY_HEADER=api-key
LLM_TIMEOUT_SECONDS=180
WORKER_REQUEST_TIMEOUT_SECONDS=210
NUTRICHAT_PORT=8005
```

Use an authorized key and keep it out of Git, screenshots, logs and submissions.
A healthy service does not verify model access, remaining quota or extraction
quality. The adapter requests JSON-object output and includes the validated extraction
schema in its prompt. The school gateway rejected native `json_schema` response
format during this integration check, so that format is not enabled. Exact
localized cooking labels may normalize to their equivalent preparation enum;
invalid weight states are never guessed. Strict schema and food-identity checks
remain after generation.

The API key is sent in the `api-key` header; the adapter appends
`/chat/completions` to the configured base URL.

## Start the isolated merged preview

```sh
docker compose -p nutrichat-integrated --env-file .env \
  -f compose.yaml -f compose.integrated.yaml up -d --build
```

Open [NutriChat](http://localhost:8005/app), register a local account and sign in.
The `nutrichat-integrated` project uses its own PostgreSQL volume; it does not
replace the existing account preview, Qwen demo or public ECS data. A new project
starts with no accounts or saved meals. The catalogue comes from the merged
source files, not from copying or combining users' databases.

Only the AI service loads the private model file. The API and worker receive the
provider selector without the key. The API binds to loopback; database and AI
ports stay internal. Keep the worker timeout longer than the model timeout.

To keep the model file outside this checkout, use its same absolute path for
both configuration inputs:

```sh
NUTRICHAT_MODEL_ENV_FILE=/absolute/path/hkust/.env \
docker compose -p nutrichat-integrated --env-file /absolute/path/hkust/.env \
  -f compose.yaml -f compose.integrated.yaml up -d --build
```

Use one consistent project name for that preview. A different project name creates
separate accounts and saved records; a different port alone does not isolate data.
Switching providers does not recompute previously saved estimates.

## Verify with synthetic meals

1. Submit `米饭100克熟重，水煮鸡蛋50克熟重` in Basic mode. Review both foods,
   their portions, assumptions and sources before confirming.
2. Submit `去壳水煮鸡蛋，熟重` in Advanced mode. Supply 125 g in the issued
   weight field, review the result and confirm it with a meal date.
3. Submit `豉油鸡200克熟重` in Basic mode. Check that it uses the soy-chicken
   record, not another dish selected by the model.
4. Submit `米饭100克，火星豉油鸡200克`. The unsupported item must remain visible
   and all totals must stay unavailable. Correct the name or explicitly provide
   actual catalogue ingredients and their amounts in the ingredient form.
5. In Advanced mode, review a reference recipe, change its oil and finished batch
   weight, and confirm the reviewed recipe. Check the eaten portion separately.
6. Confirm and reload a completed meal. Check the daily total, a saved weight
   measurement and the 30-day trend. Sign in as a different account to check that
   the first account's meals and profile are private.

These are acceptance steps, not claims of universal accuracy. Live calls consume
HKUST quota. The exact-name guard can request a restatement of unfamiliar wording;
unknown foods are never replaced with a related catalogue entry. Model output
cannot authorize the custom ingredient recipe, which requires explicit user review.

## Run without model access

For a separate no-key demo, follow [the integration guide](integration.md). To
switch this same preview to the offline parser while preserving its volume:

```sh
LLM_PROVIDER=heuristic NUTRICHAT_MODEL_ENV_FILE=.env.example \
docker compose -p nutrichat-integrated --env-file .env.example \
  -f compose.yaml -f compose.integrated.yaml up -d --build
```

The offline parser accepts six legacy English foods and explicit grams, such as
`100g egg`. It does not provide Chinese dialogue. Use the full-description
replacement control to correct an offline meal; it does not interpret chat replies.
To return to HKUST, run the private-configuration startup command again.

Let active jobs finish before switching or stopping. Use the selected Compose
files with `down` for a normal stop. Do not add `-v`: it deletes that project's
PostgreSQL volume, including accounts, profiles and daily records.
