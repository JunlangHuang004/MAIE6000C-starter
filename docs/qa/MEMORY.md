# NutriChat QA memory

Read this file at the start of every review. Preserve unresolved findings and
append linked run history. These repository files provide cross-run memory when
read; there is no promise of permanent private conversation memory or automatic
future execution.

## Current handoff — 31 October 2026 (Asia/Hong_Kong)

- Phase: expanded-catalogue demo and targeted wrapper follow-up complete; browser
  and runtime released to the parent. Await a new READY before more testing.
- Latest [expanded demo report](reports/2026-10-31-expanded-demo.md) covers the
  complete six-step workflow and fresh screenshots on
  `71a0ecd56f2de09460ce899b1b183f723ab45b0e`, followed by the exact parenthetical
  regression and custom confirmation/reload on
  `dae0b946e286736020becf018c49b4e81eb46ec6`.
- Target: `http://localhost:8003/app`, branch `nutrichat`, Qwen (Qwen Plus in
  handoff). Visible coverage: **200 ingredients and 350 reference recipes**.
  Chinese-first additions retain Chinese names/method notes in English UI.
- Final local 31-service-file digest independently matched the
  [final handoff manifest](reports/2026-10-31-expanded-demo/final-runtime-handoff.json):
  `dfd857332551291c3920fed0005a63dac9fdc5255d3ee9f9fdba9f05e80484fb`.
  Container hashes/provider/health are parent-supplied manifest evidence.
- Latest first phase: nine requirement checks passed and one rich-input known-food
  rejection failed. Targeted final-build follow-up: both checks passed, closing
  the exact new failure. Six model-facing submissions across both phases, plus
  one mode switch counted conservatively; no automatic retries. The follow-up
  was an explicit post-fix retest with a fresh cap. Unused budget is not standing
  permission for future runs.
- Main record `80afe1a8-a493-44b7-a096-4234d78547f0`: Basic 365.2 kcal, Advanced
  reference approval, exact correction to 150 g dish + 100 g eggs, 312.7 kcal;
  confirmed/reloaded at revision 6 on `71a0ecd`. All six main guide screenshots are
  fresh. The main record was not reopened on the final build because the UI has
  no record-ID picker/history list; do not imply it was.
- New rich-input `豉油鸡200克熟重、可乐鸡翅75克熟重（已去骨）、蒜蓉空心菜150克熟重。`
  initially rejected wings safely on `71a0ecd`. After a bounded-suffix fix, the exact
  phrase passed on `dae0b94`: all intended foods/weights, 743.8 kcal, 56.9 g protein / 48.5 g fat / 20.4 g carbohydrate,
  record `ed30cc68-d1bb-4441-8d66-b60c8395c546`,revision 1, not confirmed.
- Unknown `100克熟白米饭，200克月球紫晶兽肉。` withheld all totals. Structured
  replacement of item 2 with raw chicken 300 / oil 10 / soy 20 g,finished 600 / eaten 150 g
  retained rice 100 g: 244.8 kcal, 20 g protein / 4.8 g fat / 28.4 g carbohydrate. Record
  `9bd7cba2-886b-46f1-a014-a7e3876e14c7` confirmed and reloaded on final `dae0b94`,
  revision 3, editing locked. Actual selected ingredients—not the fictional food—
  supplied the calculation basis.
- Thirteen new page-only screenshots now illustrate the TA guide. Images 01–11
  capture `71a0ecd`; 12–13 capture `dae0b94`. Read-only Git comparison confirms identical
  UI/static and catalogue files between the two sources. Original captures and
  dated failures remain preserved as history.
- Retained limitations: free-text multi-ingredient recovery, English gai-lan
  recognition, zero-gram generic errors, general provider reliability, and
  non-reference edited-recipe correction variants. Individual accounts absent.
  Browser normal zoom restored; final successful dish sample visible.

## Product contract to retain

- Describe meals in natural language. Basic uses visible reference defaults;
  Advanced asks for missing facts and explicit recipe/batch-yield review.
