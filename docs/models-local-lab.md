# Local model lab (optional provider experiments)

The merged application supports Qwen and HKUST GenAI as cloud extraction adapters.
Use [the integrated preview](integration.md) for the complete account, meal and
tracking workflow. This optional lab isolates provider experiments from that
preview. Its catalogue is the same **200 ingredients and 350 reference recipes**
retained from `nutrichat`.

The [2026-10-30 provider report](evidence/local-model-verification.md) records
successful HKUST checkpoints on the earlier account preview and failed application
acceptance for the tested Ollama models. Those historical results are not live
acceptance of the merged build. Ollama remains experimental; installation and a
valid JSON response do not establish reliable food extraction.

The model lab connects NutriChat to HKUST GenAI or a locally installed Ollama
model. Both adapters extract food identities and meal facts; the existing Python
engine calculates calories, protein, fat and carbohydrates from the project
catalogue. A model response is not itself a nutrition database.

This guide applies to the merged checkout. The commands below create a distinct
project and do not change the historical submission tag or an existing deployment. The standalone `compose.models.yaml` uses a separate Compose project,
database volume and image. The example configuration uses
[http://localhost:8007/app](http://localhost:8007/app), overriding the Compose default
of port 8004 to avoid the earlier lab.

Use synthetic or public meal descriptions for lab requests. Each student should
use their own HKUST key. Keep real keys in a private `.env` outside the repository,
and do not include them in screenshots, logs, GitHub or submissions. The examples
below contain placeholders only.

## Provider selection

| Setting | Behaviour |
| --- | --- |
| `LLM_PROVIDER=hkust` | HKUST GenAI with the student's API key |
| `LLM_PROVIDER=ollama` | Experimental local Ollama; no key needed, but application acceptance failed |
| `LLM_PROVIDER=heuristic` | The existing strict, six-food English demo parser; no network calls |
| `LLM_PROVIDER=demo` | Same offline parser as `heuristic` |
| `LLM_PROVIDER=qwen` | Existing Qwen adapter using `QWEN_*` and `DASHSCOPE_API_KEY` |
| Unset or blank `LLM_PROVIDER` | Preserve the existing `NUTRITION_PROVIDER` selection |

A non-empty `LLM_PROVIDER` overrides `NUTRITION_PROVIDER`. Keep the provider
consistent across the API, worker and AI service. The model lab Compose file does
this automatically; only its AI service receives the private provider `.env` and
API key. The API and worker receive the provider selector without the key.

## Prepare HKUST GenAI

Obtain your own key through the
[HKUST GenAI API service](https://itso.hkust.edu.hk/services/it-infrastructure/hkust-genai-api-service).
Create a private file such as `/absolute/path/hkust/.env`:

```dotenv
LLM_PROVIDER=hkust
LLM_BASE_URL=https://hkust.azure-api.net/hkust-genai/v1
LLM_MODEL=gemini-2.5-flash-lite
LLM_API_KEY=replace_with_your_own_hkust_key
LLM_API_KEY_HEADER=api-key
LLM_TIMEOUT_SECONDS=180
WORKER_REQUEST_TIMEOUT_SECONDS=210
MODEL_LAB_PORT=8007
```

The adapter appends `/chat/completions` and sends the key in the `api-key` header.
The base URL and model above are also its defaults when the corresponding values
are blank. Account access and quota still need a live check; configuration alone
does not prove either. Keep the worker timeout longer than the model timeout.

## Prepare Ollama on macOS

Install the native application from [Ollama](https://ollama.com/download/mac),
open it, then download and try the classroom model:

```sh
ollama --version
ollama pull llama3.2
ollama run llama3.2 "Reply briefly: what is 2 plus 2?"
```

After the model download, local inference does not need a cloud account or key.
Keep Ollama running while using this provider. A first request can take longer
because the model must load into memory.

Create a separate private file such as `/absolute/path/ollama/.env`:

```dotenv
LLM_PROVIDER=ollama
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_MODEL=llama3.2
LLM_API_KEY=
LLM_TIMEOUT_SECONDS=180
WORKER_REQUEST_TIMEOUT_SECONDS=210
MODEL_LAB_PORT=8007
```

Keep `llama3.2` installed for the classroom exercise. A smaller optional model for
local Chinese extraction experiments is
[`qwen2.5:1.5b`](https://ollama.com/library/qwen2.5:1.5b), whose model download is
about 986 MB:

```sh
ollama pull qwen2.5:1.5b
```

To try it, change only `LLM_MODEL=qwen2.5:1.5b` in the private Ollama file before
recreating the lab services. It remains a local Ollama model and does not use the
cloud Qwen account or its key. Its final application acceptance run failed; keep
it for experiments rather than a reliable replacement for the cloud model. A
smaller download does not guarantee lower total runtime memory or correct extraction. The
[verification record](evidence/local-model-verification.md) distinguishes the
classroom model check from the application tests.

Inside Docker Desktop, `localhost` refers to the container, so the lab uses
`host.docker.internal` to reach the Mac. The documented container-to-host path was
checked with Ollama bound to its default loopback interface; no LAN listener is
required for this setup. Other machines and Docker environments may need their
own connectivity check. Do not expose the unauthenticated local API publicly.
When running Python directly on the Mac, use `http://127.0.0.1:11434/v1` instead.

NutriChat translates this base URL to Ollama's native `/api/chat` endpoint to set
the context and output limits explicitly. Requests include a strict JSON schema
with the selected food IDs as an allowlist; the shared response validator still
checks the result. These constraints improve structural reliability, not factual
understanding. The local adapter uses a compact Chinese extraction prompt. It
sends no authentication header to
Ollama, including when an unrelated `LLM_API_KEY` happens to be present. See
[Ollama configuration](https://docs.ollama.com/faq) and
[Docker Desktop host networking](https://docs.docker.com/desktop/features/networking/networking-how-tos/).

## Start the isolated application

Run from the merged checkout. Use the same absolute private file path in both
places; the first supplies the AI service's environment and `--env-file` supplies
Compose's provider, port and timeout values:

```sh
MODEL_ENV_FILE=/absolute/path/hkust/.env \
docker compose -p nutrichat-integrated-model-lab \
  --env-file /absolute/path/hkust/.env -f compose.models.yaml up -d --build
```

For an explicitly experimental Ollama run, replace both paths with
`/absolute/path/ollama/.env`. This is a standalone Compose file; do not add
`compose.yaml`. Only the API's port is published, on
`127.0.0.1`. The AI service and database remain internal to the lab network.

Open [the local lab](http://localhost:8007/app), register a disposable local test
account, then sign in. This is the merged application's independent account system; existing accounts
from other Compose projects are not imported. Use `localhost` consistently in the
browser. See [account rules](accounts.md) for username and password requirements.

To switch providers, let active jobs finish, select the other private `.env` in
both command positions, and run the same `up -d --build` command. Compose recreates
services whose configuration changed. Keep the project name
`nutrichat-integrated-model-lab` to retain the lab's accounts and meals. A provider switch does
not recompute previous estimates.

## Check the complete flow

1. In Basic mode, submit a small synthetic meal such as `100克去壳水煮鸡蛋，熟重`.
   Wait for processing, then inspect the matched food, weight and assumptions.
2. Try Advanced mode with an omitted weight, for example `去壳水煮鸡蛋，熟重`.
   Answer the weight question and any other questions actually issued. Missing
   details may require clarification rather than immediately producing totals.
3. Correct the portion to `125` grams through the issued fields. Inspect the updated
   details and catalogue sources before confirming.
4. Confirm the completed estimate, reload, and check that the confirmed meal and
   values remain saved. These steps are also the acceptance target for experimental
   providers; do not assume an installed model can complete them.
5. Try a known food mixed with an unsupported description. The unsupported item
   must be shown and all totals must remain unavailable. Correct the identity or
   explicitly review actual ingredients in the structured ingredient form.

These are verification instructions, not a claim that a particular live model
has passed them. A responding health endpoint only confirms service readiness;
it does not establish model access or extraction accuracy. Live checks create
synthetic saved records, and HKUST requests consume the student's quota.

See [the dated verification record](evidence/local-model-verification.md) for
the historical observed results and the distinction between automated and live checks.

For automated adapter and persisted-flow checks without a real model key:

```sh
MODEL_ENV_FILE=/absolute/path/ollama/.env \
docker compose -p nutrichat-integrated-model-lab \
  --env-file /absolute/path/ollama/.env -f compose.models.yaml \
  run --rm --no-deps -e LLM_PROVIDER=heuristic api \
  pytest -q tests/unit/test_local_providers.py tests/integration/test_local_provider_flow.py
```

These tests replace the model HTTP boundary with synthetic responses. They test
the application contract but cannot establish live model quality. The ordinary
offline parser still expects supported English foods and explicit grams, such as
`100g egg`; `heuristic` does not provide the full Chinese extraction workflow.

## Limits and troubleshooting

- Ollama's small local model receives a bounded candidate catalogue selected from
  food names, aliases and English IDs in user messages. Matching recipe ingredients
  are included. Retrieval does not prove a food identity, and unfamiliar wording
  can remain unknown. HKUST and Qwen use a separately bounded shortlist of up to
  60 primary records and 120 total records including recipe ingredients; this is
  retrieval context, not permission to substitute another food.
- Local requests use an 8,192-token context and at most 1,536 output tokens, with a
  conservative prompt-size check. More than 32 candidates or an oversized dialogue
  produces a request to simplify the meal or start a new record instead of silently
  truncating instructions. Try fewer foods and shorter descriptions.
- The local model can misread names, preparation, portions or corrections. Review
  its extracted facts. Catalogue arithmetic does not guarantee that the selected
  food or reference recipe matches the meal actually eaten.
- The local mass safeguard clears weights when the entire user dialogue contains
  no mass evidence. It does not prove each item's weight provenance: another
  food's weight or an English unit word can count as possible evidence.
- All model adapters now pass through the same exact original-name guard. Reviewed
  names/aliases determine identity, even when the model suggests a different ID.
  Unmatched names and uncovered meal clauses block all totals. This is stricter
  than the earlier lab and can require users to restate unsupported wording.
- The earlier local-model run omitted foods and invented recipe/yield facts.
  The merged guard addresses identity substitution and uncovered meal clauses,
  but does not establish that every quantity or recipe fact is correct. Ollama
  has not been declared accepted on this merged build. Review extracted facts,
  reference assumptions and ingredient amounts before confirmation.
- Provider errors, invalid structured output and incomplete responses fail the
  request. The application does not replace a failed model call with invented
  nutrients or silently switch to another model. Basic mode's labelled reference
  assumptions still come from the existing deterministic meal engine.
- For connection failures, verify that Ollama is open and `ollama list` includes
  `llama3.2`. Check the host address from the AI container. For HKUST, check your key,
  endpoint, model access and quota privately.
- If a local request times out, wait for model loading, reduce the meal size and
  retry. `LLM_TIMEOUT_SECONDS` defaults to 120 and accepts values up to 600; always
  keep `WORKER_REQUEST_TIMEOUT_SECONDS` higher. A queued record also needs a healthy
  worker. See [operations](operations.md) for the existing job recovery limitations.

Stop this lab using the currently selected private file, retaining its database:

```sh
MODEL_ENV_FILE=/absolute/path/hkust/.env \
docker compose -p nutrichat-integrated-model-lab \
  --env-file /absolute/path/hkust/.env -f compose.models.yaml down
```

Do not add `-v` for a normal stop or provider switch: it deletes the lab database.
