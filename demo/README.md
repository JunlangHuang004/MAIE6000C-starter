# NutriChat — self-guided TA demo

This folder makes the **`nutrichat` branch** runnable and inspectable. The main
product demo supports Chinese meal descriptions with **138 USDA ingredient records
and 250 editable Chinese reference recipes**. Users open `/app` directly; this
branch's local application needs **no account registration or login**.

Follow the Chinese workflow first when the server is configured for Qwen. A
separate, optional offline check reproduces the engineering boundaries without a
model key. Its six English fixture names are not the product's full food catalogue.
All example meals are synthetic.

[Follow the six-step screenshot guide](SCREENSHOT_GUIDE.md) to see the Chinese
workflow from input to confirmed reload.

The working slice is meal description → queued analysis/job → background
processing → saved estimate/questions → review/correction → confirmation and
reload. A recording or in-person presentation is not needed to follow these
instructions.

## 1. Get the correct branch

Requirements for setting up a fresh machine: Git, Docker running, Docker Compose
**2.24.4+** (the overlays use `!override`), and host Python **3.10+** for the offline
launcher/check. The initial build needs internet access for images and Python
packages. Application dependencies run in Docker; no host `pip install` is needed.

```sh
git clone --branch nutrichat --single-branch https://github.com/JunlangHuang004/MAIE6000C-starter.git nutrichat-ta-demo
cd nutrichat-ta-demo
git branch --show-current
git rev-parse HEAD
```

The branch command should print `nutrichat`. If you already have this checkout,
use it instead of cloning again. On Windows, use `python` if that is the name of
your Python 3 installation.