- Chinese/English interface switching preserves meal state and unsent values.
  Translation is separate from model recognition.
- Users review, correct, confirm and reload a durable record. Confirmed records
  are locked. Pending required input leaves nutrition totals absent.
- Unsupported food must say there is no corresponding food record. It must never
  become a different dish. A mixed meal with an unsupported item must withhold
  **all** meal nutrition totals rather than show a partial estimate.
- A custom ingredient recipe can replace one item after explicit catalogue
  selection, grams, raw/cooked/as-sold state and acceptance. Preserve other items;
  unresolved items still block totals. Consumed amounts and whole-batch allocation
  are distinct. Label custom recipes, assumptions and provenance; do not imply
  the unsupported dish became a measured catalogue record.
- Last tested runtime coverage is 200 ingredient records and 350 reference
  recipes, with reviewed names/aliases; this is finite coverage, not recognition
  of every dish, synonym or spelling. Numeric precision is not measured accuracy.
- Local app lacks individual accounts and per-user ownership. An optional public
  shared-password session gateway exists; it is not individual account support.
  The older public deployment is not proof of the intended branch build.

## Open issues and retained limitations

| ID | Severity / status | Evidence and expected retest |
| --- | --- | --- |
| NC-QA-001 | P1 historical issue / sampled safety retest passed on `2245020` | User reported 豉油鸡 → 清蒸鲤鱼. Baseline B01–B04 rejected 豉油鸡 and 酱油鸡 explicitly in both modes with no substitute/totals. B05 withheld all mixed-meal totals. Retain regression coverage; this does not prove historical saved records were repaired or every unknown is safe. |
| NC-QA-002 | P1 historical substitution / safety retest passed; recognition limitation open | Historical gai lan → 清炒西兰花 with 148.2 kcal is documented in [English-input verification](../evidence/qwen-english-verification.md), source `6219a782bb8fd28fd5747ecf2de9d44606889270`. Baseline B09 on `2245020` rejected the entire exact input `Garlic stir-fried Chinese broccoli (gai lan), 200 g` with no totals. This prevents the sampled wrong estimate but does not demonstrate gai-lan recognition. |
| NC-QA-003 | P2 / reproduced for 0 g; open | B11 still gave a generic service-unavailable error without totals for `0克熟白米饭`. Negative and 10001 g historical variants in [demo verification](../../demo/VERIFICATION.md) were not retested. Do not infer the service-error root cause from the UI message. |
| NC-QA-004 | P2 / historical reliability concern, cause unproven | Historical twice-cooked-pork request failed; a longer Chinese dialogue needed a deliberate rerun. See [English verification](../evidence/qwen-english-verification.md) and [demo verification](../../demo/VERIFICATION.md). Preserve future failures and retries; do not infer a root cause or reliability guarantee from a small successful run. |
| NC-QA-GAP-001 | Documented scope limitation | No individual local registration/login or private account history. Optional public shared gateway is a separate deployment feature. Report scope truthfully; do not imply it was tested locally. |
| NC-QA-005 | P2 / exact reproduced variants passed on `7c841b1` | Baseline B05/B12 and follow-up T04/T05 rejected known rice. Latest browser S07/S08 correctly estimated exact `100克熟白米饭` as 100 g/130 kcal and `200 g cooked white rice, no added oil` as 200 g/260 kcal with 0 g oil. Mixed S01 retained known rice through custom recovery. Close those sampled variants with the latest report; preserve failed history and do not infer universal paraphrase coverage. |
| NC-QA-006 | P2 / exact Basic and Advanced phrase variants passed | Baseline Advanced record `3aed4959-68ad-4c86-8d57-c1ddaaedc5a2` failed the exact correction `番茄炒蛋实际吃了150克熟重，水煮鸡蛋可食部分还是100克。`. Basic retest passed on `a9843de`; expanded-demo E04–E05 passed the same phrase in Advanced on `71a0ecd`, retaining the reviewed 400 g reference batch and 15 g oil, then confirming/reloading. Non-reference oil edits remain untested. |
| NC-QA-007 | P2 / free-text path open; structured alternative passed on `7c841b1` | Exact reply `改成这次实际吃下的食材：生鸡胸肉150克、食用油5克、酱油10克` still failed on `a9843de`: the ingredient list remained one unsupported food, with no totals. Not repeated in the latest run. New explicit ingredient form passed consumed/batch calculations, item preservation, acceptance, language toggle, confirm/reload in S02–S06. This is an alternative, not evidence that free-text recovery is fixed. |

