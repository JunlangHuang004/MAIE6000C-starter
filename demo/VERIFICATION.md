# NutriChat demo verification — 28 October 2026

The Chinese workflow is runnable, with the reliability limitations below. This
record does **not** claim that every live request succeeds or that the estimates
are measured nutritional values.

## Version and environment

- Branch: `nutrichat`, based on `93ad2074226e8e7c7dcd3df058605f8a233dca35`.
- These checks ran with the demo documentation/scripts still uncommitted. The
  offline JSON records that base commit and `dirty: true`; it is not evidence of
  a clean checkout of the later documentation commit.
- Application services, migrations, dependencies and base Compose configuration
  were unchanged. The demo adds isolated Compose overlays, launch/check scripts,
  tests, documentation and screenshots. No `test` account or tracking features
  were included.
- Docker application runtime: Python 3.11. Localhost port 8003 used the real
  configured Qwen provider; port 8002 used the separate offline fixture.
- Both local apps opened directly without registration/login. The `test` app on
  port 8001 and the public ECS deployment were not used as proof of this version.
- All test meals were synthetic. Model credentials are excluded from Git.

## Browser workflow

The [illustrated guide](SCREENSHOT_GUIDE.md) shows the actual Chinese UI. The
workflow was exercised twice with the same kind of meal:

1. Basic input: `一份番茄炒蛋，两个水煮鸡蛋`.
2. Reference portions: 200 g tomato and scrambled eggs plus 100 g edible boiled
   eggs; 365.2 kcal, 23.3 g protein, 25.5 g fat and 10.0 g carbohydrate.
3. Switch to Advanced: required questions appeared and nutrient totals were
   withheld. Supply 200 g / 100 g cooked edible weights and approve the shown
   whole-batch recipe: 300 g tomato, 150 g raw egg, 15 g oil, 5 g sugar, 2 g salt,
   and 400 g finished yield.
4. Correct the consumed dish portion to 150 g in conversation; retain the eggs
   at 100 g, and approve the recipe again if requested.
5. Corrected result: 312.7 kcal, 20.6 g protein, 21.8 g fat and 7.8 g carbohydrate.
6. Confirm and reload: the record ID, confirmed state and totals persisted;
   correction/mode-switch controls were no longer available.

These figures describe the accepted synthetic recipe, not a universal calorie
value for a named dish. Questions and interpretation wording can vary.

## Varied foods and gram weights: 14 of 17 checks passed

Run on the real Qwen stack, with **no automatic retries**:

```sh
python3 demo/check_food_matrix.py --base-url http://localhost:8003 --live
```

This uses model quota and creates 17 synthetic records. It saves a fresh report
to ignored `demo/output/food-matrix.json` and exits nonzero if any check fails.
The [checked-in report](evidence/food-matrix.json) contains all observed responses,
IDs and assertions. The final stricter assertions were applied to the same saved
responses without extra Qwen calls; the report records that revalidation.

| Input / condition | Observed result | Check |
| --- | --- | --- |
| Cooked rice, 50 / 100 / 200 g | 65 / 130 / 260 kcal; all four nutrients proportional within rounding | Passed |
| Roasted skinless chicken breast, 100 g | 165 kcal | Passed |
| Shelled boiled eggs, 100 g | 155 kcal | Passed |
| Boiled broccoli, 150 g | 52.5 kcal | Passed |
| Rice 100 g + boiled eggs 100 g + broccoli 150 g | 337.5 kcal | Passed |
| Tomato and scrambled eggs, 200 g | 210.2 kcal using the reference recipe | Passed |
| Mapo tofu, 180 g | 185.7 kcal using the reference recipe | Passed |
| Kung pao chicken, 250 g | 417.6 kcal using the reference recipe | Passed |
| Ten cabbage-pork dumplings, grams unknown | Labelled 200 g reference portion; 407.2 kcal | Passed |
| Rice without weight, Basic | Labelled 150 g default; 195 kcal; draft did not invent user-supplied grams | Passed |
| Rice without weight, Advanced | Asked for grams; no totals | Passed |
| Unsupported fictional food | Asked the user to identify the food; no totals | Passed |
| Rice with 0 g, -100 g or 10001 g | Failed state and null totals, but only a generic service-error message | **3 checks failed** |

For successful numeric cases, assertions checked food IDs, explicit gram values,
finite nonnegative nutrients, per-food sums and independent arithmetic from the
catalogue. This is a small live sample; it is not a live test of all 250 recipes.
The three invalid-weight cases did not display fabricated totals, but their
generic errors do not establish useful, input-specific validation. Improving
those messages/clarification is a remaining product issue.

## Longer Chinese conversation: one failed attempt, one successful rerun

```sh
docker compose -p nutrichat-qwen-demo --env-file .env -f compose.yaml -f demo/compose.qwen.yaml exec -T api python scripts/check_expanded_dialogue.py --base-url http://api:8000 --live
```

The first attempt failed on the initial cabbage-pork dumpling / green-pepper beef
meal: the upstream request returned HTTP 200, but the internal AI request returned
502 and the application showed a generic failure without totals. It was not a
credential rejection. One deliberate rerun passed the entire script:

- Piece-to-reference-weight handling and explicit cooked grams.
- Basic → Advanced, withheld totals, and rejection of premature confirmation.
- Recipe oil editing, a conversation correction to 160 g dumplings, and batch
  yield updates for the beef dish.
- Confirmation, reload and rejection of subsequent mode changes.
- Explicit gross bone weight: labelled 60% edible-weight assumption in Basic;
  Advanced asked for edible grams without retaining that assumption as a fact.

The failed first attempt is part of the evidence. There is no automatic retry or
worker crash recovery in this branch; model extraction remains a reliability
limit even when deterministic tests pass.

## Offline integration and durable storage

`python3 demo/run.py check` passed using real local HTTP, PostgreSQL, a background
worker and the internal AI HTTP boundary. See
[the synthetic report](evidence/offline-check.json).

- Worker paused: the database contained a queued meal, pending job, zero attempts
  and null totals before processing.
- Worker resumed: `100g egg` produced 155 kcal; matching job logs and timestamps
  showed completion and the AI request counter increased.
- PATCH to `200g egg` created a second job and produced 310 kcal. HTTP and database
  values agreed for all four nutrients, status and revision.
- Confirmation persisted; reload was identical; a later edit returned HTTP 409.
- `stop` followed by `start` retained the confirmed meal, ID and revision in the
  dedicated database volume.

The fixture only parses six English food keys with explicit grams. It does not
prove Chinese extraction; conversation correction there must use API PATCH.

## Automated checks and limits

The full unit/integration suite passed **408 tests**, with two existing dependency
deprecation warnings; whole-repository Ruff passed. Both ran in a separate
container with read-only source and no network. Existing catalogue tests exercise
all 250 recipes through both calculation
modes with controlled inputs; this differs from live model extraction.

Screenshots and checked-in JSON are observations from this run. A TA should run
the commands again for independent evidence. No new CI result is claimed for a
`nutrichat` push, and no deployment or Canvas submission was performed.
