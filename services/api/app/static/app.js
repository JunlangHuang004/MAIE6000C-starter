/* The UI language changes presentation only; API payloads and saved facts stay unchanged. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const I = window.NutriI18n;
  let analysis = null, busy = false, timer = null, catalogue = [];
  let questionVersion = '', notice = {raw:'', error:false};
  let ingredientEditor = null;
  const el = (tag, text) => {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    return element;
  };
  function message(value, error = false) {
    notice = typeof value === 'string' ? {raw:value,error} : {...value,error};
    renderMessage();
  }
  function renderMessage() {
    let value = notice.key ? I.t(notice.key, notice.values) : I.systemText(notice.raw || '');
    if (notice.recovery) value += ' ' + I.t('refreshRecovery');
    $('message').textContent = value;
    $('message').classList.toggle('error', notice.error);
  }
  function applyStaticLanguage() {
    document.documentElement.lang = I.getLanguage();
    document.title = I.t('title');
    document.querySelectorAll('[data-i18n]').forEach(node => { node.textContent = I.t(node.dataset.i18n); });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(node => { node.placeholder = I.t(node.dataset.i18nPlaceholder); });
    document.querySelectorAll('[data-i18n-label]').forEach(node => { node.setAttribute('aria-label', I.t(node.dataset.i18nLabel)); });
    $('language-zh').setAttribute('aria-pressed', String(I.getLanguage() === 'zh-CN'));
    $('language-en').setAttribute('aria-pressed', String(I.getLanguage() === 'en'));
    catalogueInfo();
    modeHelp();
    renderMessage();
  }
  function changeLanguage(language) {
    I.setLanguage(language);
    applyStaticLanguage();
    render();
    translateIngredientEditor();
    showFoods();
  }
  async function api(path, method = 'GET', body) {
    const response = await fetch(path, {
      method, headers:{'Content-Type':'application/json'},
      ...(body ? {body:JSON.stringify(body)} : {})
    });
    if (response.redirected && new URL(response.url).pathname === '/login') {
      location.href = '/login';
      throw Error('请重新登录');
    }
    if (!(response.headers.get('content-type') || '').includes('application/json')) {
      throw Error('连接暂时不可用，请稍后重试');
    }
    const data = await response.json();
    if (!response.ok) {
      const error = Error(Array.isArray(data.detail)
        ? data.detail.map(item => item.msg).join('\n') : data.detail || '请求失败');
      error.status = response.status;
      throw error;
    }
    return data;
  }
  function controls() {
    const locked = busy || analysis?.status === 'queued';
    $('meal').disabled = locked || !!analysis;
    $('estimate').hidden = !!analysis;
    $('estimate').disabled = locked;
    $('new').hidden = !analysis;
    $('new').disabled = locked;
    for (const id of ['reply-submit','answer-submit']) $(id).disabled = locked;
    const answerable = (analysis?.questions || []).some(q => ['number','choice','food','confirm','recipe'].includes(q.kind));
    $('answer-submit').hidden = !answerable;
    $('answer-submit').disabled = locked || !answerable;
    document.querySelector('[data-i18n="answerHelp"]').hidden = !answerable;
    $('confirm').disabled = locked || analysis?.status !== 'completed' || !!ingredientEditor;
    $('reply').disabled = locked;
    $('mode').disabled = !!analysis || busy;
    $('switch-mode').hidden = !analysis || analysis.status === 'confirmed';
    $('switch-mode').disabled = locked;
    $('switch-mode').textContent = I.t(analysis?.mode === 'basic' ? 'switchAdvanced' : 'switchBasic');
    const recipeLocked = locked || !analysis || analysis.status === 'confirmed';
    document.querySelectorAll('[data-build-ingredients],[data-edit-ingredients]').forEach(button => {
      button.disabled = recipeLocked;
      button.setAttribute('aria-expanded', String(ingredientEditor?.itemIndex === Number(button.dataset.buildIngredients ?? button.dataset.editIngredients)));
    });
    $('ingredient-form').querySelectorAll('input,select,button').forEach(input => { input.disabled = recipeLocked; });
    $('ingredient-add').disabled = recipeLocked || $('ingredient-rows').children.length >= 30;
    $('ingredient-submit').disabled = recipeLocked || !!ingredientEditor?.stale;
    $('ingredient-rows').querySelectorAll('[data-remove-ingredient]').forEach(button => {
      button.disabled = recipeLocked || $('ingredient-rows').children.length <= 1;
    });
    // Language controls remain usable while a model job is pending.
  }
  function numberInput(value, min = 0, max = 10000) {
    const input = el('input');
    input.type = 'number'; input.step = 'any'; input.min = min; input.max = max;
    if (value != null) input.value = value;
    return input;
  }
  function translateQuestions() {
    const questions = new Map((analysis?.questions || []).map(q => [q.key,q]));
    for (const row of $('questions').children) {
      const q = questions.get(row.dataset.key);
      if (!q) continue;
      const item = analysis.draft?.[Number(q.key.split('.')[0])] || {};
      row.querySelector('[data-question-label]').textContent = I.questionLabel(q, analysis.draft);
      const unit = row.querySelector('[data-unit]');
      if (unit) unit.textContent = I.t('grams');
      const select = row.querySelector('select[data-answer]');
      if (select) {
        select.options[0].textContent = I.t('select');
        for (let index = 0; index < q.options.length; index++) {
          select.options[index+1].textContent = I.questionOption(q,q.options[index]);
        }
      }
      const checked = row.querySelector('[data-checked-label]');
      if (checked) checked.textContent = I.t('checked');
      const modelNote = row.querySelector('[data-model-note]');
      if (modelNote) {
        modelNote.hidden = I.getLanguage() !== 'en';
        modelNote.textContent = I.t('modelNote', {text:item.uncertainty || q.label});
      }
      const method = row.querySelector('[data-recipe-method]');
      if (method) method.textContent = I.t('method',{method:I.method(item.food_id,q.method)});
      row.querySelectorAll('[data-ingredient-label]').forEach(label => {
        const ingredient = q.ingredients.find(ing => ing.id === label.dataset.ingredientLabel);
        label.textContent = I.t('ingredientBatch',{name:I.foodName(ingredient.id,ingredient.name)});
      });
      const yieldLabel = row.querySelector('[data-yield-label]');
      if (yieldLabel) yieldLabel.textContent = I.t('batchYield');
      const acceptLabel = row.querySelector('[data-accept-label]');
      if (acceptLabel) acceptLabel.textContent = I.t('acceptRecipe');
      const builder = row.querySelector('[data-build-ingredients]');
      if (builder) builder.textContent = I.t('ingredientBuild');
    }
  }
  function renderQuestions() {
    const signature = analysis.id + ':' + analysis.revision + ':' + JSON.stringify(analysis.questions || []);
    if (signature === questionVersion) {
      translateQuestions();
      return;
    }
    questionVersion = signature;
    const box = $('questions');
    box.replaceChildren();
    for (const q of analysis.questions || []) {
      const row = el('div'); row.className = 'question';
      row.dataset.key = q.key; row.dataset.kind = q.kind;
      const label = el(q.kind === 'unsupported' ? 'p' : 'label'); label.dataset.questionLabel = q.key;
      if (q.kind === 'unsupported') row.classList.add('error');
      row.append(label);
      if (q.kind === 'unsupported') {
        const button = el('button'); button.type = 'button'; button.className = 'secondary';
        button.dataset.buildIngredients = q.key.split('.')[0];
        button.setAttribute('aria-controls','ingredient-builder');
        button.addEventListener('click',() => openIngredientEditor(Number(button.dataset.buildIngredients)));
        row.append(button);
      } else if (q.kind === 'number') {
        const input = numberInput(null,q.min,q.max);
        input.dataset.answer = 'value'; input.id = 'q-' + q.key;
        label.htmlFor = input.id;
        const unit = el('span'); unit.dataset.unit = 'true';
        row.append(input,unit);
      } else if (q.kind === 'choice' || q.kind === 'food') {
        const input = el('select'); input.id = 'q-' + q.key;
        label.htmlFor = input.id; input.dataset.answer = 'value';
        const empty = el('option'); empty.value = ''; input.append(empty);
        for (const option of q.options) {
          const opt = el('option'); opt.value = option.value; input.append(opt);
        }
        row.append(input);
      } else if (q.kind === 'confirm') {
        const input = el('input'); input.type = 'checkbox';
        input.dataset.answer = 'value'; input.id = 'q-' + q.key; label.htmlFor = input.id;
        const checked = el('span'); checked.dataset.checkedLabel = 'true';
        const note = el('p'); note.dataset.modelNote = 'true'; note.className = 'muted';
        row.append(note,input,checked);
      } else if (q.kind === 'recipe') {
        const method = el('p'); method.dataset.recipeMethod = 'true'; row.append(method);
        for (const ingredient of q.ingredients) {
          const line = el('div'); line.className = 'ingredient';
          const input = numberInput(ingredient.grams);
          input.dataset.ingredient = ingredient.id; input.id = 'q-' + q.key + '-' + ingredient.id;
          const ingredientLabel = el('label'); ingredientLabel.htmlFor = input.id;
          ingredientLabel.dataset.ingredientLabel = ingredient.id;
          line.append(ingredientLabel,input); row.append(line);
        }
        const yieldInput = numberInput(q.recipe.yield_g,0.1);
        yieldInput.dataset.yield = 'true'; yieldInput.id = 'yield-' + q.key;
        const yieldLabel = el('label'); yieldLabel.htmlFor = yieldInput.id;
        yieldLabel.dataset.yieldLabel = 'true'; row.append(yieldLabel,yieldInput);
        const accept = el('input'); accept.type = 'checkbox';
        accept.dataset.accept = 'true'; accept.id = 'accept-' + q.key;
        const acceptLabel = el('label'); acceptLabel.htmlFor = accept.id;
        const acceptText = el('span'); acceptText.dataset.acceptLabel = 'true';
        acceptLabel.append(accept,acceptText); row.append(acceptLabel);
      }
      box.append(row);
    }
    translateQuestions();
  }
  function ingredientState(state) {
    return I.t({raw:'stateRaw',cooked:'stateCooked',as_sold:'stateAsSold'}[state] || 'stateAsSold');
  }
  function editorRows() {
    return Array.from($('ingredient-rows').children).map(row => ({
      food_id:row.querySelector('[data-ingredient-food]').value,
      grams:row.querySelector('[data-ingredient-grams]').value,
      search:row.querySelector('[data-ingredient-search]').value
    }));
  }
  function populateIngredientSelect(row) {
    const select = row.querySelector('[data-ingredient-food]');
    const selected = select.value || row.dataset.initialFood || '';
    delete row.dataset.initialFood;
    const search = row.querySelector('[data-ingredient-search]').value.trim().toLowerCase();
    const choices = catalogue.filter(food => food.kind === 'ingredient' && (food.id === selected ||
      [food.name,...(food.aliases || []),I.foodName(food.id,food.name),
        window.NUTRICHAT_EN_CATALOGUE?.[food.id]?.name || ''].join(' ').toLowerCase().includes(search)));
    select.replaceChildren();
    const empty = el('option',I.t('select')); empty.value = ''; select.append(empty);
    for (const food of choices) {
      const option = el('option',I.foodName(food.id,food.name) + ' · ' + ingredientState(food.state));
      option.value = food.id; select.append(option);
    }
    select.value = choices.some(food => food.id === selected) ? selected : '';
    const food = catalogue.find(entry => entry.id === select.value && entry.kind === 'ingredient');
    row.querySelector('[data-ingredient-state]').textContent = food
      ? I.t('ingredientState',{state:ingredientState(food.state)})
      : (choices.length ? I.t('ingredientChooseRequired') : I.t('noFoods'));
  }
  function renderIngredientRows(values) {
    $('ingredient-rows').replaceChildren();
    for (const [index,value] of values.entries()) {
      const row = el('div'); row.className = 'ingredient-row'; row.dataset.initialFood = value.food_id || '';
      const search = el('input'); search.type = 'search'; search.dataset.ingredientSearch = 'true';
      search.value = value.search || ''; search.id = 'ingredient-search-' + index;
      const searchLabel = el('label'); searchLabel.htmlFor = search.id; searchLabel.dataset.ingredientSearchLabel = 'true';
      const select = el('select'); select.dataset.ingredientFood = 'true'; select.id = 'ingredient-food-' + index;
      const selectLabel = el('label'); selectLabel.htmlFor = select.id; selectLabel.dataset.ingredientSelectLabel = 'true';
      const grams = numberInput(value.grams === '' ? null : value.grams,0.1); grams.required = true;
      grams.dataset.ingredientGrams = 'true'; grams.id = 'ingredient-grams-' + index;
      const gramsLabel = el('label'); gramsLabel.htmlFor = grams.id; gramsLabel.dataset.ingredientGramsLabel = 'true';
      const columns = el('div'); columns.className = 'ingredient-row-fields';
      const foodColumn = el('div'), gramsColumn = el('div');
      foodColumn.append(selectLabel,select); gramsColumn.append(gramsLabel,grams); columns.append(foodColumn,gramsColumn);
      const state = el('p'); state.className = 'muted'; state.dataset.ingredientState = 'true';
      const remove = el('button'); remove.type = 'button'; remove.className = 'secondary';
      remove.dataset.removeIngredient = 'true';
      remove.addEventListener('click',() => {
        const rows = editorRows(); if (rows.length <= 1) return;
        rows.splice(index,1); renderIngredientRows(rows); $('ingredient-accepted').checked = false;
      });
      search.addEventListener('input',() => {
        // A changed query is not a new selection, nor permission to retain an old one.
        select.value = ''; $('ingredient-accepted').checked = false;
        populateIngredientSelect(row);
      });
      select.addEventListener('change',() => populateIngredientSelect(row));
      row.append(searchLabel,search,columns,state,remove); $('ingredient-rows').append(row);
    }
    translateIngredientEditor(); controls();
  }
  function translateIngredientEditor() {
    if (!ingredientEditor) return;
    $('ingredient-builder-target').textContent = I.t('ingredientBuilderTarget',{
      index:ingredientEditor.itemIndex + 1,name:ingredientEditor.originalName
    });
    const batch = $('ingredient-basis').value === 'batch';
    $('ingredient-batch-fields').hidden = !batch;
    $('ingredient-basis-help').textContent = I.t(batch ? 'ingredientBatchHelp' : 'ingredientConsumedHelp');
    for (const [index,row] of Array.from($('ingredient-rows').children).entries()) {
      row.querySelector('[data-ingredient-search-label]').textContent = I.t('ingredientSearch',{index:index+1});
      row.querySelector('[data-ingredient-select-label]').textContent = I.t('ingredientSelect',{index:index+1});
      row.querySelector('[data-ingredient-grams-label]').textContent = I.t('ingredientGrams',{index:index+1});
      row.querySelector('[data-remove-ingredient]').textContent = I.t('ingredientRemove',{index:index+1});
      populateIngredientSelect(row);
    }
  }
  function openIngredientEditor(index) {
    if (busy || !analysis || !['needs_input','completed','failed'].includes(analysis.status)) return;
    const item = analysis.draft?.[index]; if (!item) return;
    const recipe = item.custom_recipe;
    ingredientEditor = {analysisId:analysis.id,revision:analysis.revision,itemIndex:index,originalName:item.name,stale:false};
    $('ingredient-name').value = recipe?.name || item.name;
    $('ingredient-basis').value = recipe?.basis || 'consumed';
    $('ingredient-yield').value = recipe?.batch_yield_g ?? '';
    $('ingredient-consumed').value = recipe?.consumed_g ?? '';
    $('ingredient-accepted').checked = false;
    $('ingredient-editor-warning').hidden = true;
    $('ingredient-builder').hidden = false;
    renderIngredientRows(recipe?.ingredients?.length ? recipe.ingredients : [{food_id:'',grams:''}]);
    $('ingredient-builder').scrollIntoView?.({block:'nearest',behavior:'smooth'});
    $('ingredient-name').focus();
  }
  function closeIngredientEditor() {
    ingredientEditor = null; $('ingredient-builder').hidden = true; controls();
  }
  function renderIngredientActions() {
    $('ingredient-editor-actions').replaceChildren();
    if (!analysis || !['needs_input','completed','failed'].includes(analysis.status)) return;
    (analysis.draft || []).forEach((item,index) => {
      if (!item.custom_recipe) return;
      const button = el('button',I.t('ingredientEdit',{name:item.custom_recipe.name || item.name}));
      button.type = 'button'; button.className = 'secondary'; button.dataset.editIngredients = index;
      button.setAttribute('aria-controls','ingredient-builder');
      button.addEventListener('click',() => openIngredientEditor(index));
      $('ingredient-editor-actions').append(button);
    });
  }
  function ingredientPayload() {
    const name = $('ingredient-name').value.trim();
    if (!name || name.length > 120) throw Error(I.t('ingredientNameRequired'));
    const ingredients = editorRows().map(row => ({food_id:row.food_id,grams:row.grams === '' ? NaN : Number(row.grams)}));
    if (!ingredients.length || ingredients.some(row => !catalogue.some(food => food.id === row.food_id && food.kind === 'ingredient'))) {
      throw Error(I.t('ingredientChooseRequired'));
    }
    if (ingredients.some(row => !Number.isFinite(row.grams) || row.grams <= 0 || row.grams > 10000)) throw Error(I.t('ingredientWeightRequired'));
    if (new Set(ingredients.map(row => row.food_id)).size !== ingredients.length) throw Error(I.t('ingredientDuplicate'));
    const basis = $('ingredient-basis').value;
    const batch_yield_g = basis === 'batch' ? Number($('ingredient-yield').value) : null;
    const consumed_g = basis === 'batch' ? Number($('ingredient-consumed').value) : null;
    if (basis === 'batch' && (![batch_yield_g,consumed_g].every(value => Number.isFinite(value) && value > 0 && value <= 10000) || consumed_g > batch_yield_g)) {
      throw Error(I.t('ingredientBatchInvalid'));
    }
    if (!$('ingredient-accepted').checked) throw Error(I.t('ingredientAcceptRequired'));
    return {revision:ingredientEditor.revision,item_index:ingredientEditor.itemIndex,name,basis,
      ingredients,batch_yield_g,consumed_g,accepted:true};
  }
  function quantityEvidence(detail,block) {
    const provenance = detail.quantity_provenance;
    if (!provenance) return;
    let text;
    if (detail.kind === 'custom_recipe' || provenance.kind === 'custom_recipe') {
      text = provenance.basis === 'batch' ? I.t('customBatchEvidence',{
        yield:provenance.batch_yield_g,consumed:provenance.consumed_g,
        percent:Math.round(provenance.factor * 10000) / 100
      }) : I.t('customConsumedEvidence');
      const origin = el('p',text); origin.className = 'quantity-origin'; block.append(origin);
      for (const ingredient of provenance.ingredients || []) block.append(el('p',I.t('customIngredientEvidence',{
        name:I.foodName(ingredient.food_id,ingredient.name),grams:ingredient.grams,state:ingredientState(ingredient.state)
      })));
      block.append(el('p',I.t(provenance.basis === 'batch' ? 'ingredientBatchHelp' : 'ingredientConsumedHelp')));
      return;
    }
    const grams = provenance.calculated_grams ?? detail.grams;
    if (provenance.kind === 'user_grams') text = I.t('quantityUser',{grams:provenance.input_grams ?? grams});
    if (provenance.kind === 'portion_reference') text = I.t('quantityPortion',{count:provenance.portion_count,reference:provenance.reference_grams,grams});
    if (provenance.kind === 'default_portion') text = I.t('quantityDefault',{grams});
    if (provenance.kind === 'edible_fraction') text = I.t('quantityEdible',{input:provenance.input_grams,grams});
    if (text) { const origin = el('p',text); origin.className = 'quantity-origin'; block.append(origin); }
  }
  function detailLabel(detail) {
    if (detail.kind !== 'custom_recipe') return `${I.foodName(detail.food_id,detail.name)} · ${detail.grams}g`;
    const weight = I.t(detail.quantity_provenance?.basis === 'batch' ? 'customConsumedWeight' : 'customIngredientSum',{grams:detail.grams});
    return `${I.t('customRecipeTitle',{name:detail.name})} · ${weight}`;
  }
  function renderHistory() {
    $('history').replaceChildren();
    for (const entry of analysis.conversation || []) {
      const bubble = el('div'); bubble.className = 'bubble ' + entry.role;
      let text = entry.display || entry.content;
      if (entry.role === 'assistant') text = I.systemText(text);
      else if (entry.kind === 'ingredient_recipe') text = I.t('ingredientRecipeRecorded',{
        name:String(entry.content || '').replace(/^已确认自定义食材配方：/,'')
      });
      else if (entry.display && entry.display !== entry.content
        && entry.content?.startsWith('已回答：')
        && entry.content.includes('\n当前餐食资料：')) text = I.structuredReply(entry);
      bubble.append(el('strong',entry.role === 'user' ? I.t('you') : 'NutriChat'),document.createTextNode(text));
      $('history').append(bubble);
    }
  }
  function renderEvidence() {
    const open = new Map(Array.from($('evidence').children).map(block => [block.dataset.item,block.open]));
    $('evidence').replaceChildren();
    for (const [index,detail] of (analysis.details || []).entries()) {
      const block = el('details'); block.dataset.item = detail.food_id + ':' + index;
      block.open = open.get(block.dataset.item) ?? true;
      block.append(el('summary',`${detailLabel(detail)} · ${detail.nutrients.calories} kcal`));
      quantityEvidence(detail,block);
      for (const assumption of detail.assumptions || []) block.append(el('p',I.assumption(assumption,detail.food_id)));
      const sources = el('p'); sources.className = 'sources';
      sources.append(document.createTextNode(I.t('sources')));
      const seen = new Set();
      for (const source of detail.sources || []) {
        if (seen.has(source.url)) continue;
        seen.add(source.url);
        const link = el('a',`${source.name} #${source.id} (${source.license})`);
        if (source.url?.startsWith('https://fdc.nal.usda.gov/')) {
          link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
        }
        sources.append(link,document.createTextNode(' '));
      }
      block.append(sources); $('evidence').append(block);
    }
  }
  function render() {
    const state = analysis?.status;
    $('dialogue').hidden = !analysis;
    $('result').hidden = !analysis || !['completed','confirmed'].includes(state);
    $('answer-form').hidden = state !== 'needs_input';
    const custom = analysis?.draft?.some(item => item.custom_recipe);
    $('reply-form').hidden = !['needs_input','completed','failed'].includes(state) || !!custom;
    $('custom-recipe-guidance').hidden = !custom || !['needs_input','completed','failed'].includes(state);
    if (ingredientEditor && (analysis?.id !== ingredientEditor.analysisId || state === 'confirmed')) closeIngredientEditor();
    if (ingredientEditor && analysis?.revision !== ingredientEditor.revision) {
      ingredientEditor.stale = true; $('ingredient-editor-warning').hidden = false;
    }
    renderIngredientActions();
    if (analysis) {
      $('mode').value = analysis.mode; modeHelp();
      $('dialogue-title').textContent = I.t(analysis.mode === 'basic' ? 'basicDialogue' : 'advancedDialogue');
      renderHistory();
      if (state === 'needs_input') renderQuestions();
      $('status').textContent = I.t(analysis.mode) + ' · ' + I.t(state);
      $('interpreted').textContent = (analysis.details || []).length
        ? analysis.details.map(detailLabel).join(' · ')
        : analysis.interpreted_food_text || '';
      for (const key of ['calories','protein_g','carbs_g','fat_g']) $(key).textContent = analysis[key] ?? '—';
      $('record').textContent = I.t('record',{id:analysis.id,revision:analysis.revision});
      $('confirm').hidden = state === 'confirmed';
      $('review-help').textContent = I.t(state === 'confirmed' ? 'confirmedHelp' : 'reviewHelp');
      renderEvidence();
    }
    controls();
  }
  function saved(data) {
    analysis = data.analysis || data;
    I.storageSet('nutrichat.analysis',analysis.id);
    $('meal').value = analysis.food_text;
    render(); clearTimeout(timer);
    if (analysis.status === 'queued') {
      message({key:'parsing'}); timer = setTimeout(poll,1200);
    }
  }
  async function poll() {
    try {
      const next = await api('/analyses/' + analysis.id);
      analysis = next; render();
      if (next.status === 'queued') timer = setTimeout(poll,1500);
      else if (next.status === 'needs_input') message({key:next.questions?.some(q => q.kind === 'unsupported') ? 'unsupportedMessage' : 'needsInputMessage'});
      else if (next.status === 'failed') message(next.error_message || {key:'failedMessage'},true);
      else message({key:'savedMessage'});
    } catch (error) { message({raw:error.message,recovery:true},true); }
  }
  async function submit(work) {
    busy = true; controls();
    try { await work(); } catch (error) { message(error.message,true); }
    finally { busy = false; controls(); }
  }
  $('meal-form').addEventListener('submit',event => {
    event.preventDefault();
    submit(async () => saved(await api('/analyses','POST',{food_text:$('meal').value,mode:$('mode').value})));
  });
  $('reply-form').addEventListener('submit',event => {
    event.preventDefault();
    submit(async () => {
      const text = $('reply').value.trim(); if (!text) return;
      saved(await api('/analyses/' + analysis.id + '/reply','POST',{revision:analysis.revision,message:text}));
      $('reply').value = '';
    });
  });
  $('answer-form').addEventListener('submit',event => {
    event.preventDefault();
    submit(async () => {
      const answers = {};
      for (const row of $('questions').children) {
        const kind = row.dataset.kind;
        if (kind === 'unsupported') continue;
        let value;
        if (kind === 'recipe') {
          if (!row.querySelector('[data-accept]').checked) continue;
          const ingredients = {};
          for (const input of row.querySelectorAll('[data-ingredient]')) {
            if (input.value === '') throw Error('请填完整配方数值，零用量请填 0');
            ingredients[input.dataset.ingredient] = Number(input.value);
          }
          const yieldInput = row.querySelector('[data-yield]');
          if (yieldInput.value === '') throw Error('请填成品总重');
          value = {ingredients,yield_g:Number(yieldInput.value)};
        } else {
          const input = row.querySelector('[data-answer]');
          if (kind === 'confirm') { if (!input.checked) continue; value = true; }
          else { if (input.value === '') continue; value = kind === 'number' ? Number(input.value) : input.value; }
        }
        answers[row.dataset.key] = value;
      }
      if (!Object.keys(answers).length) throw Error('请至少回答一个问题，或使用下方对话补充。');
      saved(await api('/analyses/' + analysis.id + '/reply','POST',{revision:analysis.revision,answers}));
    });
  });
  $('ingredient-add').addEventListener('click',() => {
    if (busy || !ingredientEditor || $('ingredient-rows').children.length >= 30) return;
    renderIngredientRows([...editorRows(),{food_id:'',grams:''}]); $('ingredient-accepted').checked = false;
  });
  $('ingredient-cancel').addEventListener('click',closeIngredientEditor);
  $('ingredient-basis').addEventListener('change',translateIngredientEditor);
  $('ingredient-form').addEventListener('input',event => {
    if (event.target.id !== 'ingredient-accepted' && !event.target.matches('[data-ingredient-search]')) $('ingredient-accepted').checked = false;
  });
  $('ingredient-form').addEventListener('change',event => {
    if (event.target.id !== 'ingredient-accepted') $('ingredient-accepted').checked = false;
  });
  $('ingredient-form').addEventListener('submit',event => {
    event.preventDefault();
    if (busy || !ingredientEditor || ingredientEditor.stale || !analysis || !['needs_input','completed','failed'].includes(analysis.status)) return;
    submit(async () => {
      const payload = ingredientPayload();
      try {
        const result = await api('/analyses/' + ingredientEditor.analysisId + '/ingredients','POST',payload);
        closeIngredientEditor(); saved(result);
      } catch (error) {
        if (error.status === 409) {
          ingredientEditor.stale = true; $('ingredient-editor-warning').hidden = false;
          throw Error(I.t('ingredientStale'));
        }
        throw error;
      }
    });
  });
  $('confirm').addEventListener('click',() => submit(async () => {
    saved(await api('/analyses/' + analysis.id + '/confirm','POST',{revision:analysis.revision}));
    message({key:'confirmedMessage'});
  }));
  $('new').addEventListener('click',() => {
    clearTimeout(timer); analysis = null; questionVersion = '';
    I.storageRemove('nutrichat.analysis');
    $('meal').value = ''; $('reply').value = ''; message(''); render(); $('meal').focus();
  });
  function modeHelp() { $('mode-help').textContent = I.t($('mode').value === 'basic' ? 'basicHelp' : 'advancedHelp'); }
  $('mode').addEventListener('change',modeHelp);
  $('switch-mode').addEventListener('click',() => submit(async () => {
    saved(await api('/analyses/' + analysis.id + '/mode','POST',{
      revision:analysis.revision,mode:analysis.mode === 'basic' ? 'advanced' : 'basic'
    }));
  }));
  function catalogueInfo() {
    if (!catalogue.length) return;
    $('catalogue-info').textContent = I.t('catalogueCount',{
      ingredients:catalogue.filter(food => food.kind === 'ingredient').length,
      recipes:catalogue.filter(food => food.kind === 'recipe').length
    });
    if (catalogue.some(food => !window.NUTRICHAT_EN_CATALOGUE?.[food.id])) {
      const note = I.t('catalogueChineseAdditions');
      if (note) $('catalogue-info').textContent += ' · ' + note;
    }
  }
  function showFoods() {
    const search = $('search').value.trim().toLowerCase();
    const open = new Set(Array.from($('food-list').children).filter(node => node.open).map(node => node.dataset.foodId));
    $('food-list').replaceChildren();
    const matches = catalogue.filter(food => [food.name,...food.aliases,
      window.NUTRICHAT_EN_CATALOGUE?.[food.id]?.name || ''].join(' ').toLowerCase().includes(search));
    for (const food of matches) {
      const block = el('details'); block.dataset.foodId = food.id; block.open = open.has(food.id);
      block.append(el('summary',I.foodName(food.id,food.name) + (food.kind === 'recipe' ? ' · ' + I.t('referenceRecipe') : '')));
      block.append(el('p',food.kind === 'recipe'
        ? I.t('catalogueRecipe',{method:I.method(food.id,food.method).replace(/[.!?。]+$/, '')})
        : I.t('catalogueIngredient',{calories:food.nutrients.calories,protein:food.nutrients.protein_g,
          fat:food.nutrients.fat_g,carbs:food.nutrients.carbs_g,fdc:food.fdc_id})));
      $('food-list').append(block);
    }
    if (!matches.length && catalogue.length) $('food-list').append(el('p',I.t('noFoods')));
  }
  $('search').addEventListener('input',showFoods);
  $('language-zh').addEventListener('click',() => changeLanguage('zh-CN'));
  $('language-en').addEventListener('click',() => changeLanguage('en'));
  async function init() {
    applyStaticLanguage(); controls();
    try {
      const data = await api('/foods'); catalogue = data.catalogue.foods;
      I.setCatalogue(catalogue); catalogueInfo(); showFoods();
      if (data.provider === 'demo') message({key:'demoMessage'});
      const id = I.storageGet('nutrichat.analysis');
      if (id) {
        analysis = await api('/analyses/' + encodeURIComponent(id));
        $('meal').value = analysis.food_text; render();
        if (analysis.status === 'queued') { message({key:'parsing'}); timer = setTimeout(poll,500); }
        else if (analysis.status === 'failed') message(analysis.error_message || {key:'failedMessage'},true);
        else if (analysis.status === 'needs_input' && analysis.questions?.some(q => q.kind === 'unsupported')) message({key:'unsupportedMessage'});
      }
    } catch (error) { message(error.message,true); }
  }
  init();
})();
