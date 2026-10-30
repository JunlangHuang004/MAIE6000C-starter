# Independent browser acceptance — 31 October 2026

**Assessment: not accepted for the complete review/correct/confirm workflow.**
The sampled unsupported chicken names now produce explicit no-record messages
without substituting another dish or displaying partial meal totals. Basic and
Advanced calculation worked for the supported Chinese example. However, five of
the twelve scenarios failed their full expected behavior: known rice was rejected
in two inputs, ordinary portion correction and explicit-ingredient recovery were
rejected, and zero-weight validation still returned a generic service error.

Seven scenarios passed their stated requirement, including a qualified gai-lan
identity-safety pass: it was rejected instead of estimated as broccoli. That is
**not** a successful recognition result. This small sample does not establish
general recognition reliability, measured nutritional accuracy or coverage of
all 388 catalogue entries.

## Provenance and method

- Reviewer: the separate `nutrichat-qa` agent, using the project QA memory and
  requirements rather than assuming the implementation passed.
- Target: `http://localhost:8003/app`; branch `nutrichat`.
- Tested runtime source: `224502091bdf1b60635f13c854db93863501b153`.
- Browser interval: approximately **2026-10-31 01:10–01:20 Asia/Hong_Kong**
  (2026-10-30 17:10–17:20 UTC).
- At the start, Git HEAD matched that revision and only documentation/QA files
  were dirty. The parent later prepared a product patch in the worktree while
  explicitly keeping the runtime frozen at `2245020`. This report applies to the
  frozen runtime, not the later worktree or a later deployment.
- The [runtime handoff manifest](2026-10-31-independent-browser/runtime-handoff.json)
  records matching 29-file source digests for local/API/AI/worker:
  `7d7938a6a96a315febe237121bc518d7e5cc9ff72232cd43973be636fc0c8a18`.
  The reviewer read and checked consistency of this parent-supplied manifest;
  it did not independently recompute the container digests.
- Provider: Qwen per the manifest; `qwen-plus` per the READY handoff. The browser
  does not expose the model name, so it was not independently read from the UI.
- All interactions used native Safari through CUA. A browser-provider tab was
  unavailable; no external Playwright, mocked responses or substituted fixture
  provider was used. No direct API/draft inspection was performed in this review.
- The browser initially restored an existing analysis. The reviewer immediately
  chose **New meal** and did not edit it. Every submitted meal was synthetic.
- [Request ledger](2026-10-31-independent-browser/request-ledger.json): **12/12
  conservatively counted actions** — seven initial estimates, three mode changes
  and two natural-language corrections. One structured Advanced answer submission
  was tracked separately. Mode changes were counted even though they may not call
  the model. There were **no model retries** and no request beyond the cap.
- One attempted correction click hit the browser's required-field validation
  because automation had not entered the text. The reviewer verified the filled
  field before its accepted submission; this was not a repeated model request.
- Screenshots show the app page region with unrelated browser chrome removed.
  Accompanying `.txt` files contain the visible accessibility text, not API drafts.

The planned matrix was adapted to cover both chicken names in both modes and the
user's explicit-ingredient recovery question. The fictional-food case was omitted
to remain within the bound. Confirmation/reload of a completed corrected record
was attempted as a workflow objective but blocked before a confirm control was
available; it is not counted as a pass.

## Twelve scenario results

| Case | Input/action | Observed behavior | Result |
| --- | --- | --- | --- |
| B01 | Basic: `豉油鸡，200克熟重` | Explicit no corresponding record; no fish substitution and no nutrition totals. Chinese → English → Chinese before submission preserved the unsent text and Basic mode. | Pass |
| B02 | Switch B01 to Advanced | Explicit no-record outcome retained; no estimate or substituted food. | Pass |
| B03 | New meal, Advanced: `酱油鸡，200克熟重` | Explicit no corresponding record and no totals. | Pass |
| B04 | Switch B03 to Basic | Explicit no-record outcome retained; no estimate or substituted food. | Pass |
| B05 | Basic: `100克熟白米饭，200克豉油鸡` | Entire meal totals withheld, as required. However, both weighted mentions were reported unsupported, including known cooked white rice. | **Fail — NC-QA-005**; total suppression passed |
| B06 | Basic: `一份番茄炒蛋，两个水煮鸡蛋` | Correct dish and eggs; visible defaults of 200 g dish and 100 g eggs. 365.2 kcal, 23.3 g protein, 25.5 g fat, 10 g carbohydrate. Reference recipe and source links visible. | Pass |
| B07 | Switch B06 to Advanced; fill weights 200/100 g, cooked edible dish weight; review recipe and change batch oil 15 → 10 g | Required questions withheld totals. The 200/100 g entries, 10 g oil, 400 g batch yield and checked approvals survived switching to English. Structured submission produced 343.1 kcal, 23.3 g protein, 23 g fat, 10 g carbohydrate. | Pass |
| B08 | Correct B06/B07: `番茄炒蛋实际吃了150克熟重，水煮鸡蛋可食部分还是100克。` | Old totals cleared. The UI then invented two unsupported food mentions from the correction suffixes: `实际吃了150克熟重` and `可食部分还是100克`. Recipe oil stayed 10 g, but the meal could not finish or be confirmed. | **Fail — NC-QA-006** |
| B09 | New Basic meal: `Garlic stir-fried Chinese broccoli (gai lan), 200 g` | The entire input, including comma and weight, appeared in the no-record message. No broccoli estimate and no totals. No API source/draft was inspected. | Pass for identity safety; **recognition unavailable** |
| B10 | Reply to B09: `改成这次实际吃下的食材：生鸡胸肉150克、食用油5克、酱油10克` | The phrase after `改成` was treated as one unsupported food. No ingredient-based estimate or useful ingredient clarification appeared; no totals. | **Fail — NC-QA-007** |
| B11 | New Basic meal: `0克熟白米饭` | Generic “estimation service is temporarily unavailable” message; no totals and no specific invalid-weight guidance. No retry. | **Fail — NC-QA-003** |
| B12 | New Basic meal: `200 g cooked white rice, no added oil` | The entire English input was reported as an unsupported food. No totals or confirm control. Reload retained English, the same description and the saved no-record state. | **Fail — NC-QA-005** |

