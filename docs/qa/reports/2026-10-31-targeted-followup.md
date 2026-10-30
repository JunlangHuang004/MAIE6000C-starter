# Targeted browser follow-up — 31 October 2026

**Partial improvement; full acceptance remains open.** On the new frozen runtime,
the ordinary Chinese portion correction succeeded in Basic, then confirmation and
reload preserved the corrected record. Explicit ingredient recovery and both rice
inputs still failed. The five bounded scenarios produced **2 passes and 3 failures**,
without model retries. Keep the [failed baseline](2026-10-31-independent-browser.md)
as the historical record; this report does not replace it.

## Tested environment and scope

- Runtime commit: `a9843debc3bd25244145d8fdcb0f78b696307e5d`, branch `nutrichat`.
- Target: `http://localhost:8003/app`; native Safari controlled only through CUA.
- Approximate interval: **2026-10-31 01:24–01:29 Asia/Hong_Kong**
  (2026-10-30 17:24–17:29 UTC).
- The reviewer independently recomputed the digest of all 29 local service
  `.py`/`.json`/`.html`/`.js` files and matched
  `081fa170788a43f21ca911d54649db0be8a0866d028207eaba741bb2e4833711`.
  The [handoff manifest](2026-10-31-targeted-followup/runtime-handoff.json)
  records that same source digest for API, AI and worker. Container digest
  computation remains parent-supplied evidence, not a separate reviewer run.
- HEAD matched at the start. The parent began later local product work while
  explicitly freezing this runtime until the review ended. This evidence does
  not apply to that subsequent code or a later build.
- Qwen is recorded in the manifest; `qwen-plus` was specified in the handoff and
  was not independently exposed by the browser.
- The parent authorized a fresh **five-action** budget. All five were used:
  three new meal submissions and two natural-language replies. No mode changes,
  structured-answer submissions or model retries occurred. Confirmation and
  reload did not submit another meal to the model. See the
  [request ledger](2026-10-31-targeted-followup/request-ledger.json).
- These were real browser/application interactions. No fixture/mocked checks,
  direct API or hidden draft/source-text inspection was used. The parent's
  deterministic test results are separate evidence and are not counted here.
- Recovery used the reviewer's saved English-rice rejection from baseline B12.
  The correction test used a **fresh equivalent Basic meal**, not the original
  Advanced record. This distinction limits what the retest closes.

## Results

| Case | Exact action/input | Observed result | Assessment |
| --- | --- | --- | --- |
| T01 | Reply to the saved rejected rice record: `改成这次实际吃下的食材：生鸡胸肉150克、食用油5克、酱油10克` | The prefix was removed, but `生鸡胸肉150克、食用油5克、酱油10克` was still treated as one unsupported food. No totals. | **Fail — NC-QA-007 remains open** |
| T02 | New Basic meal: `一份番茄炒蛋，两个水煮鸡蛋` | Correct dish 200 g and eggs 100 g; labelled defaults; 365.2 kcal. | Pass |
| T03 | Reply: `番茄炒蛋实际吃了150克熟重，水煮鸡蛋可食部分还是100克。`; review, confirm, reload | Correct dish 150 g and eggs 100 g; 312.7 kcal, 20.6 g protein, 21.8 g fat, 7.8 g carbohydrate. Confirmation and reload preserved the same ID, revision 3, confirmed status and totals. Editing/mode-change controls were absent. | Pass in Basic; original Advanced variant not retested |
| T04 | New Basic meal: `200 g cooked white rice, no added oil` | Entire English string still reported unsupported. No totals. | **Fail — NC-QA-005 English variant remains open** |
| T05 | New Basic meal: `100克熟白米饭` | Entire weighted Chinese rice phrase reported unsupported. No totals. | **Fail — NC-QA-005 Chinese variant remains open** |

The successful record is **`06d099fc-2891-47aa-970a-8cf204609939`**. Revision 1
was the Basic estimate, revision 2 the corrected estimate, and revision 3 the
confirmed result. The reference batch retained 15 g oil and 400 g finished yield.
This was the Basic recipe assumption; it was not the baseline Advanced recipe
edited to 10 g oil. The UI's locked state was observed, but no direct API edit was
attempted to recheck server-side rejection.

## Evidence

- T01: [ingredient recovery screenshot](2026-10-31-targeted-followup/01-ingredient-recovery-still-fails.png)
  and [visible page text](2026-10-31-targeted-followup/01-ingredient-recovery-still-fails.txt).
- T03: [corrected, confirmed, reloaded meal](2026-10-31-targeted-followup/02-corrected-confirmed-reloaded.png)
  and [visible page text including record ID](2026-10-31-targeted-followup/02-corrected-confirmed-reloaded.txt).
- T04: [English rice rejection](2026-10-31-targeted-followup/03-english-rice-still-rejected.png)
  and [visible page text](2026-10-31-targeted-followup/03-english-rice-still-rejected.txt).
- T05: [Chinese rice rejection](2026-10-31-targeted-followup/04-chinese-rice-still-rejected.png)
  and [visible page text](2026-10-31-targeted-followup/04-chinese-rice-still-rejected.txt).

Screenshots were cropped to the page body to exclude unrelated browser tabs.
The saved text is accessibility-visible UI content, not provider/source-text
fields. The quoted unknown-food labels do not by themselves prove which internal
layer caused the false rejection.

## Retained limitations and next checks

NC-QA-006 is **partially verified fixed for the exact phrase in Basic**. Repeat the
original Advanced case before closing that variant, including preservation of
user-edited oil/recipe values and renewed recipe review where required.
NC-QA-005 and NC-QA-007 remain open on this runtime. Do not promise that ordinary
rice recognition or a supplied ingredient list will work from this evidence.

Gai-lan recognition, unsupported chicken names in both modes, mixed-meal total
suppression, zero/negative/over-limit weights and broad reliability were not
retested in this five-action run. The baseline observations remain the relevant
evidence for those areas; the zero-weight generic failure and English gai-lan
recognition limitation remain open. No universal matching or nutrition-accuracy
claim is supported.

The last Safari page was left on the synthetic Chinese-rice rejection for
inspection. The native-app fallback offers no browser-tab deliverable marker.
The runtime was released to the parent after the final result. No product edits,
push, deployment, account changes or Canvas submission were performed by this
reviewer. Future product changes require a new identified runtime and a new
bounded handoff; no model requests remain in this run's budget.
