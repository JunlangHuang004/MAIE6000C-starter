# Run and inspect the integrated demo

This checkout combines the `nutrichat` food workflow with accounts, personal
references and daily tracking. The frozen `w07-midterm` tag remains a separate
meal-only submission; do not use its no-login instructions for this checkout.

## Full Chinese workflow

Follow [integrated setup](../docs/integration.md) to select Qwen or HKUST, start an
isolated project and open <http://localhost:8005/app>. Register/sign in before
creating meals. The catalogue is the unchanged `nutrichat` set of **200 ingredients
and 350 recipes**. No private model key is included in Git.

Suggested review sequence:

1. Save a synthetic adult profile and inspect the daily calorie/macronutrient
   reference. Switch Chinese/English and confirm unsent values are preserved.
2. Basic: enter `一份番茄炒蛋，两个水煮鸡蛋`. Inspect default portions and assumptions.
3. Switch to Advanced, supply missing details and explicitly review the recipe.
   Review any changed foods/weights before confirmation.
4. Try `100克白米饭，200克月球紫晶兽肉`. The unknown item must block **all** totals;
   the app must not replace it with another dish. Use **Build from actual
   ingredients** to enter actual supported ingredients and weights if known.
5. Choose the consumption date and confirm a completed estimate. Reload; its
   saved result and date must remain. It should appear in your recent meals and
   that day's automatic calorie sum.
6. Save a daily weight and optional manual calorie total. A manual total replaces
   the meal sum; clear it to restore automatic aggregation. Review both 30-day
   charts; absent days remain blank.
7. Sign out and use a second account. Its history/profile/tracking are separate;
   the first account's meal URL must return 404 for the second account.

[Integrated screenshots](INTEGRATED_GUIDE.md) show accounts, profile and trends.
[Meal screenshots](SCREENSHOT_GUIDE.md) illustrate the preserved estimation
workflow and identify their capture versions. See [the integration verification
record](../docs/evidence/integration-verification.md) for current acceptance results.
Reference recipes are estimates; successful workflow checks do not establish
measured nutrition accuracy or recognition of every dish.

## Key-free engineering check

Requirements: Docker running, Docker Compose 2.24.4+, host Python 3.10+.
Application Python and HTTP checks run inside Docker. From the checkout root:

```sh
python3 demo/run.py start
python3 demo/run.py check
python3 demo/run.py status
python3 demo/run.py stop
```

Open <http://localhost:8006/app> and register an account for manual exploration.
The scripted check creates its own disposable account with random credentials
and revokes its session afterward. It writes synthetic evidence to ignored
`demo/output/check.json`, never an API key or password.

This project is `nutrichat-integrated-demo`, with its own PostgreSQL volume. No
private `.env` is loaded. Only API loopback port 8006 is published. The default
fixture supports six English foods and explicit grams: `100g egg` is 155 kcal;
use **Replace meal description** with `200g egg` to obtain 310 kcal. It does not
interpret Chinese descriptions or conversational replies. Unsupported offline
free-text replies return an explicit error instead of silently retaining old totals.

The check observes pending rows while its worker is paused, resumes the worker,
checks saved totals, corrects the meal, confirms/reloads it, rejects an edit to the
confirmed record, saves a profile, tests daily manual override/clear, and verifies
30-day data plus logs/metrics. Let it finish before submitting other meals in the
same project. It does not pause a different project or change the public server.

To use another independent copy, change **both** values consistently:

```sh
export NUTRICHAT_DEMO_PROJECT=nutrichat-my-review
export NUTRICHAT_DEMO_PORT=18082
python3 demo/run.py start
python3 demo/run.py check
python3 demo/run.py stop
```

Changing just the port does not isolate services or the database. Original preview
project names are protected by the launcher. `stop` retains data; restart with the
same name and port to resume. Do not remove volumes as a routine troubleshooting step.

## Tests and troubleshooting

```sh
docker compose -p nutrichat-integrated-demo --env-file .env.example \
  -f compose.yaml -f demo/compose.demo.yaml exec -T api pytest -q -m 'not smoke'
docker compose -p nutrichat-integrated-demo --env-file .env.example \
  -f compose.yaml -f demo/compose.demo.yaml exec -T -e SMOKE_BASE_URL=http://api:8000 \
  api pytest tests/smoke -q
npm ci --prefix tests/frontend
npm test --prefix tests/frontend
```

Live Qwen matrix checks require an existing dedicated check account. Set
`NUTRICHAT_CHECK_USERNAME` and securely supply `NUTRICHAT_CHECK_PASSWORD` (or use
the terminal's hidden password prompt), then run:

```sh
python3 demo/check_food_matrix.py --base-url http://localhost:8005 --live
```

Run with the installed Python dependencies, or inside the API container. This
uses model quota and creates synthetic records; it is not an offline test.
It retains failure evidence and does not retry failed inputs to improve a score.

- Cannot start: check Docker and Compose versions and whether the selected port
  is already occupied. Choose a new project and port together.
- Sign-in loops: HTTP previews require `AUTH_COOKIE_SECURE=false`; the browser
  origin must exactly match `AUTH_PUBLIC_ORIGIN`, including hostname and port.
- HTTP 403 on writes: include `X-NutriChat-Request: 1` and a matching browser Origin.
- No Chinese interpretation: the offline provider is selected, or model
  configuration/access/quota failed. Healthy containers do not prove model access.
- Long-lived queued record: inspect worker/job state. Interrupted claimed jobs
  have no automatic recovery. Do not delete records or volumes to hide the failure.
- Old meal missing after upgrading: old shared records retain null ownership;
  new accounts do not automatically own them. See [data upgrade policy](../docs/integration.md#data-upgrades-and-existing-records).

Earlier [demo verification](VERIFICATION.md) and screenshots remain dated evidence
of the original meal-only release. Current limits and checks are documented in
[operations](../docs/operations.md) and the integration report.
