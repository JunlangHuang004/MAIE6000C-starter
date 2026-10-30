# Interface language verification — 2026-10-31

Scope: Chinese/English display switching in the `nutrichat` meal application.
The Qwen extraction prompt, food IDs, nutrition catalogue and calculation engine
were not changed. English display names are not new model-matching aliases.

## Automated checks

- 15 frontend DOM tests passed using Node and jsdom 26.1.0. The tests cover saved
  language, unavailable browser storage, static and dynamic text, catalogue search,
  all 388 English names and 250 recipe methods, raw/cooked and gai-lan/broccoli
  distinctions, form values and checkboxes, unchanged record IDs/revisions/totals,
  no requests or extra polling on language change, queued and confirmed states,
  server errors and safe rendering of untrusted text.
- 417 Python tests passed; two smoke tests were deselected and two dependency
  deprecation warnings were reported. This includes nine new UI asset tests for
  allowed files, JavaScript content type, cache behavior and traversal rejection.
  This run used an isolated container with networking disabled and empty keys.
- `ruff check --no-cache .` passed.
- A clean `npm ci --prefix tests/frontend` installation and the documented
  `npm test --prefix tests/frontend` entry point passed all 15 frontend tests.

## Browser and running-application check

The local Qwen demo on port 8003 served all three JavaScript assets with hashes
matching the checkout. The API container was healthy. Other application stacks
and the public deployment were not updated.

An existing confirmed record retained its ID, revision and 312.7 kcal total when
the UI changed from Chinese to English. A separate synthetic meal then exercised:

1. English input: `200g of the Chinese dish tomato-and-egg stir-fry, cooked edible weight.`
2. Language switching while analysis was queued, followed by an English recipe form.
3. Editing whole-batch oil from 15 g to 5 g and finished batch weight from 400 g
   to 420 g, accepting the recipe and entering an unsent reply.
4. Switching to Chinese and back: both edited values, the acceptance checkbox and
   the unsent reply remained intact. The temporary reply was cleared before submission.
5. Submitting the preserved recipe values: 158.1 kcal, 10.2 g protein, 9.5 g fat
   and 8.5 g carbohydrates for the 200 g portion.
6. Confirming and reloading: English remained selected and the same confirmed
   record, revision 3 and totals were restored. This flow made one live extraction
   request; structured recipe answers reused the saved draft.

The [English interface screenshot](../../demo/images/07-english-interface.png)
shows the actual running page. This is a functional display check, not evidence
that all model interpretations or real-meal nutrition estimates are accurate.
User descriptions and free-form model notes retain their original language.

## Fresh offline integration check

After rebuilding the isolated `nutrichat-demo` stack from this checkout, the
31 October `python3 demo/run.py check` run passed. The
[raw synthetic evidence](../../demo/evidence/offline-check-2026-10-31.json) records
queued PostgreSQL state before worker execution, two completed jobs, an internal
AI request counter increase of two, 155 → 310 kcal correction, confirmation,
identical reload and HTTP 409 for a locked edit. The source was `dab4a0a` with
only documentation/evidence changes uncommitted during the check.
This provider uses legacy fixture values and does not validate Qwen extraction.

The two live smoke tests also passed separately on this freshly built offline
stack (`2 passed, 2 warnings in 4.79s`):

```sh
docker compose -p nutrichat-demo --env-file .env.example -f compose.yaml -f demo/compose.demo.yaml exec -T -e SMOKE_BASE_URL=http://api:8000 api pytest tests/smoke -q
```
