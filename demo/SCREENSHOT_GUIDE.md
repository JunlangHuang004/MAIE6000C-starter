# NutriChat: screenshot guide for the TA

This guide shows the **Chinese meal workflow on the `nutrichat` branch**. After
the operator completes the [Qwen setup](README.md#2-main-product-demo-chinese-meals),
open **http://localhost:8003/app** directly. **No account registration or login is
required.** The model key is configured on the server, not entered by the user.
The scope of this guide is the meal-estimation workflow on `nutrichat`.

The current interface also has **中文 / English** buttons in its header. Select
**中文** to match these screenshots, or **English** to use translated controls and
clarification forms. Switching preserves the meal and unsent form values. The
screenshots below were captured before the language buttons were added.

The screenshots follow one synthetic meal record through the workflow. In your
own run, compare the record ID immediately before and after reload; it must remain
the same. Your new record will have its own ID. The figures depend on the selected
foods, recipe, edible weights and accepted
assumptions. They are not guaranteed outputs for every Qwen response or measured
nutrition for an actual meal. Use the [verification record](VERIFICATION.md) for
the separately recorded checks and their limits.

**Workflow:** describe → review Basic estimate → add Advanced details → correct
the portion → review the recalculated estimate → confirm and reload.

## 1. Describe a Chinese meal in Basic mode

Keep **基础版 · 快速大概估算** (Basic: quick approximate estimate) selected.
In **餐食描述** (Meal description), enter:

```text
一份番茄炒蛋，两个水煮鸡蛋
```

Meaning: “One serving of tomato and scrambled eggs, and two boiled eggs.” Click
**开始估算** (Estimate). If a previous record is displayed, first click
**新的一餐** (New meal).

![Basic mode with the Chinese meal description entered](images/01-enter-meal.jpg)

**Check:** the page shows **138 ingredients and 250 reference recipes**. This is
the Qwen product workflow, not the separate six-food offline engineering fixture.
The header's **退出登录** (Log out) button belongs to the optional public gateway;
there is no need to use it in this directly accessible local application.

## 2. Review the Basic estimate and its assumptions

Wait for **待核对确认** (Awaiting review and confirmation). Read the four cards
and the assumptions below them before accepting the result.

In the illustrated run, the app interpreted the meal as **200 g of cooked
tomato-and-egg dish plus 100 g of edible boiled eggs**, using reference serving
weights. The result was:

| Calories | Protein | Fat | Carbohydrates |
| ---: | ---: | ---: | ---: |
| 365.2 kcal | 23.3 g | 25.5 g | 10 g |

![Basic estimate with reference portions, recipe assumptions and nutrition sources](images/02-basic-estimate.jpg)

**Check:** the assumed weights and recipe are visible, not presented as quantities
the user measured. The dish details identify the whole-batch recipe and data
sources. Basic mode gives a quick estimate from limited information; it does not
prove that the reference portion matches the real meal.

For this walkthrough, **do not confirm yet**. Click
**切换到进阶版补充细节** (Switch to Advanced and add details).

## 3. Answer the Advanced questions

The app asks about information not yet supplied or confirmed. Enter **200 g** for
the cooked dish and **100 g** for the edible boiled eggs, excluding their shells.
Select the matching cooked-weight/preparation options when asked. Review any
uncertainty confirmation before checking it.

For the tomato-and-egg recipe, the illustrated run retained these **whole-batch**
reference values:

| Field | Value used in this example |
| --- | ---: |
| Raw tomato | 300 g |
| Raw whole egg | 150 g |
| Cooking oil | 15 g |
| Sugar | 5 g |
| Salt | 2 g |
| Finished whole-batch weight | 400 g |

The **200 g eaten portion** is separate from the **400 g finished batch**. The
15 g oil value is for the whole batch, not additional oil for the eaten portion.
Edit these fields when they do not match the meal being estimated.

Tick **我接受以上配方和成品重量作为本次估算依据** (Accept this recipe and finished
batch weight as the basis of this estimate), then click **提交回答** (Submit
answers). Submit any remaining requested answers until the result is ready.

![Advanced clarification form for weights, preparation and the editable batch recipe](images/03-advanced-questions.jpg)

**Check:** unresolved required questions leave nutrient totals empty. The app
must not silently treat Basic defaults as facts supplied by the user. The exact
questions and their order may vary with the extracted information.

## 4. Correct the eaten portion in conversation

Before confirming, use **继续对话／补充或更正** (Continue the conversation / add or
correct details). Enter:

```text
番茄炒蛋实际吃了150克熟重，水煮鸡蛋可食部分还是100克。
```

Meaning: “I actually ate 150 g cooked tomato and scrambled eggs; the edible
boiled-egg portion is still 100 g.” Click **发送补充说明** (Send the additional
information).

![Conversation correction changing the cooked dish portion to 150 grams](images/04-weight-correction.jpg)

**Check:** the correction changes the dish portion while keeping the boiled eggs
at 100 g. Qwen reinterprets the conversation, so the app can ask for recipe
approval again. Review and accept the same reference batch only if that is what
you intend to use; answer any remaining questions before proceeding.

## 5. Review the corrected estimate

Read **本餐营养估算** (Nutrition estimate for this meal) again. In the illustrated
run, the corrected interpretation was **150 g of cooked tomato-and-egg dish plus
100 g of edible boiled eggs**, with the same accepted batch recipe:

| Calories | Protein | Fat | Carbohydrates |
| ---: | ---: | ---: | ---: |
| 312.7 kcal | 20.6 g | 21.8 g | 7.8 g |

![Recalculated estimate after correcting the portion and approving the recipe](images/05-corrected-estimate.jpg)

**Check:** the interpreted dish portion is now 150 g; the result and recipe
details reflect that change. The original description can remain visible at the
top because the correction is part of the saved conversation. Read the current
interpretation and details, not only the original text box.

These numbers illustrate this particular recipe and interpretation. If a new run
differs, compare food mappings, quantities, assumptions and accepted recipe values
before deciding whether there is an error. Then click **确认并保存** (Confirm
and save).

## 6. Reload and verify the confirmed record

Refresh the browser after confirmation. Verify that **已确认保存** (Confirmed
and saved), the same record ID, and the same final totals remain visible.

![Confirmed Advanced-mode meal restored after reloading, with editing controls hidden](images/06-confirmed-after-reload.jpg)

**Check:** the confirmation button, conversation correction form and mode switch
are no longer available. The page says that further changes require **新的一餐**
(New meal). Confirmation locks the reviewed record; reloading reads the saved
result rather than creating another estimate.

The browser remembers the last viewed meal ID. This branch has no independent
accounts or personal history list. A reviewer can copy the displayed ID and
inspect `GET /analyses/{id}` in http://localhost:8003/docs.

## Optional: use the English interface

Select **English** in the header. The same workflow is available with English
controls, clarification forms, food display names and recipe explanations. Select
**中文** to switch back. Unsent answers stay in their fields, and the browser
remembers the selected language after reloading.

This additional screenshot uses a separate synthetic record to show the current
language controls; it does not replace the six-step meal sequence above.

![English interface with the language controls in the header](images/07-english-interface.png)

See the [language-switch verification](../docs/evidence/ui-language-verification.md)
for the form-preservation and confirmation checks. User descriptions and free-form
model notes retain their original wording, and switching language does not change
the model's food-recognition behavior.

## What to inspect beyond the pictures

- Follow the [full walkthrough](WALKTHROUGH.md) for the English control guide,
  internal responsibilities, state transitions and limitations.
- Run the [separate offline integration check](README.md#3-optional-offline-engineering-check)
  to inspect actual API responses, PostgreSQL rows, worker logs, correction,
  confirmation and locked edits without a Qwen key.
- Treat screenshots as illustrations of an observed run. They do not replace
  running the application, and they do not establish that every live model call
  succeeds. Record provider failures separately rather than substituting an
  offline result for a Chinese estimate.
