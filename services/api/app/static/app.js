/* The UI language changes presentation only; API payloads and saved facts stay unchanged. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const I = window.NutriI18n;
  let analysis = null, busy = false, timer = null, catalogue = [];
  let questionVersion = '', notice = {raw:'', error:false};
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
    if (!response.ok) throw Error(Array.isArray(data.detail)
      ? data.detail.map(item => item.msg).join('\n') : data.detail || '请求失败');
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
    $('confirm').disabled = locked || analysis?.status !== 'completed';
    $('reply').disabled = locked;
    $('mode').disabled = !!analysis || busy;
    $('switch-mode').hidden = !analysis || analysis.status === 'confirmed';
    $('switch-mode').disabled = locked;
    $('switch-mode').textContent = I.t(analysis?.mode === 'basic' ? 'switchAdvanced' : 'switchBasic');
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
      if (q.kind === 'number') {
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
  function renderHistory() {
    $('history').replaceChildren();
    for (const entry of analysis.conversation || []) {
      const bubble = el('div'); bubble.className = 'bubble ' + entry.role;
      let text = entry.display || entry.content;
      if (entry.role === 'assistant') text = I.systemText(text);
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
      block.append(el('summary',`${I.foodName(detail.food_id,detail.name)} · ${detail.grams}g · ${detail.nutrients.calories} kcal`));
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
    $('reply-form').hidden = !['needs_input','completed','failed'].includes(state);
    if (analysis) {
      $('mode').value = analysis.mode; modeHelp();
      $('dialogue-title').textContent = I.t(analysis.mode === 'basic' ? 'basicDialogue' : 'advancedDialogue');
      renderHistory();
      if (state === 'needs_input') renderQuestions();
      $('status').textContent = I.t(analysis.mode) + ' · ' + I.t(state);
      $('interpreted').textContent = (analysis.details || []).length
        ? analysis.details.map(detail => I.foodName(detail.food_id,detail.name) + ' ' + detail.grams + 'g').join(' · ')
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
