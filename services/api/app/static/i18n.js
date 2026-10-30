/* Presentation-only language support. Original meal facts are never translated in storage. */
(() => {
  'use strict';
  const strings = {
    title: ['NutriChat · 中餐营养估算', 'NutriChat · Meal nutrition estimates'],
    language: ['界面语言', 'Interface language'],
    logout: ['退出登录', 'Log out'],
    heading: ['说说这餐吃了什么', 'What did you eat?'],
    introduction: ['基础版快速了解大概热量；进阶版补充份量、做法和配方，细化营养估算。', 'Use Basic for a quick estimate, or add portions, cooking details and recipes in Advanced.'],
    chooseMode: ['选择估算模式', 'Estimation mode'],
    basicOption: ['基础版 · 快速大概估算', 'Basic · Quick estimate'],
    advancedOption: ['进阶版 · 补充细节精算', 'Advanced · Add details'],
    basic: ['基础版', 'Basic'], advanced: ['进阶版', 'Advanced'],
    basicHelp: ['按已有信息估算；缺少份量和配方时使用明确标注的参考值。', 'Estimate from the information available. Missing portions and recipes use clearly labelled reference values.'],
    advancedHelp: ['逐项追问不明确的重量、生熟状态、做法和用油；配方可自行填写和调整。', 'Answer questions about weight, raw or cooked state, preparation and oil. Review and edit the recipe.'],
    switchAdvanced: ['切换到进阶版补充细节', 'Switch to Advanced and add details'],
    switchBasic: ['切换到基础版快速估算', 'Switch to Basic for a quick estimate'],
    mealLabel: ['餐食描述', 'Meal description'],
    mealPlaceholder: ['例如：番茄炒蛋200克，少油，配150克熟米饭。', 'For example: 200g tomato-and-egg stir-fry with 150g cooked white rice.'],
    estimate: ['开始估算', 'Estimate meal'], newMeal: ['新的一餐', 'New meal'],
    catalogueCount: ['{ingredients}种食材 · {recipes}道参考菜谱', '{ingredients} ingredients · {recipes} reference recipes'],
    supportedFoods: ['查看支持的食材和菜谱', 'Browse supported foods and recipes'],
    searchPlaceholder: ['搜索食物／菜名', 'Search foods or dishes'], searchLabel: ['搜索食物', 'Search foods'],
    noFoods: ['没有找到匹配的食物。试试其他名称。', 'No matching foods. Try another name.'],
    referenceRecipe: ['参考菜谱', 'Reference recipe'],
    catalogueRecipe: ['{method}；配料及成品重量可在估算时修改。', '{method}. You can edit ingredients and the finished batch weight during estimation.'],
    catalogueIngredient: ['每100g：{calories} kcal，蛋白质 {protein}g，脂肪 {fat}g，碳水 {carbs}g。来源：USDA SR Legacy #{fdc}，CC0。', 'Per 100g: {calories} kcal, protein {protein}g, fat {fat}g, carbohydrates {carbs}g. Source: USDA SR Legacy #{fdc}, CC0.'],
    dialogue: ['餐食对话', 'Meal conversation'],
    basicDialogue: ['餐食记录与补充', 'Meal record and corrections'],
    advancedDialogue: ['进阶版 · 补充餐食信息', 'Advanced · Add meal details'],
    history: ['查看本餐对话记录', 'View this meal’s conversation'],
    originalHistory: ['你输入的描述及模型自由文本保留原文。', 'Your descriptions and free-form model notes stay in their original language.'],
    you: ['你', 'You'], answerSubmit: ['提交回答', 'Submit answers'],
    answerHelp: ['可以先回答已知的问题。不知道用量时，请在下方说明。', 'Answer what you know first. If a quantity is unknown, explain it below.'],
    replyLabel: ['继续对话／补充或更正', 'Continue · Add or correct details'],
    replyPlaceholder: ['例如：其实是煎蛋，150克是熟重；我这一份额外用了5克油。', 'For example: the eggs were fried; 150g is the cooked weight, and this portion had 5g extra oil.'],
    replySubmit: ['发送补充说明', 'Send details'], resultHeading: ['本餐营养估算', 'Nutrition estimate'],
    calories: ['热量 · kcal', 'Energy · kcal'], protein: ['蛋白质 · g', 'Protein · g'],
    fat: ['脂肪 · g', 'Fat · g'], carbs: ['碳水 · g', 'Carbohydrates · g'],
    reviewHelp: ['请核对食用重量、做法、用油及配方。需要修改时，在上方继续对话。', 'Review the eaten weight, preparation, oil and recipe. Use the conversation above to make corrections.'],
    confirmedHelp: ['这份估算已确认保存。需要再次修改，请开始新的一餐。', 'This estimate is confirmed and saved. Start a new meal to make further changes.'],
    confirm: ['确认并保存', 'Confirm and save'], record: ['记录 {id} · 第 {revision} 版', 'Record {id} · Revision {revision}'],
    sources: ['数据来源：', 'Sources: '],
    disclaimer: ['参考估算会受到原料、烹调失水及实际摄入油量影响。生重与熟重不自动互换；菜谱默认用量须经你确认。所有重量均指可食部分。', 'Estimates vary with ingredients, cooking losses and oil actually consumed. Raw and cooked weights are not converted automatically. Review reference recipe quantities. All weights refer to edible portions.'],
    queued: ['正在分析…', 'Analysing…'], needs_input: ['等待补充信息', 'More details needed'],
    completed: ['待核对确认', 'Ready for review'], failed: ['暂未完成', 'Estimate unavailable'],
    confirmed: ['已确认保存', 'Confirmed and saved'],
    parsing: ['正在解析并检查缺失信息…', 'Reading the meal and checking for missing details…'],
    needsInputMessage: ['还需要这些信息，回答后会继续估算。', 'Please answer these questions to continue the estimate.'],
    unsupportedMessage: ['以下食物没有对应记录，本餐暂不提供营养估算。请核对名称或补充实际食材。', 'Some foods below have no corresponding records, so this meal has no nutrition estimate. Check their names or describe the actual ingredients.'],
    unsupportedFood: ['数据库未找到“{name}”的对应食物记录，暂不能估算。请核对菜名，或在下方提供实际食材及各自克数；不会使用其他食物代替。', '{name}: no corresponding food record was found, so it cannot be estimated. Check the name or provide the actual ingredients and their gram weights below. Other foods will not be substituted.'],
    failedMessage: ['估算暂未完成，请补充描述后重试。', 'The estimate could not be completed. Add details and try again.'],
    savedMessage: ['估算已保存，请核对后确认。', 'The estimate is saved. Review it before confirming.'],
    confirmedMessage: ['这餐的估算已确认并保存。', 'This meal estimate is confirmed and saved.'],
    refreshRecovery: ['刷新页面可恢复记录。', 'Reload the page to restore the record.'],
    demoMessage: ['当前为演示模式，仅支持原有英文克数输入；中餐对话需配置千问。', 'Offline demo: use the supported English food names with grams. Configure Qwen for the Chinese meal and dialogue workflow.'],
    select: ['请选择', 'Please select'], grams: [' 克', ' g'], checked: [' 我已核对并确认', ' I have reviewed and confirmed this'],
    method: ['参考做法：{method}', 'Reference preparation: {method}'],
    ingredientBatch: ['{name}（克／整锅）', '{name} (g / whole batch)'],
    batchYield: ['整锅做熟后的成品总重（克）', 'Total finished cooked batch weight (g)'],
    acceptRecipe: [' 我接受以上配方和成品重量作为本次估算依据', ' I accept this recipe and finished batch weight as the basis of this estimate'],
    modelNote: ['模型原文：{text}', 'Model note (original): {text}'],
    originalNote: ['{text}', 'Original note: {text}'],
    genericError: ['请求失败', 'Request failed'],
    signInAgain: ['请重新登录', 'Please log in again'],
    connection: ['连接暂时不可用，请稍后重试', 'The connection is unavailable. Please try again.'],
    fillRecipe: ['请填完整配方数值，零用量请填 0', 'Fill in all recipe quantities. Enter 0 for an ingredient you do not use.'],
    fillYield: ['请填成品总重', 'Enter the finished batch weight.'],
    answerOne: ['请至少回答一个问题，或使用下方对话补充。', 'Answer at least one question, or add details in the conversation below.'],
    ingredientBuild: ['按实际食材估算', 'Build from actual ingredients'],
    ingredientEdit: ['编辑食材配方：{name}', 'Edit ingredient recipe: {name}'],
    ingredientRecipeRecorded: ['已确认自定义食材配方：{name}', 'Custom ingredient recipe reviewed: {name}'],
    ingredientBuilderTitle: ['按实际食材填写配方', 'Build an ingredient recipe'],
    ingredientBuilderTarget: ['仅替换第 {index} 项“{name}”；其他餐食条目会保留。', 'Replace only item {index}, “{name}”. The other meal items remain unchanged.'],
    ingredientBuilderHelp: ['逐项选择实际食材及其生熟状态，填写克数。油、糖和酱料也要单独填写；没有对应记录的食材不能用相近食物替代。', 'Select each actual ingredient and its raw/cooked state, then enter grams. Include oil, sugar and sauces as separate rows. Do not substitute a similar food for an ingredient with no matching record.'],
    ingredientRecipeName: ['本次配方名称', 'Recipe name for this meal'],
    ingredientBasis: ['这些用量代表什么？', 'What do these amounts describe?'],
    ingredientConsumed: ['本次实际吃下的食材用量', 'Ingredient amounts actually consumed'],
    ingredientBatchBasis: ['整锅配料，再填写本次吃下多少', 'Whole-batch ingredients, then my eaten portion'],
    ingredientConsumedHelp: ['填写本次吃下的各食材用量，重量须符合所选条目的生熟状态。食材重量之和不代表菜肴做熟后的总重。', 'Enter ingredient amounts actually consumed, using each selected record’s raw/cooked weight basis. Their sum is not the finished cooked dish weight.'],
    ingredientBatchHelp: ['填写整锅全部配料、做熟后的成品总重，以及本次吃下的熟重。按食用比例分摊，假设食材在整锅中分布均匀；不自动扣除弃掉的油或汤汁。', 'Enter all batch ingredients, finished cooked batch weight and cooked portion eaten. Nutrition scales by that fraction, assuming an even mixture. Discarded oil or broth is not deducted automatically.'],
    ingredientRows: ['食材及克数', 'Ingredients and gram weights'],
    ingredientAdd: ['添加食材', 'Add ingredient'],
    ingredientSearch: ['搜索第 {index} 项食材', 'Search ingredient {index}'],
    ingredientSelect: ['选择第 {index} 项食材及状态', 'Select ingredient {index} and state'],
    ingredientGrams: ['第 {index} 项食材重量（克）', 'Ingredient {index} weight (g)'],
    ingredientRemove: ['移除第 {index} 项食材', 'Remove ingredient {index}'],
    ingredientState: ['重量依据：{state}', 'Weight basis: {state}'],
    stateRaw: ['烹调前生可食重量', 'raw edible weight before cooking'],
    stateCooked: ['熟制可食重量', 'cooked edible weight'],
    stateAsSold: ['可食部分净重', 'net edible weight as sold'],
    ingredientEatenWeight: ['本次吃下的熟制可食重量（克）', 'Cooked edible portion eaten (g)'],
    ingredientAccept: [' 我已核对食材、生熟状态及用量，并确认这些食材完整描述这一项食物。', ' I reviewed the ingredients, their raw/cooked states and amounts, and confirm they completely describe this meal item.'],
    ingredientCalculate: ['按这些食材计算', 'Calculate from these ingredients'],
    cancel: ['取消', 'Cancel'],
    ingredientNameRequired: ['请填写本次配方名称。', 'Enter a name for this ingredient recipe.'],
    ingredientChooseRequired: ['请逐项选择数据库中的实际食材。搜索文字不代表已选中食材。', 'Select an actual catalogue ingredient for every row. Search text alone does not select a food.'],
    ingredientWeightRequired: ['每项食材重量须大于 0 且不超过 10000 克。', 'Each ingredient weight must be greater than 0 and no more than 10000 g.'],
    ingredientDuplicate: ['同一种食材请合并为一项，避免重复计算。', 'Combine duplicate ingredients into one row to avoid double counting.'],
    ingredientBatchInvalid: ['请填写有效的成品总重和食用克数（均大于 0，不超过 10000）；食用量不能超过整锅总重。', 'Enter valid finished batch and eaten weights (greater than 0, up to 10000 g). The eaten portion cannot exceed the batch.'],
    ingredientAcceptRequired: ['请先核对并勾选食材及用量确认。', 'Review the ingredients and amounts, then check the confirmation box.'],
    ingredientStale: ['记录版本已变化，填写内容已保留。请先记下这些用量，再刷新页面重新读取记录。', 'This record changed. Your entries are preserved here. Note these amounts before reloading the current record.'],
    customRecipeGuidance: ['本餐含自定义食材配方。请使用“编辑食材配方”更改用量，或开始新的一餐；其他待回答的问题仍可逐项填写。', 'This meal includes a custom ingredient recipe. Use “Edit ingredient recipe” to change it, or start a new meal. You can still answer other pending questions individually.'],
    customRecipeTitle: ['自定义食材配方：{name}', 'User-defined ingredient recipe: {name}'],
    customIngredientSum: ['食材重量合计 {grams}g（非成品熟重）', 'Ingredient weight sum {grams}g (not finished cooked weight)'],
    customConsumedWeight: ['本次熟制食用量 {grams}g', 'Cooked portion eaten: {grams}g'],
    customBatchEvidence: ['用户填写：整锅成品 {yield}g，本次吃下 {consumed}g；按 {percent}% 分摊营养。', 'User supplied: finished batch {yield}g, portion eaten {consumed}g; allocating {percent}% of batch nutrition.'],
    customConsumedEvidence: ['用量依据：用户逐项填写本次实际摄入的食材克数。未采用默认份量。', 'Quantity basis: user-entered ingredient grams actually consumed. No default portion was used.'],
    customIngredientEvidence: ['{name}：{grams}g · {state}', '{name}: {grams}g · {state}'],
    quantityUser: ['份量依据：从餐食描述提取的克数为 {grams}g；请核对提取结果、可食部分及生熟状态。', 'Quantity basis: {grams}g extracted from your description. Review the extracted amount, edible portion and raw/cooked state.'],
    quantityPortion: ['份量依据：按 {count} 份／个数及每份 {reference}g 的参考换算，共 {grams}g；不是实测重量。', 'Quantity basis: {count} portions/counts × reference {reference}g = {grams}g; not a measured weight.'],
    quantityDefault: ['份量依据：未提供克数，使用默认参考份量 {grams}g。', 'Quantity basis: grams were not supplied; using a default reference portion of {grams}g.'],
    quantityEdible: ['份量依据：总重 {input}g 按参考可食比例换算为 {grams}g；请核对实际净重。', 'Quantity basis: gross {input}g converted to {grams}g using an assumed edible fraction. Review the actual edible weight.']
  };
  const storageGet = key => { try { return localStorage.getItem(key); } catch (_) { return null; } };
  const storageSet = (key, value) => { try { localStorage.setItem(key, value); } catch (_) { /* Memory-only preference is still usable. */ } };
  const storageRemove = key => { try { localStorage.removeItem(key); } catch (_) { /* Storage may be unavailable. */ } };
  let language = storageGet('nutrichat.language') === 'en' ? 'en' : 'zh-CN';
  let foods = new Map();
  let namePairs = [];
  const english = () => language === 'en';
  const catalogue = () => window.NUTRICHAT_EN_CATALOGUE || {};
  function t(key, values = {}) {
    const pair = strings[key];
    const template = pair ? pair[english() ? 1 : 0] : key;
    return template.replace(/\{(\w+)\}/g, (match, name) => values[name] ?? match);
  }
  function setLanguage(value) {
    language = value === 'en' ? 'en' : 'zh-CN';
    storageSet('nutrichat.language', language);
    return language;
  }
  function setCatalogue(values) {
    foods = new Map(values.map(food => [food.id, food]));
    namePairs = values.filter(food => catalogue()[food.id]?.name)
      .map(food => [food.name, catalogue()[food.id].name]).sort((a, b) => b[0].length - a[0].length);
  }
  function foodName(id, fallback = '') {
    return english() ? (catalogue()[id]?.name || fallback || id || '') : (foods.get(id)?.name || fallback || id || '');
  }
  function method(id, fallback = '') {
    return english() ? (catalogue()[id]?.method || systemText(fallback)) : fallback;
  }
  function translatedNames(text) {
    let result = String(text ?? '');
    // Match longest catalogue names once, rather than translating substrings repeatedly.
    if (!namePairs.length) return result;
    const escape = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(namePairs.map(pair => escape(pair[0])).join('|'), 'g');
    const names = new Map(namePairs);
    return result.replace(pattern, name => names.get(name));
  }
  const preparations = {
    as_served: 'As described by the selected food', raw: 'Raw', boiled: 'Boiled',
    steamed: 'Steamed', roasted: 'Roasted', stir_fried: 'Stir-fried', fried: 'Pan-fried / deep-fried',
    braised: 'Stewed / braised', other: 'Other preparation'
  };
  const states = {raw: 'raw edible weight before cooking', cooked: 'cooked edible weight', as_sold: 'net edible weight as sold'};
  function questionLabel(q, draft = []) {
    if (!english()) return q.label;
    const [index, field] = q.key.split('.');
    const item = draft[Number(index)] || {};
    const name = foodName(item.food_id, item.name || 'This food');
    if (q.kind === 'unsupported') return t('unsupportedFood', {name:item.name || 'This food'});
    if (q.kind === 'recipe') return `${name}: review the reference preparation and whole-batch recipe. You can change ingredient quantities and finished batch weight. These are estimates, not measured amounts for your meal.`;
    if (q.kind === 'food') {
      if (q.label.includes('参考做法')) return `${name}: the reference preparation does not match your description. Select a matching food or explain the raw ingredients and actual preparation below; do not substitute a different cooked food.`;
      return `${name}: no exact food match yet. Select the correct food, or describe the ingredients below if no option fits.`;
    }
    if (field === 'resolved') return `${name}: please review the selected food and the model note below, or correct the description in the conversation.`;
    if (field === 'grams') {
      if (item.weight_includes_inedible || q.label.includes('骨头')) return `${name}: the supplied weight includes bones, shells or other inedible parts. Enter the edible grams actually eaten; do not use the gross weight.`;
      return `${name}: how many grams did you eat? Enter the edible portion weight.`;
    }
    if (field === 'weight_basis') {
      if (foods.get(item.food_id)?.kind === 'recipe') return `${name}: is the portion weight the finished cooked edible weight?`;
      const state = foods.get(item.food_id)?.state || q.options?.[0]?.value;
      return `${name}: this record uses ${states[state] || 'the stated food weight'}. Is that the weight you supplied? If not, explain below; raw and cooked weights cannot be interchanged.`;
    }
    if (field === 'preparation') return `${name}: how was it prepared?`;
    if (field === 'oil_g') return `${name}: how many grams of additional oil did you consume in this portion? This is not the whole pot’s oil. Enter 0 if none; describe sugar, sauces and other ingredients below.`;
    return systemText(q.label);
  }
  function questionOption(q, option) {
    if (!english()) return option.label;
    if (q.kind === 'food') return foodName(option.value, option.label);
    const field = q.key.split('.')[1];
    if (field === 'preparation') return preparations[option.value] || systemText(option.label);
    if (field === 'weight_basis') return `Yes, ${states[option.value] || option.value}`;
    return systemText(option.label);
  }
  const exactEnglish = {
    '用户填写并确认的食材配方；不是数据库中的实测菜肴记录。': 'An ingredient recipe supplied and reviewed by the user, not a measured dish record in the database.',
    '食材按所选记录的生重、熟重或可食净重计算，不自动互换。': 'Ingredient weights use the selected raw, cooked or net edible state. These states are not converted automatically.',
    '油、糖及酱料需逐项列入；不自动估计未填写的配料或烹调损耗。': 'List oil, sugar and sauces separately. Unlisted ingredients and cooking losses are not estimated automatically.',
    '本餐包含自定义食材配方，请使用配方编辑器修改，或开始新的一餐。': 'This meal contains a custom ingredient recipe. Edit it in the recipe form, or start a new meal.',
    '找不到要修改的食物，请刷新后重试。': 'The food item to edit was not found. Reload and try again.',
    '请先核对食材、重量状态及用量，并确认配方。': 'Review the ingredients, their weight states and amounts, then confirm the recipe.',
    '同一食材只能添加一次，请合并其克数。': 'Add each ingredient only once; combine its gram weights.',
    '整锅配方需要成品总重和本次食用重量。': 'A whole-batch recipe needs the finished batch weight and the portion eaten.',
    '本次食用重量不能超过整锅成品总重。': 'The portion eaten cannot exceed the finished batch weight.',
    '本次食材用量模式不接受整锅重量；请选择整锅配方模式。': 'Consumed-ingredient mode does not accept batch weights. Select whole-batch mode instead.',
    '请选择目录中已有的食材记录；不能使用未知食物或整道参考菜谱。': 'Select existing ingredient records. Unknown foods and whole reference dishes cannot be used as ingredients.',
    '基础版快速参考估算': 'Basic-mode reference estimate',
    '基础版暂用参考配方及整锅成品重量；未逐项核实，可切换进阶版修改。': 'Basic mode uses a reference recipe and finished batch weight that have not been checked item by item. Switch to Advanced to review them.',
    '基础版参考配方，未经逐项确认；不是实测菜肴营养。': 'Basic reference recipe, not confirmed item by item. This is not measured nutrition for your dish.',
    '参考配方已由用户确认；不是实测菜肴营养。': 'The user confirmed the reference recipe. This is not measured nutrition for the dish.',
    '烹调失水不自动换算；额外糖、酱料需作为食材补充。': 'Cooking losses are not converted automatically. Add extra sugar and sauces as separate ingredients.',
    '做法不明确，暂按所选食材条目的加工状态计算；未另加烹调油。': 'Preparation was not specified. Using the selected food record’s state, with no extra cooking oil added.',
    '未提供摄入油量，暂额外计入这一份食用油 10g。': 'Consumed oil was not provided. This portion provisionally includes 10g of extra cooking oil.',
    '份量过大，请填写实际克数。': 'The portion is too large. Please enter the actual grams.',
    '记录已更新，请刷新后回答。': 'This record has changed. Reload before answering.',
    '本次对话较长，请整理餐食描述后重新估算。': 'This conversation is long. Summarise the meal and start a new estimate.',
    '对话资料过长，请整理后开始新餐食。': 'The conversation is too long. Summarise it and start a new meal.',
    '回答已过期或字段不正确，请刷新后重试。': 'These answers are out of date or invalid. Reload and try again.',
    '请选择提供的选项。': 'Choose one of the supplied options.',
    '没有对应的食物记录，请通过下方对话更正菜名或提供实际食材。': 'No corresponding food record was found. Use the conversation below to correct the name or provide the actual ingredients.',
    '重量必须是数字。': 'Weight must be a number.',
    '重量超出允许范围。': 'Weight is outside the allowed range.',
    '请确认或补充说明。': 'Please confirm or provide more details.',
    '请提供完整配方和成品重量。': 'Provide the complete recipe and finished batch weight.',
    '配方食材不匹配；新增食材请通过对话补充。': 'The recipe ingredients do not match. Add new ingredients through the conversation.',
    '配料重量必须在 0 到 10000 克之间。': 'Ingredient weights must be between 0 and 10000 grams.',
    '成品和配料总重必须大于 0。': 'Finished batch weight and total ingredient weight must be greater than 0.',
    '估算服务暂时不可用，请重试或补充更清楚的餐食描述。': 'The estimation service is temporarily unavailable. Try again or provide a clearer meal description.',
    '千问服务暂时不可用，请稍后重试。': 'Qwen is temporarily unavailable. Please try again later.',
    '千问返回的数据格式不正确，请重试或简化餐食描述。': 'Qwen returned an invalid response. Try again or simplify the meal description.',
    '已核对配方及成品重量': 'Recipe and finished batch weight reviewed',
    '确认': 'Confirmed',
    '生食': 'Raw', '按所选食物的加工状态': 'As described by the selected food',
    '水煮': 'Boiled', '清蒸': 'Steamed', '烤': 'Roasted', '炒': 'Stir-fried',
    '煎／炸': 'Pan-fried / deep-fried', '炖／红烧': 'Stewed / braised', '其他做法': 'Other preparation',
    '烹调前的生重': 'raw edible weight before cooking', '熟重': 'cooked edible weight', '可食部分净重': 'net edible weight',
    '生可食重量': 'raw edible weight', '熟可食重量': 'cooked edible weight', '可食净重': 'net edible weight'
  };
  for (const pair of Object.values(strings)) exactEnglish[pair[0]] = pair[1];
  const exactChinese = Object.fromEntries(Object.entries(exactEnglish).map(([zh, en]) => [en, zh]));
  Object.assign(exactChinese, {
    'Analysis not found': '未找到这份餐食记录',
    'State or revision changed; reload the estimate.': '记录状态或版本已变化，请重新读取估算。',
    'Failed to fetch': '网络连接失败，请稍后重试。', 'Load failed': '网络连接失败，请稍后重试。'
  });
  function assumption(text, foodId) {
    if (!english()) return text;
    if (exactEnglish[text]) return exactEnglish[text];
    let m;
    if (text.startsWith('待核实：')) return t('modelNote', {text: text.slice(4)});
    if (text.startsWith('参考做法：')) return t('method', {method: method(foodId, text.slice(5))});
    if (text.startsWith('整锅配料：')) return 'Whole-batch ingredients: ' + translatedNames(text.slice(5)).replaceAll('、', ', ');
    if ((m = text.match(/^整锅成品 (.+)g；本次食用 (.+)g$/))) return `Finished batch: ${m[1]}g; portion eaten: ${m[2]}g`;
    if ((m = text.match(/^按 (.+) 的每100g可食部分数据计算$/))) return `Calculated from the edible-portion data per 100g of ${foodName(foodId, translatedNames(m[1]))}.`;
    if ((m = text.match(/^做法：(.+)；另计食用油 (.+)g$/))) return `Preparation: ${exactEnglish[m[1]] || m[1]}; additional oil: ${m[2]}g`;
    if ((m = text.match(/^未说明重量状态，暂按(.+)计算。$/))) return `Weight state was not specified. Provisionally using ${exactEnglish[m[1]] || m[1]}.`;
    if ((m = text.match(/^未提供克数，暂按 (.+) (碗|个|杯|份)、每(?:碗|个|杯|份) (.+)g，共 (.+)g 估算。$/))) {
      const unit = {碗:'bowl(s)', 个:'piece(s)', 杯:'cup(s)', 份:'serving(s)'}[m[2]];
      return `Grams were not provided. Assuming ${m[1]} ${unit}, ${m[3]}g each, ${m[4]}g in total.`;
    }
    if ((m = text.match(/^提供的 (.+)g 含骨或壳，基础版暂按 60% 可食比例，估算可食重量 (.+)g；这是粗略假设，并非实测去骨率，可在进阶版填写实际净重。$/))) return `The supplied ${m[1]}g includes bones or shells. Basic mode assumes 60% is edible (${m[2]}g). This is a rough assumption, not a measured edible yield. Enter the actual net weight in Advanced.`;
    return systemText(text);
  }
  function generatedQuestion(text) {
    let m;
    if ((m = text.match(/^数据库未找到“(.+)”的对应食物记录，暂不能估算。请核对菜名，或在下方提供实际食材及各自克数；不会使用其他食物代替。$/))) return t('unsupportedFood', {name:m[1]});
    if ((m = text.match(/^“(.+)”没有对应的食物记录，暂不能估算。请核对菜名，或在下方提供实际食材及各自克数；不会使用其他食物代替。$/))) return t('unsupportedFood', {name:m[1]});
    if ((m = text.match(/^(.+)吃了多少克？请填可食部分重量。$/))) return `${translatedNames(m[1])}: how many grams did you eat? Enter the edible portion weight.`;
    if ((m = text.match(/^(.+)是什么做法？$/))) return `${translatedNames(m[1])}: how was it prepared?`;
    if ((m = text.match(/^(.+)的食用克数是做熟后的成品重量吗？$/))) return `${translatedNames(m[1])}: is the portion weight the finished cooked edible weight?`;
    if ((m = text.match(/^(.+)采用以下参考做法和整锅配方吗？可修改配料克数及成品总重。这些是估算假设，不代表你的实际用量。$/))) return `${translatedNames(m[1])}: review the reference preparation, whole-batch ingredients and finished batch weight. These are assumptions, not your measured quantities.`;
    if ((m = text.match(/^(.+)的数据按(.+)计算，你提供的是这个重量吗？若不是，请在下方说明，不能将生熟重量直接互换。$/))) return `${translatedNames(m[1])}: this record uses ${exactEnglish[m[2]] || m[2]}. Confirm that weight basis or explain below; raw and cooked weights cannot be interchanged.`;
    if ((m = text.match(/^(.+)这一份实际吃进去的额外油脂有多少克？不是整锅用油量；无额外油填 0。糖、酱料及其他配料请在下方补充。$/))) return `${translatedNames(m[1])}: how many grams of additional oil were consumed in this portion, not the whole pot? Enter 0 if none. Add sugar, sauces and other ingredients below.`;
    if ((m = text.match(/^(.+)提供的重量包含骨头、壳等不可食部分。请填写实际吃下的可食部分克数，不能直接按带骨或带壳重量计算。$/))) return `${translatedNames(m[1])}: the weight includes bones or shells. Enter the edible grams actually eaten, not the gross weight.`;
    if ((m = text.match(/^“(.+)”尚未匹配。请选择准确食物；没有合适选项请用下方对话补充食材。$/))) return `${m[1]}: no exact food match yet. Select the correct food or describe its ingredients below.`;
    if ((m = text.match(/^(.+)的参考做法与你描述的不一致。请选择吻合的食物条目，或在下方说明原料生重及实际做法，不能套用另一种熟制数据。$/))) return `${translatedNames(m[1])}: the reference preparation does not match. Select the right food or explain the raw ingredients and preparation; do not use a different cooked record.`;
    if ((m = text.match(/^(.+)：(.+) 请核对所选食物，或在下方补充更正。$/))) return `${translatedNames(m[1])}: review the selected food or correct it below. Model note (original): ${m[2]}`;
    return null;
  }
  function systemText(text) {
    const value = String(text ?? '');
    if (value.startsWith('Value error, ')) return systemText(value.slice('Value error, '.length));
    if (!english()) return exactChinese[value] || value;
    if (exactEnglish[value]) return exactEnglish[value];
    if (value.includes('\n')) return value.split('\n').map(systemText).join('\n');
    const question = generatedQuestion(value);
    if (question) return question;
    if (!/[\u3400-\u9fff]/.test(value)) return value;
    return t('originalNote', {text:value});
  }
  function structuredReply(message) {
    if (!english()) return message.display || message.content;
    // Structured answers are machine-generated records. User prose is never run through this path.
    try {
      const start = message.content.indexOf('{');
      const end = message.content.indexOf('\n当前餐食资料：');
      const answers = JSON.parse(message.content.slice(start, end < 0 ? undefined : end));
      const names = {grams:'Edible grams', weight_basis:'Weight basis', preparation:'Preparation', oil_g:'Extra oil (g)', resolved:'Food reviewed', recipe:'Recipe', food_id:'Selected food'};
      const parts = Object.entries(answers).map(([key,value]) => {
        const [index,field] = key.split('.');
        let shown = value;
        if (field === 'recipe') shown = 'Ingredients: ' + Object.entries(value.ingredients).map(([id,g]) => `${foodName(id,id)} ${g}g`).join(', ') + `; finished batch ${value.yield_g}g`;
        else if (field === 'food_id') shown = foodName(value,value);
        else if (field === 'preparation') shown = preparations[value] || value;
        else if (field === 'weight_basis') shown = states[value] || value;
        else if (value === true) shown = 'Confirmed';
        return `Item ${Number(index)+1} · ${names[field] || field}: ${shown}`;
      });
      return 'Answers supplied:\n' + parts.join('\n');
    } catch (_) { return t('originalNote', {text:message.display || message.content}); }
  }
  window.NutriI18n = {getLanguage:()=>language, setLanguage, setCatalogue, t, foodName, method,
    questionLabel, questionOption, assumption, systemText, structuredReply,
    storageGet, storageSet, storageRemove};
})();