The supported Chinese record was
`3aed4959-68ad-4c86-8d57-c1ddaaedc5a2`: Basic revision 1, reviewed Advanced
revision 3. Its later failed correction was not confirmed. The unsupported/error
screens did not expose a record ID in the visible page, so no ID is invented for
those cases. Reload of an unsupported state is not proof of confirmed-record
durability or record locking.

## Findings requiring follow-up

### NC-QA-005 — P2: ordinary rice inputs are falsely rejected

Reproduce B05 or B12 in Basic. The Chinese mixed meal says no record exists for
`100克熟白米饭`; the English single-food meal says no record exists for
`200 g cooked white rice, no added oil`. Expected: match the actual supported rice
identity, preserve 100/200 g and the oil statement, and still withhold the whole
mixed meal when the chicken remains unsupported. In the English single-food case,
proceed with the supported estimate or a genuine missing-detail question.

Evidence: [mixed meal screenshot](2026-10-31-independent-browser/04-mixed-unsupported-rice-false-rejection.png),
[visible mixed-meal text](2026-10-31-independent-browser/04-mixed-unsupported-rice-false-rejection.txt),
[English rice screenshot](2026-10-31-independent-browser/11-english-rice-false-rejection.png),
[English rice text](2026-10-31-independent-browser/11-english-rice-false-rejection.txt).

### NC-QA-006 — P2: normal portion correction becomes extra unknown foods

Reproduce B06 → B07 → B08. The ordinary Chinese correction produces two unsupported
entries consisting of quantity/context words. Expected: retain the intended dish
and eggs, update the dish portion to 150 g, preserve the eggs at 100 g and the
reviewed recipe, then request only legitimate remaining review. No confirmed
save/reload test can complete on this path while the false unknown foods remain.

Evidence: [correction screenshot](2026-10-31-independent-browser/07-correction-false-foods.png)
and [visible text](2026-10-31-independent-browser/07-correction-false-foods.txt).
This is a demonstrated workflow failure; the browser evidence alone does not
establish the underlying parser/model responsibility.

### NC-QA-007 — P2: explicit ingredients and seasoning do not recover a rejected meal

Reproduce B09 → B10. The UI reports
`这次实际吃下的食材：生鸡胸肉150克、食用油5克、酱油10克` as one unsupported
food. Expected: interpret the explicitly supplied chicken, consumed oil and soy
sauce with their quantities, or ask a specific clarification about those items.
It must not infer a replacement prepared dish or keep asking for ingredient details
while rejecting the provided list as a single food.

Evidence: [recovery screenshot](2026-10-31-independent-browser/09-explicit-ingredients-failed-recovery.png)
and [visible text](2026-10-31-independent-browser/09-explicit-ingredients-failed-recovery.txt).
This run cannot support a promise that adding ingredients always recovers an
unsupported dish. The recovery was attempted after gai-lan rejection; recovery
after each chicken-name rejection was not separately tested.

### NC-QA-003 — P2: zero-weight validation still appears as service failure

B11 reproduces the historical usability issue for 0 g. No numeric result was
fabricated, but the generic service message does not tell the user to enter a valid
positive weight. Negative and over-limit weights were not repeated, so those
historical variants remain open. The message alone does not establish the cause.

Evidence: [zero-weight screenshot](2026-10-31-independent-browser/10-zero-weight-generic-failure.png)
and [visible text](2026-10-31-independent-browser/10-zero-weight-generic-failure.txt).

## What passed, and what remains untested

The sampled fresh `豉油鸡` and `酱油鸡` inputs passed explicit rejection in both
modes. The mixed meal withheld all totals. Gai lan was not substituted with
broccoli. These observations address the reported identity-safety failures for
these cases; they do not establish recognition of every supported name or repair
of historical saved analyses.

The supported Chinese recipe demonstrated Basic defaults, Advanced clarification,
edited oil arithmetic and unsent form preservation across language switching.
Evidence: [Basic estimate](2026-10-31-independent-browser/05-basic-supported-estimate.png),
[Basic visible text](2026-10-31-independent-browser/05-basic-supported-estimate.txt),
[Advanced English form](2026-10-31-independent-browser/06-advanced-english-fields.png).
Unsupported-message evidence is also saved for
[Basic chicken](2026-10-31-independent-browser/01-basic-unsupported.png),
[Advanced chicken](2026-10-31-independent-browser/02-advanced-unsupported.png),
[the alternative name](2026-10-31-independent-browser/03-basic-alias.png) and
[English gai lan](2026-10-31-independent-browser/08-english-gai-lan-safe-rejection.png).

No confirmed record was created in this run; confirmed reload and locked edits
remain unverified on this runtime. Catalogue browsing beyond the visible coverage
count, all other food names, other invalid weights, the public gateway, individual
accounts, responsive/mobile layouts, concurrency and broad reliability were not
tested. No product edits, deployment, push, account changes or Canvas submissions
were made by this reviewer.

The parent received each new defect promptly and plans a separate source update.
Any targeted retest must identify that new runtime and preserve this baseline.
