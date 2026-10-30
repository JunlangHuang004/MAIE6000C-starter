# Independent NutriChat QA

This folder is the durable working record for the on-demand `nutrichat-qa`
reviewer. Each run begins by reading [MEMORY.md](MEMORY.md). The reviewer writes
observations to files that a future run can read; this does not establish permanent
private chat memory or schedule automatic work.

The project agent is defined in
[`nutrichat-qa.toml`](../../.codex/agents/nutrichat-qa.toml). Its required `name`,
`description` and `developer_instructions` fields follow the
[official OpenAI subagent schema](https://learn.chatgpt.com/docs/agent-configuration/subagents),
checked on 31 October 2026. It inherits the parent session's model and permissions.
The review-only boundaries are instructions, not an independent security sandbox.

## Run workflow

1. Read this document, MEMORY, the current user requirements, [main README](../../README.md)
   and [demo guide](../../demo/README.md). Preserve unresolved defect IDs and
   distinguish user-reported issues from personally reproduced ones.
2. Record the date/time zone, target URL, branch, full Git revision and dirty state.
   Compare these with the last tested revision. Verify the running build corresponds
   to the intended source using build metadata or non-secret source fingerprints;
   if verification is unavailable, label it unverified. A branch name alone is
   insufficient. Do not read `.env` contents, cookies or credentials.
3. Establish the target provider without exposing configuration secrets. The
   intended full product is Qwen on `http://localhost:8003/app`; the separate port
   8002 demo fixture is not evidence of Chinese model extraction. Reconfirm target
   details each run. A `READY` handoff is required when the parent is still updating
   the runtime; initial preparation is not permission to test a stale build.
4. Select 8–12 synthetic scenarios from the matrix below. Record the intended
   model-triggering request cap before starting; use at most 12 by default,
   counting natural-language corrections and any model-backed mode changes.
   Structured form submissions, polling and language switches should be recorded
   separately. Do not automatically retry failures or silently replace cases.
5. Exercise the visible browser workflow. Capture a screenshot for each distinct
   failure and key successful states. Use direct API readbacks only as separately
   labelled supporting evidence. Do not use mocks to claim live acceptance.
6. Report each case as pass, fail, blocked or not run. A provider error remains a
   failed attempted case even if a later deliberate retry succeeds. A necessary
   clarification with withheld totals can be a pass. A wrong food with plausible
   totals is a failure. Inspect the interpreted food, quantity and assumptions,
   not just the completion state.
7. Save a dated report and evidence without replacing older reports. Update MEMORY
   with tested source/build, report links, new observations, unresolved defects and
   the next targeted checks. Close a defect only with an explicit relevant retest.
   Send findings to the implementing agent; do not change product code.

## Acceptance matrix

These are planned inputs, not evidence of a run. Adapt only when the current
requirements or catalogue establish a different expected outcome, and record why.
The twelve scenarios below require about ten model submissions when the workflow
is successful; stop at the agreed cap if extra clarifications consume it.

The current catalogue has 200 ingredients and 350 recipes, including soy-sauce
chicken (`dish_251`). The matrix below uses a fictional absent food for negative
checks. Earlier dated reports used soy-sauce chicken before it was added; preserve
those observations rather than applying their old identity expectation now.
Focused follow-ups can use a smaller explicitly agreed case/request budget.

| ID | Synthetic action/input | Required observation |
| --- | --- | --- |
| QA-01 | Open the target, inspect Basic/Advanced and supported-food catalogue; toggle 中文 / English with an unsent meal description | Controls and catalogue are usable in both languages; text and mode survive; language change does not estimate a meal. Record local account limitations accurately. |
| QA-02 | Basic: `一份番茄炒蛋，两个水煮鸡蛋` | Correct foods; visible reference portions/recipe assumptions; estimate available for review; assumptions are not presented as user-measured facts. |
| QA-03 | English UI, Basic: `200 g cooked white rice, no added oil` | Intended rice and edible grams; correct unit labels; no silent food substitution. Display translation and input recognition are assessed separately. |
| QA-04 | Switch QA-02 to Advanced; answer issued edible-weight/state/preparation/oil questions and review whole-batch recipe/yield | Totals withheld while required details remain unresolved; editable values persist through language switching; calculation uses explicitly accepted details. |
| QA-05 | Correct QA-02: `番茄炒蛋实际吃了150克熟重，水煮鸡蛋可食部分还是100克。` | Previous totals clear while reprocessing; interpretation retains both intended foods and changes the requested portion; renewed recipe approval if required. |
| QA-06 | Review and confirm the corrected meal, then reload | Same record ID, confirmed status and totals; confirmed record cannot be edited; a new meal can be started. |
| QA-07 | Basic: `月球紫晶兽肉，200克熟重` | With the verified absent name, explicit no-corresponding-record message; no substitute dish and no nutrition totals. Specifically reject 清蒸鲤鱼 substitution. |
| QA-08 | Advanced: `月球紫晶兽肉，200克熟重` | The same unsupported-food protection in Advanced; a quantity clarification cannot authorize a different food. |
| QA-09 | Basic: `100克熟白米饭，200克月球紫晶兽肉` | Known and unsupported mentions are accounted for; explicit unsupported message; no partial meal totals, including rice-only totals. |
| QA-10 | Basic: `100克月球紫晶兽肉` | Explicit unsupported-food message; no similar-food fallback and no totals. |
| QA-11 | Basic: `Garlic stir-fried Chinese broccoli (gai lan), 200 g` | Correct 蒜蓉芥蓝 identity if supported by reviewed names/aliases, otherwise explicit no-record outcome; never 清炒西兰花 with a numeric estimate. Record which outcome occurred. |
| QA-12 | Basic: `0克熟白米饭` | No calculated estimate; useful input-specific validation/clarification. A generic service failure is safer than fabricated totals but fails usability acceptance. |

For unsupported cases, inspect all four meal totals and any visible subtotals.
Zero-valued fabricated totals do not count as withheld. Record whether the UI gives
an actionable way to use a supported name or the actual supported ingredients.
Do not infer that a long catalogue guarantees matching of an unlisted synonym.

## Evidence and reporting

Use `docs/qa/reports/YYYY-MM-DD-<run>.md` and
`docs/qa/evidence/YYYY-MM-DD-<run>/` for new material. Include only synthetic data.
Screenshots must omit keys, cookies, unrelated browser tabs and personal records.
Do not save raw environment dumps or full logs containing private material.

Each report contains:

- **Scope and provenance:** requested outcome, URL, date/time interval, branch,
  full revision, dirty files relevant to the tested build, runtime verification,
  provider/model if safely observable, and previous report compared.
- **Execution:** planned versus attempted cases, model request count/cap, any
  deliberate retries, and tools used. Label browser/live-provider, direct API,
  deterministic, mocked/fixture and historical evidence separately.
- **Case results:** exact input/actions, expected and observed identity/quantity,
  status, totals or their absence, record ID, pass/fail/blocked/not-run and evidence.
- **Findings:** stable defect ID, severity, reproducible steps, actual/expected
  result, affected scope, screenshot/reference and retest status.
- **Assessment:** what the sample supports, release blockers, usability issues,
  environmental blockers and untested scope. Never promise universal food
  recognition or measured nutritional accuracy.

Severity: P1 is a release-blocking wrong-food estimate, unsupported-food total or
other material integrity failure; P2 is a workflow, recovery or clarity defect;
P3 is a minor presentation issue. Environmental failures and documented scope
gaps are recorded separately instead of being disguised as passes.

The reviewer may create synthetic records and QA evidence within the authorized
local review. It must not edit product files, read/store secrets, deploy, push,
publish, submit to Canvas, manage accounts or configure recurring jobs.