| What you want to inspect | Start here |
| --- | --- |
| Chinese food estimation, both modes, clarification and conversation | [Main product demo on port 8003](#2-main-product-demo-chinese-meals) |
| Repeatable service integration without Qwen credentials | [Optional offline check on port 8002](#3-optional-offline-engineering-check) |

On a prepared demo machine, users can open the running application immediately.
On a fresh machine, the operator configures Qwen once for the Chinese workflow;
end users do not supply a model key. If no authorized key is available, use the
offline check and inspect the written Chinese walkthrough and recorded evidence
separately. The repository does not distribute private credentials or require a
purchase to run the offline check.

## 2. Main product demo: Chinese meals

### Configure the server once

1. Create `.env` from `.env.example` **only if `.env` does not already exist**.
   Preserve existing settings when editing an existing file.
2. Follow [Qwen configuration](../docs/cloud-deployment.md#configure-qwen). In the
   private `.env`, set `NUTRITION_PROVIDER=qwen`, an authorized `DASHSCOPE_API_KEY`,
   the matching region/workspace's `QWEN_BASE_URL`, and `QWEN_MODEL`.
3. Start the dedicated local Qwen project:

```sh
docker compose -p nutrichat-qwen-demo --env-file .env -f compose.yaml -f demo/compose.qwen.yaml up -d --build --wait db ai api worker
```

4. Open **<http://localhost:8003/app>** directly. There is no registration or login
   step. API documentation is at <http://localhost:8003/docs>. Check
   <http://localhost:8003/foods> shows `"provider": "qwen"`.

This project has its own database volume, a loopback-only API port and no published
PostgreSQL/AI ports. It does not change other local application stacks. The
existing public ECS deployment is older and is not the reference for this
branch-specific guide. Qwen requests consume the configured
account's quota; healthy containers alone do not prove model access.

### Follow the user workflow

The header's **中文 / English** buttons switch the interface language and remember
the preference in this browser. The steps and screenshots below use Chinese;
select **中文** to follow the same labels, or **English** for translated controls,
questions, catalogue names and recipe explanations. Switching does not submit a
meal or discard unsent form entries. User descriptions and free-form model notes
remain in their original language. This display setting does not change Qwen's
food-recognition behavior.

See the [language-switch verification](../docs/evidence/ui-language-verification.md)
and [English interface screenshot](images/07-english-interface.png). English meal
recognition was checked separately: [19 of 21 sampled inputs passed](../docs/evidence/qwen-english-verification.md),
with a service failure and a gai-lan/broccoli mismatch retained in the report.

1. Keep **基础版 · 快速大概估算** (Basic) selected. If an old meal is displayed,
   first click **新的一餐** (New meal).
2. In **餐食描述** (Meal description), enter `一份番茄炒蛋，两个水煮鸡蛋` —
   one serving of tomato and scrambled eggs, plus two boiled eggs. Click
   **开始估算** (Estimate).
3. Review the interpreted foods, nutrient totals and visible portion/recipe
   assumptions. Open **查看支持的食材和菜谱** to inspect the larger catalogue.
4. Before confirming, click **切换到进阶版补充细节** (Switch to Advanced).
   Answer the issued weight, preparation and recipe questions. The
   [detailed walkthrough](WALKTHROUGH.md#4-main-product-demo-chinese-meal-dialogue)
   supplies synthetic quantities and explains whole-batch ingredients/yield.
5. Use **继续对话／补充或更正** to correct a portion, then click
   **发送补充说明**. Review the new interpretation and complete any remaining
   questions. Pending questions leave nutrient totals empty.
6. Click **确认并保存** (Confirm and save). Verify **已确认保存** (Confirmed),
   then refresh. The same record ID, confirmed status and totals should remain.
7. Use **新的一餐** for another estimate. Confirmed records are locked.

The [English walkthrough](WALKTHROUGH.md) maps all Chinese controls to their
meaning, explains the product idea and internal responsibilities, and includes
error cases. Chinese totals depend on the accepted recipe and quantities, so
check the interpretation and assumptions rather than expecting one fixed number.

The local header's **退出登录** button belongs to the optional public gateway;
there is no local logout route and no need to use it. The browser remembers the
last viewed meal ID, not an account-specific history list. Keep an ID to inspect
that record later through `GET /analyses/{id}`.

If Qwen fails, record that outcome. A successful offline check is evidence of
service integration, not proof of live Chinese extraction. See
[the verification record](VERIFICATION.md) for what was actually observed.

### Optional live checks with different foods and weights

After starting the Qwen project, run:

```sh
python3 demo/check_food_matrix.py --base-url http://localhost:8003 --live
```

This creates 17 synthetic meals and consumes model quota. It checks different
foods, 50/100/200 g rice, mixed meals, missing weights and invalid inputs without
automatic retries. Results go to `demo/output/food-matrix.json`; a failed check
produces a nonzero exit code. The recorded run passed 14 of 17 checks: three
invalid-weight cases returned generic failures without totals instead of useful
validation messages. See [all results and limits](VERIFICATION.md).

## 3. Optional offline engineering check

No Qwen account, API key or `.env` changes are needed for this supporting check.
From the repository root, run:

```sh
python3 demo/run.py start
python3 demo/run.py check
```

The launcher selects the small offline fixture provider, clears model credentials,
uses project `nutrichat-demo` and keeps its own database volume. It publishes only
the API on loopback port 8002. It does not modify the Qwen project or other local
application stacks.

The check performs actual HTTP, PostgreSQL and worker operations. It pauses only
this dedicated worker to inspect queued state, resumes it, and creates a separate
synthetic meal. Let the check finish before submitting other meals to port 8002.
It does not manipulate the meal currently open in your browser.

| Check | What the TA should see |
| --- | --- |
| Accepted input | HTTP 201, analysis ID and job ID |
| Durable pending input | Worker paused; PostgreSQL has `queued` analysis, `pending` job and null totals |
| Background processing | Worker resumes; matching job logs, attempts and timestamps; AI request counter increases |
| Saved initial estimate | HTTP and database agree on 155 kcal / 13 g protein / 11 g fat / 1.1 g carbohydrate for `100g egg` |
| Correction | API PATCH changes the description to `200g egg`; a new job produces 310 / 26 / 22 / 2.2 |
| Confirmation and reload | Current revision confirms successfully; a later GET returns the same confirmed result |
| Locked record | Attempted edit after confirmation returns HTTP 409 |
| Operational status | Readiness returns HTTP 200; this alone is not proof of worker success |

The command prints its outcome, exits nonzero on failure and saves
**`demo/output/check.json`**. Open that report for IDs, HTTP results, database
snapshots and matching logs from **your run**. Fresh output is ignored by Git and
replaces the previous local report. Every check creates another synthetic meal;
request idempotency is not implemented. The worker is resumed after the check.
[Checked-in verification](VERIFICATION.md) records the author's run separately.

### Optional browser inspection of the offline fixture

Open **<http://localhost:8002/app>** directly, enter `100g egg` in **餐食描述**,
and click **开始估算**. Expect 155 kcal, 13 g protein, 11 g fat and 1.1 g
carbohydrate. Click **确认并保存**, refresh, and check the saved record remains.
API documentation is at <http://localhost:8002/docs>.

This provider accepts six English food keys with explicit grams. It does not
provide the full Chinese catalogue, assumed portions or Advanced-mode dialogue.
The visible catalogue panel still lists 138 ingredients and 250 recipes; those
belong to the Qwen workflow. The offline conversation reply box does not replace
the original meal text, so use the API PATCH exercised by `check` for correction,
or start a separate meal. See the
[offline walkthrough](WALKTHROUGH.md#5-optional-supporting-check-offline-workflow)
for exact inputs and optional manual API inspection.

## 4. Inspect, stop and resume

For the Chinese Qwen project:

```sh
docker compose -p nutrichat-qwen-demo --env-file .env -f compose.yaml -f demo/compose.qwen.yaml ps
docker compose -p nutrichat-qwen-demo --env-file .env -f compose.yaml -f demo/compose.qwen.yaml logs --tail=50 api worker ai
docker compose -p nutrichat-qwen-demo --env-file .env -f compose.yaml -f demo/compose.qwen.yaml stop
```

Use the startup command in section 2 to resume it. For the offline project:

```sh
python3 demo/run.py status
python3 demo/run.py stop
python3 demo/run.py start
docker compose -p nutrichat-demo --env-file .env.example -f compose.yaml -f demo/compose.demo.yaml logs --tail=50 api worker ai
```

Stopping keeps each project's database. Starting again restores its records.
Keep synthetic examples separate from real meal data: this branch has no
individual account isolation.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `docker` unavailable / daemon connection fails | Install/start Docker and check `docker info` before startup |
| YAML `!override` error | Update Docker Compose to 2.24.4 or later |
| Chinese request fails | Check Qwen credentials, matching region/workspace, quota and AI/worker logs; do not replace the failure with a fixture result |
| Page asks for local account registration | Check you opened this `nutrichat` demo directly on port 8003 for Qwen or port 8002 for the offline check |
| Port 8003 or 8002 is occupied | Set `NUTRICHAT_QWEN_DEMO_PORT` or `NUTRICHAT_DEMO_PORT` respectively to an unused port; retain the setting for subsequent commands and use the chosen browser port |
| Chinese text is rejected on port 8002 | This is the offline fixture; use the configured Qwen product on port 8003 for Chinese meals |
| `egg` is rejected in the offline fixture | Use `100g egg`; explicit grams are required |
| Offline dialogue correction leaves the same number | Use the API PATCH exercised by `check`; the offline parser ignores conversation context |
| Analysis stays queued | Check the appropriate worker's logs/status; the offline `check` pauses its worker briefly, so let it finish |
| Offline check fails | Inspect `demo/output/check.json` and logs; fix the reported cause, then rerun `start` and `check` |
| Old browser record is missing after replacing a database | Enter a supported meal description in the available text box and click **开始估算**; a successful new estimate replaces the stale remembered ID. Keep the database volume to preserve old records |

On macOS/Linux, an offline port override example is
`NUTRICHAT_DEMO_PORT=8012 python3 demo/run.py start`; open
`http://localhost:8012/app` and use the same override for subsequent commands.
In PowerShell, set `$env:NUTRICHAT_DEMO_PORT="8012"` first. The Qwen overlay uses
`NUTRICHAT_QWEN_DEMO_PORT` in the same way.

## Folder map

| File | Purpose |
| --- | --- |
| [README.md](README.md) | TA setup, product workflow, verification and troubleshooting |
| [SCREENSHOT_GUIDE.md](SCREENSHOT_GUIDE.md) | Six illustrated steps through the Chinese product workflow |
| [WALKTHROUGH.md](WALKTHROUGH.md) | English usage guide, Chinese control labels, architecture and narration |
| [compose.qwen.yaml](compose.qwen.yaml) | Main Chinese product demo configuration |
| [run.py](run.py) | Optional offline launcher and reproducible integration verifier |
| [check_food_matrix.py](check_food_matrix.py) | Opt-in varied-food and gram-weight checks using real Qwen |
| [compose.demo.yaml](compose.demo.yaml) | Offline isolated check configuration |
| [VERIFICATION.md](VERIFICATION.md) | Observed validation and scope limits |
| `output/check.json` | Locally generated offline evidence from the TA's latest check |
