# NutriChat: TA walkthrough

This guide describes the **`nutrichat` branch**, not `test`. It covers the meal
estimation application available at this checkpoint. Independent user accounts,
personal nutrition targets, daily weight records and monthly trends are **not**
part of this demo.

Start with the [demo setup guide](README.md), then open the **Chinese product
demo at http://localhost:8003/app**. Once Qwen is configured on the server, a user
opens the application directly: **no account registration or login is required**.
The user does not enter an API key into the application.

Choose **中文 / English** in the page header for the interface language. It is
remembered in the browser and can be changed during the workflow without losing
unsent answers or recalculating the meal. The English interface includes food
display names and reference recipes; user descriptions and free-form model notes
keep their original wording. The bilingual control guide below also explains the
Chinese screenshots.

[See the six-step screenshot guide](SCREENSHOT_GUIDE.md), or
[go to the detailed Chinese meal walkthrough](#4-main-product-demo-chinese-meal-dialogue).
Port 8001 belongs to the separate `test` preview and is not used here. The
`退出登录` (Log out) header button belongs to the optional public gateway
deployment; it has no role in this directly accessible local demo.

## 1. Idea and intended users

People increasingly care about their health but may not know the approximate
nutrition of the meals they already eat. NutriChat is for students, busy people
and home-food eaters who want a convenient first estimate, especially for Chinese
food. A user describes a meal, reviews the interpretation, corrects missing or
inaccurate details and confirms the saved result.

The outputs are calories, protein, fat and carbohydrates. These are estimates
based on entered quantities and reference food data, not measurements of a real
dish or individualized medical advice. The purpose is to make the assumptions
visible and editable before the user accepts the estimate.

## 2. Product demonstration and supporting engineering check

| Route | What is needed | What it demonstrates |
| --- | --- | --- |
| **Main product demo: Chinese meals, port 8003** | Server configured for Qwen with an authorized key, matching region/workspace endpoint and available quota; users open `/app` directly | The 138-ingredient/250-recipe catalogue, Chinese descriptions, Basic-mode assumptions, Advanced-mode questions, natural-language corrections and confirmation |
| **Optional offline engineering check, port 8002** | Docker, Docker Compose and Python 3; no model key | Deterministic fixture values plus the real API, PostgreSQL, worker, internal AI service, correction and persistence boundaries |

The Chinese route demonstrates NutriChat's current product features. The offline
route is a small, repeatable engineering fixture for inspecting the service
workflow without cloud-model access; its six English food keys are **not the
product's full food catalogue**. It does not establish live Chinese extraction.
No private team credentials are distributed in the repository, and the offline
check can run without a Qwen account or purchase.

## 3. Chinese UI labels: quick English guide

| Label in the application | Meaning / action |
| --- | --- |
| `说说这餐吃了什么` | Describe what you ate |
| `选择估算模式` | Select estimation mode |
| `基础版 · 快速大概估算` | Basic: quick approximate estimate |
| `进阶版 · 补充细节精算` | Advanced: supply more specific inputs |
| `餐食描述` | Meal description text box |
| `开始估算` | Start the estimate |
| `查看支持的食材和菜谱` | Expand the ingredient/recipe catalogue |
| `查看本餐对话记录` | Expand the saved conversation for this meal |
| `继续对话／补充或更正` | Add details or correct the interpretation; live dialogue needs Qwen |
| `发送补充说明` | Send the follow-up message |
| `提交回答` | Submit selected structured answers |
| `切换到进阶版补充细节` | Recalculate this unconfirmed meal in Advanced mode |
| `本餐营养估算` | Nutrition estimate for this meal |
| `热量 · kcal` / `蛋白质 · g` / `脂肪 · g` / `碳水 · g` | Calories / protein / fat / carbohydrates |
| `确认并保存` | Confirm the reviewed result and lock the record |
| `新的一餐` | Start another meal; this does not delete the previous record |

The browser defaults to Basic mode. The raw API defaults to Advanced if `mode` is
omitted. On the Qwen product stack, Basic uses visible reference assumptions and
Advanced asks for more specific food, portion and preparation details.

## 4. Main product demo: Chinese meal dialogue

Follow the [Qwen setup in the demo guide](README.md), then open
**http://localhost:8003/app** directly. No signup or login step is needed on this
branch's local application. The person setting up the server configures Qwen;
an end user only describes and reviews meals. See also the
[provider configuration details](../docs/cloud-deployment.md#configure-qwen).

The provider configuration uses `NUTRITION_PROVIDER=qwen`, `DASHSCOPE_API_KEY`,
`QWEN_BASE_URL` and `QWEN_MODEL`. Keep the key in a private environment file and
match its workspace/region to the endpoint. API and AI services must use the same
provider mode. Verify `GET /foods` returns `provider: qwen` on that stack before
using the sequence below. Model requests require authorized access and consume
quota; no private team key is included in GitHub. The offline `demo/run.py`
setup on port 8002 does not enable this Chinese workflow.

1. **Basic estimate:** if an old meal is displayed, click `新的一餐`. Choose
   `基础版 · 快速大概估算`, enter the following in `餐食描述`, then click
   `开始估算`:

   ```text
   一份番茄炒蛋，两个水煮鸡蛋
   ```

   Meaning: “One serving of tomato and scrambled eggs, and two boiled eggs.”
   Review the interpreted foods and the assumptions below each result. Basic
   mode can apply visible reference portions, preparation and recipes. Unknown
   foods or contradictions may still require questions.

2. **Inspect the assumptions:** open each food's details. Look for the selected
   weight, preparation, consumed oil, batch ingredients, finished batch weight
   and linked ingredient data sources. The collection contains **138 USDA
   ingredient records and 250 project-authored Chinese reference recipes**;
   those recipes are editable examples, not standardized restaurant dishes.

3. **Switch to Advanced:** before confirmation, click
   `切换到进阶版补充细节`. Basic defaults are not silently promoted to user facts.
   The API state may become `needs_input`, and the page asks for more information
   (`还需要这些信息，回答后会继续估算。`). Nutrient totals remain empty while
   required questions are unanswered.

4. **Answer the issued questions:** for a synthetic test, use 200 g of cooked
   tomato-and-egg dish and 100 g of edible boiled eggs, excluding the shells.
   Select the matching cooked-weight options. If asked, select boiled preparation
   for the boiled eggs; do not select a mismatching food to bypass a question.
   For the dish, inspect or edit the **whole-batch** ingredient quantities and
   **finished whole-batch weight**, then tick
   `我接受以上配方和成品重量作为本次估算依据` (Accept these recipe and yield
   assumptions for this estimate). Click `提交回答`. Answer the questions actually
   shown; their order and wording depend on the extracted facts. You may submit
   known answers first and complete the remaining questions in another round.

5. **Correct in conversation:** enter:

   ```text
   番茄炒蛋实际吃了150克熟重，水煮鸡蛋可食部分还是100克。
   ```

   Meaning: “I actually ate 150 g cooked tomato and scrambled eggs; the edible
   boiled-egg portion is still 100 g.” Click `发送补充说明`. Verify the new
   interpretation before accepting it. Re-extraction can require recipe approval
   again. Supply any further requested facts and wait for `待核对确认`.

6. **Confirm and reload:** review the resulting foods, quantities, assumptions
   and totals, choose `确认并保存`, and reload. Verify `已确认保存` (Confirmed
   and saved), the same record ID and the same totals. Confirmation locks the
   record; the follow-up and mode-switch controls disappear. Use `新的一餐`
   for another estimate. The browser restores the last viewed meal ID; this
   branch does not have per-user accounts or a personal history list.

Do not expect a single fixed calorie total for this sequence: accepted recipe
quantities, yield and extraction can differ. The acceptance criteria are correct
food/portion interpretation, visible assumptions, no totals while required
questions remain, recalculation after correction, and durable confirmation.

If Qwen times out, rejects the request or returns invalid structured data, the
application should show a failure rather than inventing a result. Record that
outcome separately. A successful offline check does not prove Qwen connectivity,
extraction quality or real-world nutritional accuracy.

## 5. Optional supporting check: offline workflow

This section uses the **small offline test fixture**, not the full Chinese
product catalogue. Start the separate stack with `python3 demo/run.py start` as
explained in the [setup guide](README.md). It is useful for checking persistence
and asynchronous processing without a model dependency. Both mode labels accept
the same explicit English gram input here; they do not add Chinese extraction or
assumed portions to the offline parser.

### A1. Enter a supported fixture meal

1. Open http://localhost:8002/app after starting the demo.
2. If a previously viewed meal is restored, click `新的一餐` (New meal).
3. Leave `基础版 · 快速大概估算` (Basic) selected.
4. Enter **`100g egg`** in `餐食描述` and click `开始估算`.
5. Wait for `待核对确认` (Awaiting review and confirmation).

The request first persists a meal and a pending job. The worker processes it in
the background, so `正在解析并检查缺失信息…` (Parsing and checking missing
information) may appear briefly. A fast result is
normal; the automated check deliberately pauses the isolated worker to make the
queued database state observable.

Expected result from the **legacy offline fixture catalogue**:

| Input | Calories | Protein | Fat | Carbohydrates |
| --- | ---: | ---: | ---: | ---: |
| `100g egg` | 155 kcal | 13 g | 11 g | 1.1 g |
| `200g egg`, after the API correction below | 310 kcal | 26 g | 22 g | 2.2 g |

These exact numbers are reproducible fixture values. They are not the Qwen
catalogue's USDA egg mapping and should not be used to compare the two providers.
Note the meal ID and revision shown below the result as `记录 … · 第 … 版`.

### A2. Confirm and verify saved state

1. On the application page, review all four nutrient totals: 155 kcal, 13 g protein,
   11 g fat and 1.1 g carbohydrates.
2. Click `确认并保存` (Confirm and save).
3. Verify `已确认保存` (Confirmed and saved), then reload the page. The same
   record ID and values must reappear.
4. Confirm that the confirmation button, mode switch and follow-up form are no
   longer available. The page says to start a new meal for further changes.
5. The automated check verifies the same protection through the API: an edit
   after confirmation receives **HTTP 409**, even with the current revision.

The estimate is already persisted before confirmation. Confirmation records the
user's acceptance and locks it; it is not the first database save. The browser
remembers only the last viewed meal ID and retrieves its contents from the API.
There is no account-specific history list in this branch. Copying the ID lets a
reviewer inspect that saved record through GET independently of the page.

### A3. Inspect validation without cloud access

If a record is displayed, click `新的一餐` first. After a rejected input, simply
replace the text and submit the next example:

| Input | Expected outcome |
| --- | --- |
| `egg` | Rejected: explicit gram weight is required by the offline provider |
| `100g pizza` | Rejected: not an accepted offline food name |
| `0g egg` | Rejected: food weight must be greater than zero |
| `100g egg and 100g broccoli` | Accepted; multiple supported items are separated by `and`, commas, semicolons or `+` |

Invalid creation input returns HTTP 422 and creates no analysis/job. This differs
from a provider failure after an accepted request, which leaves a saved `failed`
analysis and failed job. The six accepted offline catalogue keys are
`chicken breast`, `white rice`, `rice`, `egg`, `salmon` and `broccoli`;
`white rice` and `rice` use the same values. Each weight must be at most 10,000 g.

**Catalogue display limitation:** the catalogue panel shows the full ingredient
and reference-recipe collection even in offline mode. Its presence is not a
promise that the offline parser can accept those Chinese names. Check the
provider banner and the `provider` field at http://localhost:8002/foods.

### A4. Optional technical inspection: replace a description through the API

The offline provider does **not** interpret conversational corrections. In this
branch, typing `200g egg` into `继续对话／补充或更正` stores a new conversation
message but the offline calculation still reads the original meal description.
Use the supported replacement endpoint below to inspect a real correction.
Use the Chinese product walkthrough above for natural-language correction.

The automated `python3 demo/run.py check` command exercises correction without
manual ID copying. The main browser walkthrough above does not require this
manual procedure. To inspect the correction endpoint yourself, first start a
**new, unconfirmed** `100g egg` meal and wait for its result:

1. Open http://localhost:8002/docs in a second tab.
2. Expand **`GET /analyses/{analysis_id}`**, choose **Try it out**, paste the meal
   ID from the page, and choose **Execute**. Read the current `revision` and
   verify that `status` is `completed`.
3. Expand **`PATCH /analyses/{analysis_id}`** and choose **Try it out**. Use the
   same ID and this body, replacing `1` with the revision you just read:

   ```json
   {"food_text": "200g egg", "revision": 1}
   ```

4. Choose **Execute**. Expect HTTP 200, the same analysis ID with `status: queued`,
   and a newly created job ID. This replaces the description and resets its old
   dialogue; it does not append a second food to the meal.
5. After processing, execute the GET again until `status` is `completed`. Reload
   the application tab to see the corrected 310 kcal result. You can then confirm
   and reload this new record using the same controls as A2, expecting the
   **corrected** 310 / 26 / 22 / 2.2 totals. A later PATCH with its current
   revision must return HTTP 409 because confirmation locks the record.

If you get HTTP 409, read the latest record before retrying: its revision or state
has changed. Do not submit the correction while queued or after confirmation.

## 6. What happens internally

```text
Browser describes a meal
    → FastAPI saves analysis + pending job in PostgreSQL
    → Worker claims the job independently of the HTTP request
    → Internal AI service extracts/validates facts and calculates nutrition
    → Worker saves questions or results in PostgreSQL
    → Browser reads, reviews, corrects, confirms and reloads the saved record
```

| Component | Responsibility |
| --- | --- |
| Browser | Collect input, show progress/questions/evidence, send reviewed corrections and confirmation |
| FastAPI | Validate requests, persist input/jobs, expose saved results, enforce state and revision checks |
| PostgreSQL | Store meal descriptions, dialogue, drafts, questions, results, confirmation and job metadata |
| Worker | Claim a durable pending job, call the AI service, persist success or failure |
| AI service | Route to the offline parser or Qwen extraction and return validated results |
| Qwen, when configured | Map language and conversation to supported food IDs and explicit meal facts |
| Python calculation | Use the food snapshot, recipe ingredients, edible grams, oil and yield to compute totals |

Qwen is a cloud inference dependency, not a locally trained model. The model does
not supply the authoritative nutrient numbers. Structured answers to already
issued questions can update the validated draft without another Qwen call.

Analysis states are `queued → completed → confirmed`, with `needs_input` for
unresolved questions and `failed` for processing errors. Job states are
`pending → claimed → completed/failed`. A **completed job can produce a
`needs_input` analysis**: asking a valid clarification question is successful
processing, not a crash.

## 7. Evidence a TA can check

Run `python3 demo/run.py check` after the demo starts. Use its fresh
`demo/output/check.json` report rather than treating committed historical evidence
as a result from your machine. Check the reported outcome and the matching
analysis/job IDs. The report contains synthetic demonstration data.

| Boundary | Inspectable evidence | What success means |
| --- | --- | --- |
| Input | `POST /analyses` response | HTTP 201 with a meal ID and job ID |
| Persisted input | PostgreSQL read while the isolated worker is stopped | Meal is `queued`, job is `pending`, attempts are zero and nutrient totals are null |
| Asynchronous work | Worker start plus correlated `job_claimed` / `job_completed` logs | A separate worker claims and processes the saved job |
| Persisted output | PostgreSQL and `GET /analyses/{id}` reads, correction, confirmation and reload | Expected fixture totals are stored, correction recalculates, and confirmed edits are rejected |
| Operational signal | `/health/ready`, job timestamps and log IDs | API/database readiness and observable processing lifecycle |

The browser shows the product workflow; HTTP, database and correlated logs show
that the service boundaries work. `/health/ready` checks the API's database access;
HTTP 200 by itself does not prove that every worker or Qwen request is healthy.
The [setup guide](README.md) gives the commands for status, logs and shutdown.

## 8. Scope and limits to keep visible

- This branch is a shared-data teaching prototype. Local access has no built-in
  authentication or per-user ownership. Use synthetic meals for the demo.
- Confirmation locks a record. To change an already-confirmed estimate, start a
  new meal; the app does not offer an edit-after-confirmation path.
- Repeated create requests create separate records. Automatic retries,
  idempotency keys and recovery of jobs interrupted while claimed are absent.
- Basic mode trades input detail for explicit reference assumptions. Advanced
  mode improves specificity but does not establish measured nutritional accuracy.
- Regional recipe variations, cooking losses, edible portions and consumed oil
  affect results. Raw and cooked weights are not automatically interchangeable.
- Image-based nutrition recognition, personal nutrition targets and monthly
  calorie/weight trends are outside this branch's demonstration scope.
- The existing public ECS deployment may differ from this checkpoint. The local
  branch-specific setup is the reproducible reference for this guide.

## 9. Optional short narration

> NutriChat helps students and busy home-food eaters understand the approximate
> nutrition of everyday meals, especially Chinese food. Users open the
> application directly, describe what they ate, review calories and three
> macronutrients, then correct and confirm the saved estimate.
>
> The current catalogue includes 138 ingredients and 250 Chinese reference
> recipes. In Basic mode, I can describe a serving of tomato and scrambled eggs
> and review the assumptions. Switching to Advanced lets me specify edible
> weight, preparation, oil and recipe details. I can correct the portion in
> conversation, confirm the recalculated result and reload the same record.
>
> Internally, the API saves a meal and job in PostgreSQL. A separate worker calls
> the AI service. Qwen extracts meal facts, while Python calculates nutrients
> from food data.
>
> A separate offline check provides reproducible HTTP, database and worker-log
> evidence without a model key. These estimates support awareness; they are
> not measured nutrition or medical advice.

This narration is optional. The runnable demo and written instructions are the
inspection materials; neither a recorded video nor presentation slides are
required by the TA's clarification.