| NC-QA-008 | P2 / exact reproduced variant closed on `dae0b94` | Expanded-demo E06 falsely rejected known cola wings in `豉油鸡200克熟重、可乐鸡翅75克熟重（已去骨）、蒜蓉空心菜150克熟重。`, withholding all totals. Parent fixed bounded suffix handling; F02 retested the exact input successfully with all three intended foods/weights and 743.8 kcal. Preserve failed E06 and passed F02 separately. |

Historical evidence above was read from project reports, not rerun by this
reviewer. Passing unit/DOM/fixture tests does not close live recognition failures.
Unresolved issues must remain visible when adding a new report; retain closed
issues with their closing report and tested revision instead of deleting history.

## Run history

| Date | Run | Tested revision/build | Outcome |
| --- | --- | --- | --- |
| 2026-10-31 | QA setup and case planning | None; preparation HEAD only | Created agent instructions and QA memory/workflow. Verified TOML schema against official documentation. No live tests; waiting for READY. |
| 2026-10-31 01:10–01:20 HKT | [Independent Safari baseline](reports/2026-10-31-independent-browser.md) | Runtime `224502091bdf1b60635f13c854db93863501b153` | No sampled unsafe substitution/partial totals; 5 full-scenario failures. Corrections and explicit-ingredient recovery blocked. 12/12 conservative action cap reached; no retries. |
| 2026-10-31 01:24–01:29 HKT | [Targeted Safari follow-up](reports/2026-10-31-targeted-followup.md) | Runtime `a9843debc3bd25244145d8fdcb0f78b696307e5d` | Basic correction/confirmation/reload passed. Ingredient recovery and both rice inputs failed. 5/5 fresh model-action cap reached; no retries. Advanced correction not retested. |
| 2026-10-31 01:38–01:45 HKT | [Structured ingredient Safari acceptance](reports/2026-10-31-ingredient-form.md) | Runtime `7c841b15231cc3372bed571efb3b9335751db3f1` | Eight checks passed within 3/3 model actions. Consumed/batch custom recipes, validation, language preservation, rice retention and confirmed reload passed. Both exact rice regressions passed. Free-text and original Advanced limitations retained. |

| 2026-10-31 02:00–02:09 HKT | [Expanded catalogue demo and wrapper follow-up](reports/2026-10-31-expanded-demo.md) | `71a0ecd` main demo; `dae0b94` final targeted follow-up | Main Basic→Advanced→correction→confirm/reload passed; plain new dishes and unknown structured recovery passed. Rich-input known-food rejection failed, then exact post-fix retest passed. Six model-facing submissions plus one conservative mode-switch action, no automatic retries; 13 fresh guide screenshots. |

## Next run

1. Read memory and QA workflow; require a new READY with source/runtime/provider
   and a fresh bounded request cap. No ongoing monitoring is scheduled.
2. Preserve exact closed regressions: both rice variants, Basic/Advanced portion
   correction, rich `（已去骨）` food text, unknown no-substitution/no-partial-total
   behavior and structured per-item recovery.
3. Prioritize retained gaps when requested: non-reference edited recipe/oil
   corrections, free-text multi-ingredient recovery, English gai lan, invalid
   zero/negative/oversized weights and provider failures. Do not close them from
   unrelated passing samples or deterministic tests.
4. Use truly absent unknown examples; soy-sauce chicken is now supported. Recheck
   catalogue identity and source digest whenever coverage changes.
5. Record observations and failures, update memory and report to the parent.
   No product edits, deployment, publishing or Canvas submission by this reviewer.
