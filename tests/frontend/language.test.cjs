/* Isolated DOM checks; no network or model requests are sent.
 * npm install --prefix /tmp/nutrichat-ui-tests --no-audit --no-fund jsdom@26.1.0
 * NODE_PATH=/tmp/nutrichat-ui-tests/node_modules node --test tests/frontend/language.test.cjs
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const {JSDOM, VirtualConsole} = require('jsdom');

const root = path.resolve(__dirname, '../..');
const staticDir = path.join(root, 'services/api/app/static');
const foods = JSON.parse(fs.readFileSync(path.join(root, 'services/common/data/catalogue.json'))).foods;
const fixtures = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/meal-display.json')));
const clone = value => JSON.parse(JSON.stringify(value));
const flush = async () => { for (let i = 0; i < 4; i++) await new Promise(setImmediate); };

async function mount(t, {meal = null, language, storageBlocked = false, storage = {}, respond} = {}) {
  const virtualConsole=new VirtualConsole();
  virtualConsole.on('jsdomError',error=>{if(!error.message.includes('Not implemented: navigation'))throw error;});
  const dom = new JSDOM(fs.readFileSync(path.join(staticDir, 'index.html'), 'utf8'), {
    url:'http://localhost:8003/app', runScripts:'outside-only', pretendToBeVisual:true, virtualConsole,
  });
  t.after(() => dom.window.close());
  const {window} = dom;
  const document = window.document;
  const errors = [];
  window.addEventListener('error', event => errors.push(event.error || event.message));
  if (storageBlocked) {
    Object.defineProperty(window, 'localStorage', {get() {throw new Error('Storage disabled');}});
  } else {
    for(const [key,value] of Object.entries(storage))window.localStorage.setItem(key,value);
    if (language !== undefined) window.localStorage.setItem('nutrichat.language', language);
    if (meal) window.localStorage.setItem('nutrichat.analysis.user.ui-user', meal.id);
  }
  let nextTimer = 0;
  const timers = new Map();
  window.setTimeout = callback => {timers.set(++nextTimer, callback); return nextTimer;};
  window.clearTimeout = id => timers.delete(id);
  const requests = [];
  window.fetch = async (url, options = {}) => {
    const request = {url:String(url), method:options.method || 'GET',
      body:options.body ? JSON.parse(options.body) : undefined,headers:options.headers};
    requests.push(request);
    let response = respond ? await respond(request) : undefined;
    if (response === undefined) {
      if (request.url === '/auth/me') response = {body:{id:'ui-user',username:'UI user'}};
      else if(request.url === '/profile')response={body:{profile:null,reference:null}};
      else if(request.url.startsWith('/tracking'))response={body:{today:'2026-11-03',start_date:'2026-10-05',end_date:'2026-11-03',days:[],summary:{recorded_days:0,average_calories:null,weight_entries:0,weight_change_kg:null}}};
      else if(request.url.startsWith('/daily-records/'))response={body:{date:request.url.split('/').pop(),revision:0,manual_calories:null,weight_kg:null,calories:null,calorie_source:null,meal_count:0,meal_calories:null}};
      else if(request.url === '/analyses?limit=20')response={body:meal?[clone(meal)]:[]};
      else if (request.url === '/foods') response = {body:{provider:'qwen', catalogue:{foods:clone(foods)}}};
      else if (meal && request.url === '/analyses/' + meal.id && request.method === 'GET') {
        response = {body:clone(meal)};
      } else throw new Error('Unexpected request: ' + request.method + ' ' + request.url);
    }
    const status = response.status || 200;
    return {ok:status >= 200 && status < 300, status, redirected:false,
      url:'http://localhost:8003' + request.url,
      headers:{get:name => name.toLowerCase() === 'content-type' ? 'application/json' : null},
      json:async () => clone(response.body)};
  };
  for (const script of ['catalogue-en.js', 'i18n.js', 'account-i18n.js', 'app.js']) {
    window.eval(fs.readFileSync(path.join(staticDir, script), 'utf8'));
  }
  await flush();
  assert.deepEqual(errors, [], 'Frontend initialization threw an error');
  const $ = id => document.getElementById(id);
  const clickLanguage = async lang => {
    $('language-' + lang).click();
    await flush();
    assert.deepEqual(errors, [], 'Language switch threw an error');
  };
  return {window, document, $, requests, timers, clickLanguage};
}

test('Chinese is the default; English switch updates accessibility and persists locally', async t => {
  const {window, document, $, requests, clickLanguage} = await mount(t);
  assert.equal(document.documentElement.lang, 'zh-CN');
  assert.equal($('language-zh').getAttribute('aria-pressed'), 'true');
  const before = requests.length;
  await clickLanguage('en');
  assert.equal(document.documentElement.lang, 'en');
  assert.equal($('language-en').getAttribute('aria-pressed'), 'true');
  assert.equal($('language-zh').getAttribute('aria-pressed'), 'false');
  assert.equal(window.localStorage.getItem('nutrichat.language'), 'en');
  assert.match($('estimate').textContent, /estimate/i);
  assert.match($('meal').placeholder, /rice|tomato|egg|chicken/i);
  assert.equal(requests.length, before, 'Switching must not send a request');
  await clickLanguage('zh');
  assert.equal(document.documentElement.lang, 'zh-CN');
  assert.equal(window.localStorage.getItem('nutrichat.language'), 'zh-CN');
  assert.match($('estimate').textContent, /估算/);
});

test('Merged daily balance inputs save with intake coverage and remain bilingual', async t => {
  const coverage={breakfast:false,lunch:false,dinner:false,snacks:false,drinks:false};
  let saved=null;
  const day=(revision,exercise,flags)=>({date:'2026-11-03',revision,manual_calories:1800,
    weight_kg:null,calories:1800,calorie_source:'manual',meal_count:0,meal_calories:null,
    exercise_calories:exercise,baseline_expenditure_kcal:1600,
    total_expenditure_kcal:exercise==null?null:1900,
    balance_type:exercise==null?null:'deficit',balance_kcal:exercise==null?null:100,
    intake_coverage:flags,intake_complete:Object.values(flags).every(Boolean)});
  const {document,$,requests,clickLanguage}=await mount(t,{respond:request=>{
    if(request.url==='/daily-records/2026-11-03'){
      if(request.method==='PUT'){saved=request.body;return {body:day(2,saved.exercise_calories,saved.intake_coverage)};}
      return {body:day(1,null,coverage)};
    }
  }});
  assert.ok(document.querySelector('#meal-form').compareDocumentPosition($('result')) & 4);
  assert.ok($('result').compareDocumentPosition($('tracking-card')) & 4);
  $('daily-exercise').value='300';$('daily-exercise').dispatchEvent(new document.defaultView.Event('input',{bubbles:true}));
  for(const key of Object.keys(coverage)){
    $('coverage-'+key).checked=true;
    $('coverage-'+key).dispatchEvent(new document.defaultView.Event('change',{bubbles:true}));
  }
  assert.match($('daily-completeness').textContent,/尚未保存/);
  await clickLanguage('en');
  assert.equal($('daily-exercise').value,'300');
  assert.equal($('coverage-drinks').checked,true);
  assert.match($('daily-completeness').textContent,/unsaved/i);
  $('daily-form').dispatchEvent(new document.defaultView.Event('submit',{bubbles:true,cancelable:true}));
  await flush();
  assert.equal(saved.exercise_calories,300);
  assert.deepEqual(saved.intake_coverage,{breakfast:true,lunch:true,dinner:true,snacks:true,drinks:true});
  assert.match($('daily-balance-value').textContent,/deficit.*100/i);
  assert.ok(requests.some(request=>request.method==='PUT'&&request.url==='/daily-records/2026-11-03'));
});

test('Saved English choice is applied on fresh load without changing input language', async t => {
  const {$, document} = await mount(t, {language:'en'});
  assert.equal(document.documentElement.lang, 'en');
  assert.match($('estimate').textContent, /estimate/i);
  $('meal').value = '番茄炒蛋 200 克';
  assert.equal($('meal').value, '番茄炒蛋 200 克');
});

test('Unknown stored language falls back to Chinese and disabled storage does not break switching', async t => {
  const invalid = await mount(t, {language:'invalid-language'});
  assert.equal(invalid.document.documentElement.lang, 'zh-CN');
  const blocked = await mount(t, {storageBlocked:true});
  await blocked.clickLanguage('en');
  assert.equal(blocked.document.documentElement.lang, 'en');
  assert.match(blocked.$('estimate').textContent, /estimate/i);
});

test('Switch preserves meal, reply and search text and selected estimation mode', async t => {
  const {$, clickLanguage, requests} = await mount(t);
  $('meal').value = '番茄炒蛋200克 — keep my original words';
  $('reply').value = 'Actually 150g, not 200g';
  $('search').value = 'rice';
  $('mode').value = 'advanced';
  const before = requests.length;
  await clickLanguage('en');
  await clickLanguage('zh');
  assert.equal($('meal').value, '番茄炒蛋200克 — keep my original words');
  assert.equal($('reply').value, 'Actually 150g, not 200g');
  assert.equal($('search').value, 'rice');
  assert.equal($('mode').value, 'advanced');
  assert.equal(requests.length, before);
});

test('Every catalogue food has an English display name and every recipe has an English method', async t => {
  const {window} = await mount(t);
  const entries = window.NUTRICHAT_EN_CATALOGUE;
  assert.equal(Object.keys(entries).length,foods.length,'Cover the complete current catalogue');
  assert.ok(Object.keys(entries).every(id => foods.some(food => food.id === id)));
  window.NutriI18n.setLanguage('en');
  for (const food of foods) {
    assert.ok(entries[food.id],food.id+' needs an English display entry');
    assert.ok(entries[food.id].name.trim(), food.id + ' needs an English name');
    assert.doesNotMatch(entries[food.id].name, /[\u3400-\u9fff]/u, food.id);
    if (food.kind === 'recipe') {
      assert.ok(entries[food.id].method.trim(), food.id + ' needs an English method');
      assert.doesNotMatch(entries[food.id].method, /[\u3400-\u9fff]/u, food.id);
    }
  }
  assert.match(entries.chicken.name, /raw/i);
  assert.match(entries.chicken_roast.name, /roast/i);
  assert.match(entries.egg_raw.name, /raw/i);
  assert.match(entries.egg.name, /boiled/i);
  assert.match(entries.broccoli.name, /raw/i);
  assert.match(entries.broccoli_cooked.name, /boiled/i);
  assert.match(entries.gai_lan.name, /gai lan/i);
  assert.match(entries.dish_144.name, /gai lan/i);
  assert.doesNotMatch(entries.dish_017.name, /gai lan|Chinese broccoli/i);
});

test('English catalogue search finds the translated recipe and keeps Chinese search usable', async t => {
  const {window, $, clickLanguage} = await mount(t);
  await clickLanguage('en');
  $('search').value = 'Mapo';
  $('search').dispatchEvent(new window.Event('input', {bubbles:true}));
  assert.match($('food-list').textContent, /Mapo/i);
  assert.equal($('food-list').querySelectorAll('details').length, 1);
  $('search').value = '麻婆豆腐';
  $('search').dispatchEvent(new window.Event('input', {bubbles:true}));
  assert.match($('food-list').textContent, /Mapo/i);
});

test('Completed estimate changes labels and food names without changing totals, ID or revision', async t => {
  const meal = clone(fixtures.tomato_egg_dish);
  const {window, $, clickLanguage, requests} = await mount(t, {meal});
  const before = requests.length;
  const values = ['calories','protein_g','fat_g','carbs_g'].map(id => $(id).textContent);
  await clickLanguage('en');
  assert.deepEqual(['calories','protein_g','fat_g','carbs_g'].map(id => $(id).textContent), values);
  assert.match($('record').textContent, new RegExp(meal.id));
  assert.match($('record').textContent, /1/);
  assert.match($('interpreted').textContent, /tomato.*egg|egg.*tomato/i);
  assert.match($('evidence').textContent, /400\s*g/);
  assert.match($('evidence').textContent, /200\s*g/);
  assert.doesNotMatch($('evidence').textContent, /基础版|整锅|配料|数据来源/);
  assert.equal($('result').hidden, false);
  assert.equal($('confirm').disabled, false);
  assert.equal(window.localStorage.getItem('nutrichat.analysis.user.ui-user'), meal.id);
  assert.equal(requests.length, before);
});

test('Submitted meals keep a compact description and New meal restores the complete composer', async t => {
  const meal = clone(fixtures.tomato_egg_dish);
  const {document, $, requests, clickLanguage} = await mount(t, {meal});
  const before = requests.length;
  const composerInputs = ['meal-input','mode-picker','mode-help','meal-examples','composer-note','estimate'];
  for (const id of composerInputs) assert.equal($(id).hidden,true,id + ' should collapse after submission');
  assert.equal($('submitted-meal').hidden,false);
  assert.equal($('submitted-meal').textContent,meal.food_text);
  assert.equal($('meal').disabled,true);
  assert.equal($('new').hidden,false);
  assert.equal($('result').hidden,false);
  assert.equal($('dialogue').hidden,true);
  await clickLanguage('en');
  assert.match($('composer-title').textContent,/This meal/);
  assert.equal($('submitted-meal').textContent,meal.food_text,'Keep the original description in either language');
  for (const id of composerInputs) assert.equal($(id).hidden,true);
  $('new').click();
  for (const id of composerInputs) assert.equal($(id).hidden,false,id + ' should return for a new meal');
  assert.equal($('submitted-meal').hidden,true);
  assert.equal($('submitted-meal').textContent,'');
  assert.equal($('meal').disabled,false);
  assert.equal($('meal').value,'');
  assert.equal(document.activeElement,$('meal'));
  assert.equal($('result').hidden,true);
  assert.equal($('dialogue').hidden,true);
  assert.equal($('history-panel').hidden,true);
  assert.equal(requests.length,before,'Opening a new composer does not submit a meal');
});

test('Edit this meal discloses corrections and preserves an unsent reply through closing, navigation and translation', async t => {
  const meal = clone(fixtures.tomato_egg_dish);
  const revised = {...clone(meal),revision:meal.revision+1};
  const {window, document, $, requests, clickLanguage} = await mount(t, {meal,language:'en',
    respond:request => request.url.endsWith('/reply') ? {body:{analysis:revised}} : undefined});
  const before = requests.length;
  assert.equal($('dialogue').hidden,true);
  assert.equal($('edit-meal').hidden,false);
  assert.equal($('edit-meal').getAttribute('aria-controls'),'dialogue');
  assert.equal($('edit-meal').getAttribute('aria-expanded'),'false');
  $('edit-meal').click();
  assert.equal($('dialogue').hidden,false);
  assert.equal($('reply-form').hidden,false);
  assert.equal($('edit-meal').getAttribute('aria-expanded'),'true');
  assert.equal(document.activeElement,$('reply'));
  $('reply').value = 'Actually 175g, cooked weight';
  $('edit-meal').click();
  assert.equal($('dialogue').hidden,true);
  assert.equal($('edit-meal').getAttribute('aria-expanded'),'false');
  await clickLanguage('zh');
  assert.equal($('dialogue').hidden,true,'Translation must not reopen the editor');
  $('edit-meal').click();
  $('tab-diary').click();
  await clickLanguage('en');
  assert.equal($('panel-diary').hidden,false);
  $('tab-meal').click();
  assert.equal($('dialogue').hidden,false);
  assert.equal($('edit-meal').getAttribute('aria-expanded'),'true');
  assert.equal($('reply').value,'Actually 175g, cooked weight');
  assert.equal(requests.length,before,'Disclosure, navigation and translation must not send corrections');
  $('reply-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));
  await flush();
  const sent = requests.find(request => request.url.endsWith('/reply'));
  assert.deepEqual(sent.body,{revision:meal.revision,message:'Actually 175g, cooked weight'});
  assert.equal($('reply').value,'');
  assert.equal($('dialogue').hidden,true,'The returned estimate should be ready for review');
  assert.equal($('edit-meal').getAttribute('aria-expanded'),'false');
  assert.equal($('confirm').disabled,false);
  assert.equal($('pending-edit-notice').hidden,true);
});

for (const provider of ['qwen','demo']) {
  test(`Unsent ${provider === 'demo' ? 'offline replacements' : 'conversation corrections'} block confirmation until discarded, even with the editor closed`, async t => {
    const meal = {...clone(fixtures.tomato_egg_dish),food_text:'100g egg'};
    const {window, $, requests, clickLanguage} = await mount(t,{meal,language:'en',respond:request => {
      if (request.url === '/foods') return {body:{provider,catalogue:{foods:clone(foods)}}};
      if (request.url.endsWith('/confirm')) return {body:{...meal,status:'confirmed',revision:meal.revision+1}};
    }});
    const draft = $(provider === 'demo' ? 'offline-meal' : 'reply');
    const input = value => {
      draft.value = value;
      draft.dispatchEvent(new window.Event('input',{bubbles:true}));
    };
    assert.equal($('confirm').disabled,false);
    assert.equal($('pending-edit-notice').hidden,true);
    $('edit-meal').click();
    input(provider === 'demo' ? '200g egg' : 'Actually 200g egg');
    assert.equal($('confirm').disabled,true);
    assert.equal($('pending-edit-notice').hidden,false);
    assert.equal($('pending-edit-notice').getAttribute('role'),'status');
    assert.match($('pending-edit-notice').textContent,provider === 'demo'
      ? /submit.*restore the original full description/i : /submit or clear/i);
    const before = requests.length;
    $('confirm').click();
    $('confirm').dispatchEvent(new window.Event('click',{bubbles:true}));
    await flush();
    assert.equal(requests.length,before,'Unsubmitted changes must never confirm the previous estimate');
    $('edit-meal').click();
    assert.equal($('dialogue').hidden,true);
    assert.equal($('confirm').disabled,true,'Closing the editor does not discard the pending change');
    assert.equal($('pending-edit-notice').closest('[hidden]'),null,'The reason for disabled confirmation stays visible');
    $('tab-diary').click();await clickLanguage('zh');$('tab-meal').click();
    assert.equal($('confirm').disabled,true);
    assert.equal($('pending-edit-notice').hidden,false);
    assert.match($('pending-edit-notice').textContent,/提交/);
    assert.match($('pending-edit-notice').textContent,provider === 'demo' ? /恢复原来的完整描述/ : /清空修改/);
    assert.equal(draft.value,provider === 'demo' ? '200g egg' : 'Actually 200g egg');
    await clickLanguage('en');
    assert.equal($('confirm').disabled,true);
    assert.match($('pending-edit-notice').textContent,provider === 'demo'
      ? /submit.*restore the original full description/i : /submit or clear/i);
    assert.equal(requests.length,before,'Switching language must not send or discard the pending change');
    $('edit-meal').click();
    if (provider === 'demo') {
      input('');
      assert.equal($('confirm').disabled,true,'A blank replacement must not silently approve the previous meal');
      input(meal.food_text);
    } else {
      input('   ');
    }
    assert.equal($('confirm').disabled,false);
    assert.equal($('pending-edit-notice').hidden,true);
    $('confirm').click();await flush();
    assert.equal(requests.filter(request => request.url.endsWith('/confirm')).length,1);
    assert.equal($('confirm').hidden,true);
    assert.equal($('pending-edit-notice').hidden,true);
  });
}

test('Unsaved recipe quantities and approval survive repeated language switches and submit unchanged', async t => {
  const meal = clone(fixtures.mapo_tofu);
  const completed = clone(fixtures.tomato_egg_dish);
  completed.id = meal.id;
  const {window, document, $, requests, clickLanguage} = await mount(t, {meal,
    respond:request => request.method === 'POST' ? {body:{analysis:completed}} : undefined});
  const adjustment = document.querySelector('.recipe-adjust');
  adjustment.open = true;
  const ingredient = document.querySelector('[data-ingredient="oil"]');
  ingredient.value = '7.5';
  ingredient.dispatchEvent(new window.Event('input',{bubbles:true}));
  document.querySelector('[data-yield]').value = '700';
  document.querySelector('[data-yield]').dispatchEvent(new window.Event('input',{bubbles:true}));
  document.querySelector('[data-accept]').checked = true;
  $('reply').value = 'Still editing this reply';
  const before = requests.length;
  await clickLanguage('en');
  assert.equal(document.querySelector('[data-ingredient="oil"]').value, '7.5');
  assert.equal(document.querySelector('[data-yield]').value, '700');
  assert.equal(document.querySelector('[data-accept]').checked, true);
  assert.equal(document.querySelector('.recipe-adjust').open,true);
  assert.match(document.querySelector('[data-recipe-preview]').textContent,/Current batch:.*7\.5.*700/);
  assert.match($('questions').textContent, /Mapo/i);
  assert.doesNotMatch($('questions').textContent, /整锅|请选择|配方|豆瓣酱/);
  await clickLanguage('zh');
  assert.equal(document.querySelector('[data-ingredient="oil"]').value, '7.5');
  assert.equal(document.querySelector('[data-yield]').value, '700');
  assert.equal(document.querySelector('[data-accept]').checked, true);
  assert.equal(document.querySelector('.recipe-adjust').open,true);
  assert.equal($('reply').value, 'Still editing this reply');
  assert.equal(requests.length, before);
  $('answer-form').dispatchEvent(new window.Event('submit', {bubbles:true,cancelable:true}));
  await flush();
  const sent = requests.find(request => request.method === 'POST');
  assert.equal(sent.url, '/analyses/' + meal.id + '/reply');
  assert.equal(sent.body.revision, meal.revision);
  assert.equal(sent.body.answers['0.recipe'].ingredients.oil, 7.5);
  assert.equal(sent.body.answers['0.recipe'].yield_g, 700);
});

test('Recipe quantities stay in a closed disclosure, need explicit acceptance, and every edit updates the preview and clears acceptance', async t => {
  const meal = clone(fixtures.mapo_tofu);
  const {window, document, $, requests, clickLanguage} = await mount(t, {meal,language:'en'});
  const row = document.querySelector('[data-kind="recipe"]');
  const adjustment = row.querySelector('details');
  const accept = row.querySelector('[data-accept]');
  const preview = row.querySelector('[data-recipe-preview]');
  assert.equal(adjustment.open,false);
  assert.equal(accept.checked,false);
  assert.equal(adjustment.contains(accept),false,'Acceptance must remain available without expanding quantities');
  assert.equal(adjustment.contains(preview),false,'The reference recipe must remain readable while quantities are collapsed');
  assert.match(preview.textContent,/Reference batch:.*620.*Review before accepting/);
  const quantities = [...row.querySelectorAll('[data-ingredient],[data-yield]')];
  assert.equal(quantities.length,meal.questions[0].ingredients.length+1);
  assert.ok(quantities.every(input => adjustment.contains(input)));
  const before = requests.length;
  $('answer-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));
  await flush();
  assert.equal(requests.length,before,'Opening a recipe does not count as accepting it');
  adjustment.open = true;
  for (const [index,input] of quantities.entries()) {
    accept.checked = true;
    input.value = String(100 + index + 0.25);
    input.dispatchEvent(new window.Event('input',{bubbles:true}));
    assert.equal(accept.checked,false,'Changing ' + (input.dataset.ingredient || 'yield') + ' must require renewed review');
    assert.ok(preview.textContent.includes(input.value),'The preview must show the edited quantity');
    assert.match(preview.textContent,/Current batch:.*Review and accept again/);
  }
  const values = quantities.map(input => input.value);
  $('tab-diary').click();await clickLanguage('zh');$('tab-meal').click();
  assert.equal(adjustment.open,true);
  assert.deepEqual(quantities.map(input => input.value),values);
  assert.equal(accept.checked,false);
  assert.match(preview.textContent,/当前整锅配方.*重新核对/);
  await clickLanguage('en');
  assert.equal(accept.checked,false,'Translation must not approve edited quantities');
  assert.equal(requests.length,before);
});

test('Number and uncertainty answers remain filled and checked after switching', async t => {
  const meal = clone(fixtures.missing_weight);
  const {document, $, requests, clickLanguage} = await mount(t, {meal});
  document.querySelector('[data-kind="number"] input').value = '165.5';
  document.querySelector('[data-kind="confirm"] input').checked = true;
  const before = requests.length;
  await clickLanguage('en');
  assert.equal(document.querySelector('[data-kind="number"] input').value, '165.5');
  assert.equal(document.querySelector('[data-kind="confirm"] input').checked, true);
  assert.match($('questions').textContent, /gram|weight/i);
  assert.match($('questions').textContent, /portion weight unknown/);
  assert.doesNotMatch($('questions').textContent, /吃了多少克|请核对/);
  assert.equal(requests.length, before);
});

for (const mode of ['basic', 'advanced']) {
  test(`Unsupported food in ${mode} stays blocked, translated and correctable by text`, async t => {
    const meal = clone(fixtures.missing_weight);
    meal.mode = mode;
    meal.food_text = '200克火星豉油鸡';
    meal.draft = [{food_id:null,name:'火星豉油鸡',source_text:'火星豉油鸡',grams:200}];
    const label = '数据库未找到“火星豉油鸡”的对应食物记录，暂不能估算。请核对菜名，或在下方提供实际食材及各自克数；不会使用其他食物代替。';
    meal.questions = [{key:'0.food_id',kind:'unsupported',label}];
    meal.conversation = [{role:'user',content:meal.food_text},{role:'assistant',content:label}];
    const corrected = {...clone(fixtures.tomato_egg_dish),id:meal.id,mode,revision:meal.revision+1};
    const {window, document, $, requests, clickLanguage} = await mount(t, {meal,
      respond:request => request.method === 'POST' ? {body:{analysis:corrected}} : undefined});
    assert.match($('questions').textContent, /数据库未找到.*火星豉油鸡.*对应食物记录/);
    assert.equal(document.querySelector('#questions select'), null);
    assert.equal($('answer-submit').hidden, true);
    assert.equal($('answer-submit').disabled, true);
    assert.equal($('reply-form').hidden, false);
    assert.equal($('result').hidden, true);
    assert.equal($('confirm').disabled, true);
    const before = requests.length;
    $('reply').value = '更正：200克番茄炒蛋';
    await clickLanguage('en');
    assert.match($('questions').textContent, /火星豉油鸡: no corresponding food record/);
    assert.match($('questions').textContent, /will not be substituted/);
    assert.match($('history').textContent, /no corresponding food record/);
    assert.match($('message').textContent, /no nutrition estimate/);
    assert.equal($('reply').value, '更正：200克番茄炒蛋');
    assert.equal(requests.length, before);
    await clickLanguage('zh');
    assert.match($('questions').textContent, /数据库未找到/);
    $('answer-form').dispatchEvent(new window.Event('submit', {bubbles:true,cancelable:true}));
    await flush();
    assert.equal(requests.length, before, 'Unsupported rows must not submit an empty or substituted answer');
    $('reply-form').dispatchEvent(new window.Event('submit', {bubbles:true,cancelable:true}));
    await flush();
    const sent = requests.find(request => request.method === 'POST');
    assert.equal(sent.body.message, '更正：200克番茄炒蛋');
    assert.equal(sent.body.answers, undefined);
    assert.equal($('result').hidden, false);
  });
}

test('Mixed unsupported food and known recipe keep recipe answers usable without substitution', async t => {
  const meal = clone(fixtures.mapo_tofu);
  meal.draft.push({food_id:null,name:'火星豉油鸡',grams:200});
  meal.questions.push({key:'1.food_id',kind:'unsupported',
    label:'数据库未找到“火星豉油鸡”的对应食物记录，暂不能估算。请核对菜名，或在下方提供实际食材及各自克数；不会使用其他食物代替。'});
  const {window, document, $, requests, clickLanguage} = await mount(t, {meal,
    respond:request => request.method === 'POST' ? {body:{analysis:meal}} : undefined});
  assert.equal($('result').hidden, true);
  assert.equal($('answer-submit').hidden, false);
  document.querySelector('[data-ingredient="oil"]').value = '5';
  document.querySelector('[data-accept]').checked = true;
  await clickLanguage('en');
  assert.match($('questions').textContent, /no corresponding food record/);
  assert.equal(document.querySelector('[data-ingredient="oil"]').value, '5');
  $('answer-form').dispatchEvent(new window.Event('submit', {bubbles:true,cancelable:true}));
  await flush();
  const sent = requests.find(request => request.method === 'POST');
  assert.equal(sent.body.answers['0.recipe'].ingredients.oil, 5);
  assert.equal(sent.body.answers['1.food_id'], undefined);
  assert.equal($('result').hidden, true, 'A known recipe must not cause a partial meal estimate');
});

test('Bone-inclusive weight question remains an edible-weight clarification in English', async t => {
  const meal = clone(fixtures.missing_weight);
  meal.draft[0] = {...meal.draft[0],food_id:'dish_069',name:'糖醋排骨',grams:200,weight_includes_inedible:true};
  meal.questions = [{key:'0.grams',kind:'number',min:0.1,max:10000,
    label:'糖醋排骨提供的重量包含骨头、壳等不可食部分。请填写实际吃下的可食部分克数，不能直接按带骨或带壳重量计算。'}];
  const {$, clickLanguage} = await mount(t, {meal});
  await clickLanguage('en');
  assert.match($('questions').textContent, /bone/i);
  assert.match($('questions').textContent, /edible/i);
  assert.equal($('result').hidden, true);
});

test('Switch remains available during a queued analysis and does not add polling timers', async t => {
  const meal = {...clone(fixtures.tomato_egg_dish),status:'queued',details:[],calories:null};
  const {$, clickLanguage, requests, timers} = await mount(t, {meal});
  const count = requests.length;
  const pendingTimers = timers.size;
  assert.equal($('language-en').disabled, false);
  await clickLanguage('en');
  assert.equal($('meal').disabled, true);
  assert.equal($('confirm').disabled, true);
  assert.equal(requests.length, count);
  assert.equal(timers.size, pendingTimers);
});

test('Confirmed result stays locked after switching and user conversation text stays original', async t => {
  const meal = {...clone(fixtures.tomato_egg_dish),status:'confirmed',revision:3};
  meal.conversation = [{role:'user',content:'我吃了番茄炒蛋，请保留我的原文。'}];
  const {$, clickLanguage} = await mount(t, {meal});
  assert.equal($('dialogue').hidden,true,'Confirmed meals must not leave an empty correction card');
  assert.equal($('edit-meal').hidden,true);
  assert.equal($('history-panel').hidden,false);
  assert.equal($('dialogue').contains($('history-panel')),false,'Conversation history remains reachable outside the hidden editor');
  assert.equal($('history-panel').open,false);
  $('history-panel').open = true;
  await clickLanguage('en');
  assert.equal($('confirm').hidden, true);
  assert.equal($('reply-form').hidden, true);
  assert.equal($('switch-mode').hidden, true);
  assert.match($('status').textContent, /confirmed/i);
  assert.match($('history').textContent, /我吃了番茄炒蛋，请保留我的原文。/);
  assert.match($('record').textContent, /3/);
  assert.equal($('dialogue').hidden,true);
  assert.equal($('history-panel').hidden,false);
  assert.equal($('history-panel').open,true);
  $('tab-diary').click();$('tab-meal').click();
  assert.equal($('history-panel').closest('[hidden]'),null);
  assert.equal($('history-panel').open,true);
});

test('A server error is presented in English and retranslated when the language changes', async t => {
  const {$, clickLanguage} = await mount(t, {language:'en',respond:request =>
    request.url === '/foods' ? {status:503,body:{detail:'估算服务暂时不可用，请重试或补充更清楚的餐食描述。'}} : undefined});
  assert.match($('message').textContent, /unavailable|try again|retry/i);
  assert.doesNotMatch($('message').textContent, /服务暂时不可用/);
  await clickLanguage('zh');
  assert.match($('message').textContent, /暂时不可用/);
});

test('Untrusted conversation, food labels and source links remain inert text', async t => {
  const meal = clone(fixtures.tomato_egg_dish);
  const attack = '<img src=x onerror="window.__injected=true">';
  meal.food_text = attack;
  meal.conversation = [{role:'user',content:attack}];
  meal.details[0].sources.push({name:attack,id:'attack',license:'test',url:'javascript:window.__injected=true'});
  const {window, document, $, clickLanguage} = await mount(t, {meal});
  await clickLanguage('en');
  assert.match($('history').textContent, /<img src=x/);
  assert.equal(document.querySelector('#history img'), null);
  assert.equal($('submitted-meal').textContent,attack);
  assert.equal(document.querySelector('#submitted-meal img'),null);
  assert.equal(document.querySelector('#evidence img'), null);
  assert.equal(document.querySelector('a[href^="javascript:"]'), null);
  assert.equal(window.__injected, undefined);
});

function unsupportedIngredientMeal() {
  const meal = clone(fixtures.missing_weight);
  meal.mode = 'basic'; meal.food_text = '100克熟米饭，200克火星豉油鸡';
  meal.draft = [{food_id:'rice',name:'熟米饭',grams:100}, {food_id:null,name:'火星豉油鸡',grams:200}];
  meal.questions = [{key:'1.food_id',kind:'unsupported',label:'数据库未找到“火星豉油鸡”的对应食物记录，暂不能估算。'}];
  meal.details = [];
  return meal;
}
function ingredientRecipeFixture(status = 'completed') {
  const meal = clone(fixtures.tomato_egg_dish);
  const recipe = {name:'我的鸡肉配方',basis:'batch',ingredients:[{food_id:'chicken',grams:500},{food_id:'oil',grams:20}],
    batch_yield_g:400,consumed_g:100,accepted:true};
  meal.status = status; meal.mode = 'basic'; meal.draft = [{name:recipe.name,food_id:null,custom_recipe:recipe}];
  meal.details = [{kind:'custom_recipe',food_id:null,name:recipe.name,grams:100,
    nutrients:{calories:194.2,protein_g:28.1,fat_g:8.3,carbs_g:0},sources:[],
    quantity_provenance:{kind:'custom_recipe',basis:'batch',factor:0.25,batch_yield_g:400,consumed_g:100,
      ingredients:[{food_id:'chicken',name:'生鸡胸肉',grams:500,state:'raw'},{food_id:'oil',name:'食用油',grams:20,state:'as_sold'}]}}];
  return meal;
}
function setIngredientRow(document, index, food, grams) {
  const row = document.querySelectorAll('#ingredient-rows .ingredient-row')[index];
  row.querySelector('[data-ingredient-food]').value = food;
  row.querySelector('[data-ingredient-grams]').value = grams;
  return row;
}
async function submitIngredients(view) {
  view.$('ingredient-form').dispatchEvent(new view.window.Event('submit',{bubbles:true,cancelable:true}));
  await flush();
}

test('Unknown item opens a separate ingredient form and searches without selecting a substitute', async t => {
  const meal = unsupportedIngredientMeal();
  const {window,document,$,requests} = await mount(t,{meal});
  document.querySelector('[data-build-ingredients="1"]').click();
  assert.equal($('ingredient-builder').hidden,false);
  assert.equal($('ingredient-form').closest('#answer-form'),null,'Forms must not be nested');
  assert.match($('ingredient-builder-target').textContent,/第 2 项.*火星豉油鸡/);
  assert.equal($('ingredient-name').value,'火星豉油鸡');
  const row = document.querySelector('.ingredient-row');
  const search = row.querySelector('[data-ingredient-search]');
  search.value = 'chicken'; search.dispatchEvent(new window.Event('input',{bubbles:true}));
  const select = row.querySelector('[data-ingredient-food]');
  assert.equal(select.value,'','Searching must not implicitly select any food');
  assert.ok(select.options.length > 1);
  const ids = Array.from(select.options).map(option => option.value).filter(Boolean);
  assert.ok(ids.every(id => foods.find(food => food.id === id).kind === 'ingredient'));
  assert.equal(requests.filter(request => request.method === 'POST').length,0);
  assert.equal($('result').hidden,true);
});

test('Consumed ingredient payload targets only the unresolved item and keeps names as inert text', async t => {
  const meal = unsupportedIngredientMeal();
  const view = await mount(t,{meal,respond:request => request.method === 'POST'
    ? {body:{analysis:{...clone(meal),status:'queued',revision:meal.revision+1}}} : undefined});
  const {document,$,requests} = view;
  document.querySelector('[data-build-ingredients="1"]').click();
  $('ingredient-name').value = '<img src=x onerror=alert(1)>';
  setIngredientRow(document,0,'chicken','150');
  $('ingredient-add').click(); setIngredientRow(document,1,'oil','5');
  $('ingredient-add').click(); setIngredientRow(document,2,'soy_sauce','10');
  $('ingredient-accepted').checked = true;
  await submitIngredients(view);
  const sent = requests.find(request => request.method === 'POST');
  assert.equal(sent.url,'/analyses/' + meal.id + '/ingredients');
  assert.deepEqual(sent.body,{revision:meal.revision,item_index:1,name:'<img src=x onerror=alert(1)>',basis:'consumed',
    ingredients:[{food_id:'chicken',grams:150},{food_id:'oil',grams:5},{food_id:'soy_sauce',grams:10}],
    batch_yield_g:null,consumed_g:null,accepted:true});
  assert.equal(sent.body.draft,undefined,'The client must not replace the rest of the meal');
  assert.deepEqual(meal.draft[0],{food_id:'rice',name:'熟米饭',grams:100});
  assert.equal(document.querySelector('#ingredient-builder img'),null);
  assert.equal($('ingredient-builder').hidden,true);
  assert.equal($('result').hidden,true,'Queued structured calculation must not show old totals');
});

test('Batch editor preserves selections, weights, searches and acceptance across both languages', async t => {
  const meal = unsupportedIngredientMeal();
  const view = await mount(t,{meal,respond:request => request.method === 'POST'
    ? {body:{analysis:{...clone(meal),status:'queued',revision:meal.revision+1}}} : undefined});
  const {window,document,$,requests,clickLanguage} = view;
  document.querySelector('[data-build-ingredients="1"]').click();
  const row = setIngredientRow(document,0,'chicken','500');
  row.querySelector('[data-ingredient-search]').value = 'chicken';
  $('ingredient-name').value = '原文名称 — my recipe';
  $('ingredient-basis').value = 'batch';
  $('ingredient-basis').dispatchEvent(new window.Event('change',{bubbles:true}));
  $('ingredient-yield').value = '650'; $('ingredient-consumed').value = '162.5';
  $('ingredient-accepted').checked = true;
  const before = requests.length;
  await clickLanguage('en');
  assert.equal($('ingredient-batch-fields').hidden,false);
  assert.equal(row.querySelector('[data-ingredient-food]').value,'chicken');
  assert.equal(row.querySelector('[data-ingredient-search]').value,'chicken');
  assert.equal(row.querySelector('[data-ingredient-grams]').value,'500');
  assert.match(row.textContent,/raw edible weight before cooking/);
  assert.match($('ingredient-basis-help').textContent,/even mixture/);
  assert.equal($('ingredient-accepted').checked,true);
  await clickLanguage('zh');
  assert.equal($('ingredient-name').value,'原文名称 — my recipe');
  assert.equal($('ingredient-yield').value,'650'); assert.equal($('ingredient-consumed').value,'162.5');
  assert.equal($('ingredient-accepted').checked,true);
  assert.equal(requests.length,before);
  await submitIngredients(view);
  const sent = requests.find(request => request.method === 'POST');
  assert.equal(sent.body.basis,'batch');
  assert.equal(sent.body.batch_yield_g,650); assert.equal(sent.body.consumed_g,162.5);
  assert.equal(sent.body.ingredients[0].grams,500,'Do not convert whole-batch amounts into portion grams in the client');
});

test('Ingredient builder rejects unselected, blank, zero, excessive and duplicate amounts before any request', async t => {
  const view = await mount(t,{meal:unsupportedIngredientMeal(),language:'en'});
  const {document,$,requests} = view;
  document.querySelector('[data-build-ingredients="1"]').click();
  $('ingredient-accepted').checked = true;
  await submitIngredients(view);
  assert.match($('message').textContent,/Select an actual catalogue ingredient/);
  for (const amount of ['', '0', '-10','10001']) {
    setIngredientRow(document,0,'chicken',amount); $('ingredient-accepted').checked = true;
    await submitIngredients(view);
    assert.match($('message').textContent,/greater than 0/);
  }
  setIngredientRow(document,0,'chicken','100'); $('ingredient-add').click();
  setIngredientRow(document,1,'chicken','20'); $('ingredient-accepted').checked = true;
  await submitIngredients(view);
  assert.match($('message').textContent,/duplicate ingredients/);
  document.querySelectorAll('[data-remove-ingredient]')[1].click();
  $('ingredient-accepted').checked = false; await submitIngredients(view);
  assert.match($('message').textContent,/confirmation box/);
  assert.equal(requests.filter(request => request.method === 'POST').length,0);
});

test('Whole-batch weights cannot be blank, zero or less than the eaten portion', async t => {
  const view = await mount(t,{meal:unsupportedIngredientMeal(),language:'en'});
  const {document,$,requests} = view;
  document.querySelector('[data-build-ingredients="1"]').click();
  setIngredientRow(document,0,'chicken','500'); $('ingredient-basis').value = 'batch';
  for (const [yieldWeight,eaten] of [['','100'],['0','100'],['400','500'],['400','0']]) {
    $('ingredient-yield').value = yieldWeight; $('ingredient-consumed').value = eaten;
    $('ingredient-accepted').checked = true; await submitIngredients(view);
    assert.match($('message').textContent,/finished batch and eaten weights/);
  }
  assert.equal(requests.filter(request => request.method === 'POST').length,0);
});

test('Stale ingredient revision retains unsent fields and clearly requires reloading', async t => {
  const view = await mount(t,{meal:unsupportedIngredientMeal(),language:'en',respond:request => request.method === 'POST'
    ? {status:409,body:{detail:'State or revision changed; reload the estimate.'}} : undefined});
  const {document,$,requests,clickLanguage} = view;
  document.querySelector('[data-build-ingredients="1"]').click();
  setIngredientRow(document,0,'chicken','155'); $('ingredient-accepted').checked = true;
  await submitIngredients(view);
  assert.equal($('ingredient-builder').hidden,false);
  assert.equal(document.querySelector('[data-ingredient-grams]').value,'155');
  assert.equal($('ingredient-accepted').checked,true);
  assert.equal($('ingredient-editor-warning').hidden,false);
  assert.equal($('ingredient-submit').disabled,true);
  assert.match($('message').textContent,/entries are preserved/);
  await clickLanguage('zh');
  assert.match($('ingredient-editor-warning').textContent,/填写内容已保留/);
  await submitIngredients(view);
  assert.equal(requests.filter(request => request.method === 'POST').length,1,'Stale draft must not be resubmitted');
});

test('Custom recipe displays explicit batch provenance, reopens for edit, and locks after confirmation', async t => {
  const meal = ingredientRecipeFixture();
  const view = await mount(t,{meal,language:'en',respond:request => request.url.endsWith('/confirm')
    ? {body:{...clone(meal),status:'confirmed',revision:meal.revision+1}} : undefined});
  const {window,document,$,clickLanguage} = view;
  assert.equal($('reply-form').hidden,true);
  $('reply').value = 'An older unsent conversation draft';
  $('reply').dispatchEvent(new window.Event('input',{bubbles:true}));
  assert.equal($('confirm').disabled,false,'Hidden conversation fields cannot block a custom recipe');
  assert.equal($('pending-edit-notice').hidden,true);
  assert.equal($('dialogue').hidden,true);
  assert.match($('review-help').textContent,/Select Edit ingredients/);
  assert.doesNotMatch($('review-help').textContent,/conversation|chat|below/i);
  $('edit-meal').click();
  assert.equal($('dialogue').hidden,false);
  assert.equal($('custom-recipe-guidance').hidden,false);
  assert.match($('evidence').textContent,/User-defined ingredient recipe/);
  assert.match($('evidence').textContent,/allocating 25%/);
  assert.match($('evidence').textContent,/raw edible weight before cooking/);
  document.querySelector('[data-edit-ingredients="0"]').click();
  assert.equal($('ingredient-basis').value,'batch');
  assert.equal($('ingredient-yield').value,'400'); assert.equal($('ingredient-consumed').value,'100');
  assert.equal(document.querySelector('[data-ingredient-food]').value,'chicken');
  assert.equal(document.querySelector('[data-ingredient-grams]').value,'500');
  assert.equal($('ingredient-accepted').checked,false,'Editing requires renewed recipe review');
  await clickLanguage('zh');
  assert.match($('evidence').textContent,/自定义食材配方/);
  assert.match($('review-help').textContent,/修改食材配方/);
  assert.doesNotMatch($('review-help').textContent,/对话|下方/);
  assert.equal($('confirm').disabled,true,'Do not confirm an old estimate while editing ingredients');
  $('ingredient-cancel').click();
  $('confirm').click(); await flush();
  assert.equal($('ingredient-builder').hidden,true);
  assert.equal(document.querySelector('[data-edit-ingredients]'),null);
  assert.equal($('reply-form').hidden,true);
  assert.equal($('confirm').hidden,true);
  assert.equal($('dialogue').hidden,true);
  $('ingredient-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));
  await flush();
  assert.equal(view.requests.filter(request => request.url.endsWith('/ingredients')).length,0);
});

test('Custom meals with outstanding questions direct users to ingredient editing and never to a hidden conversation', async t => {
  const meal = ingredientRecipeFixture('needs_input');
  meal.draft.push({food_id:'rice',name:'白米饭',grams:null});
  meal.questions = [{key:'1.grams',kind:'number',label:'白米饭吃了多少克？请填可食部分重量。',min:0.1,max:10000}];
  const {window, document, $, requests, clickLanguage} = await mount(t,{meal,language:'en'});
  assert.equal($('dialogue').hidden,false);
  assert.equal($('answer-form').hidden,false);
  assert.equal($('answer-submit').hidden,false);
  assert.equal($('answer-help').hidden,false);
  assert.equal($('reply-form').hidden,true);
  assert.match($('answer-help').textContent,/Edit ingredient recipe/);
  assert.doesNotMatch($('answer-help').textContent,/conversation|chat|below/i);
  const before = requests.length;
  $('answer-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));
  await flush();
  assert.equal(requests.length,before);
  assert.match($('message').textContent,/answer|ingredient/i);
  assert.doesNotMatch($('message').textContent,/conversation|chat|below/i);
  await clickLanguage('zh');
  assert.match($('answer-help').textContent,/编辑食材配方/);
  assert.doesNotMatch($('answer-help').textContent,/对话|下方/);
  $('answer-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));
  await flush();
  assert.doesNotMatch($('message').textContent,/对话|下方/);
  document.querySelector('[data-edit-ingredients="0"]').click();
  assert.equal($('ingredient-builder').hidden,false,'The recommended editing action must be available');
  assert.equal(requests.length,before);
});

test('Consumed custom recipe labels ingredient sum and ordinary items expose quantity origins', async t => {
  const meal = ingredientRecipeFixture();
  meal.draft[0].custom_recipe.basis = 'consumed';
  meal.details[0].grams = 520;
  meal.details[0].quantity_provenance = {...meal.details[0].quantity_provenance,basis:'consumed',factor:1,batch_yield_g:null,consumed_g:null};
  const detail = clone(fixtures.tomato_egg_dish.details[0]);
  for (const kind of ['user_grams','portion_reference','default_portion','edible_fraction']) {
    meal.details.push({...detail,quantity_provenance:{kind,input_grams:200,calculated_grams:120,portion_count:2,reference_grams:60}});
  }
  const {$,clickLanguage} = await mount(t,{meal,language:'en'});
  assert.match($('evidence').textContent,/Ingredient weight sum 520g \(not finished cooked weight\)/);
  assert.match($('evidence').textContent,/No default portion was used/);
  assert.match($('evidence').textContent,/200g extracted from your description/);
  assert.match($('evidence').textContent,/2 portions\/counts × reference 60g = 120g/);
  assert.match($('evidence').textContent,/default reference portion of 120g/);
  assert.match($('evidence').textContent,/gross 200g converted to 120g/);
  await clickLanguage('zh');
  assert.match($('evidence').textContent,/非成品熟重/);
  assert.match($('evidence').textContent,/份量依据：未提供克数/);
});

test('Changing a search query clears the old selected ingredient and acceptance, unlike language switching', async t => {
  const view = await mount(t,{meal:unsupportedIngredientMeal()});
  const {window,document,$,clickLanguage,requests} = view;
  document.querySelector('[data-build-ingredients="1"]').click();
  const row = setIngredientRow(document,0,'chicken','150');
  $('ingredient-accepted').checked = true;
  await clickLanguage('en');
  assert.equal(row.querySelector('[data-ingredient-food]').value,'chicken');
  assert.equal($('ingredient-accepted').checked,true);
  const search = row.querySelector('[data-ingredient-search]');
  search.value = 'rice'; search.dispatchEvent(new window.Event('input',{bubbles:true}));
  assert.equal(row.querySelector('[data-ingredient-food]').value,'');
  assert.equal($('ingredient-accepted').checked,false);
  assert.equal(row.querySelector('[data-ingredient-grams]').value,'150','Keep the quantity for review');
  $('ingredient-accepted').checked = true;
  await submitIngredients(view);
  assert.equal(requests.filter(request => request.method === 'POST').length,0);
  assert.match($('message').textContent,/Select an actual catalogue ingredient/);
});

const profileFixture = () => ({
  profile:{age_years:25,height_cm:175,weight_kg:70,sex:'male',goal:'gain_muscle',activity_level:'moderate',strength_training:true,reference_scope:'general_adult',revision:1},
  reference:{status:'estimated',resting_kcal:1673.8,maintenance_kcal:2594.3,activity_factor:1.55,
    calories:2720,protein_g:112,fat_g:90.7,carbs_g:364,reason_codes:[],energy_adjustment_kcal:129.7,
    protein_g_per_kg:1.6,protein_min_g:112,protein_max_g:154,fat_energy_percent:30,
    notes:['这是根据所填资料推算的每日参考，并非测量值或必须达到的指标。']},
});
const trackingFixture = () => {
  const days=Array.from({length:30},(_,index)=>({date:new Date(Date.UTC(2026,9,5+index)).toISOString().slice(0,10),calories:null,weight_kg:null,calorie_source:null,meal_count:0}));
  days[0]={...days[0],calories:0,weight_kg:70,calorie_source:'manual'};
  days[2]={...days[2],calories:155,weight_kg:69.5,calorie_source:'meals',meal_count:1};
  return {today:'2026-11-03',start_date:days[0].date,end_date:days[29].date,days,
    summary:{recorded_days:2,average_calories:77.5,weight_entries:2,weight_change_kg:-0.5,first_weight_kg:70,last_weight_kg:69.5}};
};

test('Profile fields, goal and draft values survive bilingual switching and save with a revision and CSRF header',async t=>{
  const profile=profileFixture();
  const view=await mount(t,{respond:request=>request.url==='/profile'?{body:profile}:undefined});
  const {window,$,clickLanguage,requests}=view;
  assert.match($('profile-calories').textContent,/2,720/);
  $('profile-weight').value='72.5';$('profile-weight').dispatchEvent(new window.Event('input',{bubbles:true}));
  assert.equal($('profile-reference').hidden,true,'Stale reference must hide during edits');
  const count=requests.length;
  await clickLanguage('en');
  assert.equal($('profile-weight').value,'72.5');assert.equal($('profile-goal').value,'gain_muscle');
  assert.match($('profile-title').textContent,/details.*goal/);
  assert.match($('profile-message').textContent,/not saved/);
  assert.equal(requests.length,count);
  $('profile-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await flush();
  const sent=requests.find(request=>request.url==='/profile'&&request.method==='PUT');
  assert.equal(sent.body.weight_kg,72.5);assert.equal(sent.body.goal,'gain_muscle');assert.equal(sent.body.revision,1);
  assert.equal(sent.headers['X-NutriChat-Request'],'1');
  assert.doesNotMatch($('profile-reference').textContent,/[\u3400-\u9fff]/u);
  await clickLanguage('zh');assert.match($('profile-reference').textContent,/增肌/);
});

test('A profile review boundary withholds targets in both languages and leaves meal estimation available',async t=>{
  const profile=profileFixture();profile.reference.status='needs_review';profile.reference.reason_codes=['underweight_reference'];
  profile.reference.calories=null;profile.profile.goal='lose_fat';
  const {$,clickLanguage}=await mount(t,{respond:r=>r.url==='/profile'?{body:profile}:undefined});
  assert.equal($('profile-targets').hidden,true);assert.equal($('profile-review').hidden,false);
  assert.equal($('estimate').disabled,false);
  await clickLanguage('en');assert.match($('profile-review').textContent,/withheld|outside/);
  assert.doesNotMatch($('profile-review').textContent,/[\u3400-\u9fff]/u);
});

test('Legacy profiles require explicit eligibility and training without defaulting to yes',async t=>{
  const profile=profileFixture();
  Object.assign(profile.profile,{strength_training:null,reference_scope:null});
  Object.assign(profile.reference,{status:'needs_review',calories:null,protein_g:null,fat_g:null,carbs_g:null,
    reason_codes:['scope_confirmation_required','training_confirmation_required']});
  const {window,$,requests,clickLanguage}=await mount(t,{respond:r=>r.url==='/profile'?{body:profile}:undefined});
  assert.equal($('profile-editor').open,true);
  assert.equal($('profile-training').value,'');assert.equal($('profile-scope').value,'');
  assert.equal($('profile-targets').hidden,true);assert.equal($('profile-calculation').hidden,true);
  $('profile-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await flush();
  assert.equal(requests.filter(r=>r.url==='/profile'&&r.method==='PUT').length,0,'Unconfirmed required fields cannot save');
  await clickLanguage('en');
  assert.match($('profile-review').textContent,/confirm nutrition reference eligibility/);
  assert.match($('profile-review').textContent,/confirm whether.*resistance training/);
  assert.doesNotMatch($('profile-review').textContent,/[\u3400-\u9fff]/u);
  assert.equal($('profile-training').value,'');assert.equal($('profile-scope').value,'');
});

test('Training No survives language switches and saves a boolean false, not an empty or truthy value',async t=>{
  const profile=profileFixture();
  const {window,$,requests,clickLanguage}=await mount(t,{respond:r=>r.url==='/profile'?{body:profile}:undefined});
  $('profile-goal').value='lose_fat';$('profile-training').value='false';
  $('profile-training').dispatchEvent(new window.Event('input',{bubbles:true}));
  await clickLanguage('en');
  assert.equal($('profile-training').value,'false');assert.equal($('profile-scope').value,'general_adult');
  assert.equal($('profile-reference').hidden,true,'Edited profile must not display old reference');
  $('profile-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await flush();
  const sent=requests.find(r=>r.url==='/profile'&&r.method==='PUT');
  assert.equal(sent.body.strength_training,false);assert.equal(sent.body.reference_scope,'general_adult');
  assert.equal(sent.body.goal,'lose_fat');
});

test('Energy calculation is visible and protein follows weight-based references in both languages',async t=>{
  const profile=profileFixture();
  const {$,clickLanguage}=await mount(t,{respond:r=>r.url==='/profile'?{body:profile}:undefined});
  assert.equal($('profile-calculation').hidden,false);
  assert.equal($('profile-calculation').closest('details'),null,'Resting and maintenance explanation is not collapsed');
  assert.match($('profile-energy-basis').textContent,/1,674.*1\.55.*2,594/);
  assert.match($('profile-goal-basis').textContent,/5%.*129\.7/);
  assert.match($('profile-protein').textContent,/112/);
  assert.match($('profile-macro-basis').textContent,/1\.6.*112–154/);
  await clickLanguage('en');
  assert.match($('profile-goal-basis').textContent,/5%.*129\.7.*default starting point/);
  assert.match($('profile-macro-basis').textContent,/1\.6.*112–154.*not a mandatory/);
  assert.doesNotMatch($('profile-reference').textContent,/[\u3400-\u9fff]/u);
});

test('Fat-loss explanation describes the bounded deficit rather than the retired ten percent policy',async t=>{
  const profile=profileFixture();profile.profile.goal='lose_fat';
  Object.assign(profile.reference,{calories:2210,protein_g:126,fat_g:73.7,carbs_g:260.8,
    energy_adjustment_kcal:-389.1,protein_g_per_kg:1.8});
  const {$,clickLanguage}=await mount(t,{respond:r=>r.url==='/profile'?{body:profile}:undefined});
  assert.match($('profile-goal-basis').textContent,/15%.*500.*389\.1/);
  await clickLanguage('en');
  assert.match($('profile-goal-basis').textContent,/15%.*500.*389\.1/);
  assert.doesNotMatch($('profile-goal-basis').textContent,/10%/);
  assert.match($('profile-calories').textContent,/2,210/);
});

test('Professional guidance and training scope notices explain withheld targets while meal tools remain usable',async t=>{
  const profile=profileFixture();
  Object.assign(profile.profile,{strength_training:false,reference_scope:'professional_guidance'});
  Object.assign(profile.reference,{status:'needs_review',calories:null,protein_g:null,fat_g:null,carbs_g:null,
    reason_codes:['professional_guidance_required','strength_training_required']});
  const {$,clickLanguage}=await mount(t,{respond:r=>r.url==='/profile'?{body:profile}:undefined});
  assert.equal($('profile-training').value,'false');
  assert.equal($('profile-targets').hidden,true);assert.equal($('profile-calculation').hidden,true);
  assert.equal($('estimate').disabled,false);
  await clickLanguage('en');
  assert.match($('profile-review').textContent,/professional assessment/);
  assert.match($('profile-review').textContent,/require regular resistance training/);
  assert.doesNotMatch($('profile-review').textContent,/[\u3400-\u9fff]/u);
});

test('A stale profile revision preserves entered values and requires reloading before another save',async t=>{
  const profile=profileFixture();
  const {window,$,requests,clickLanguage}=await mount(t,{respond:r=>r.url==='/profile'
    ?r.method==='PUT'?{status:409,body:{detail:'Profile changed'}}:{body:profile}:undefined});
  $('profile-height').value='180';$('profile-height').dispatchEvent(new window.Event('input',{bubbles:true}));
  $('profile-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await flush();
  assert.equal($('profile-height').value,'180');assert.equal($('profile-save').disabled,true);
  assert.equal($('profile-reload').hidden,false);
  await clickLanguage('en');assert.match($('profile-message').textContent,/updated elsewhere/);
  $('profile-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await flush();
  assert.equal(requests.filter(r=>r.url==='/profile'&&r.method==='PUT').length,1);
});

test('Trend lines bridge missing dates without adding data, manual zero remains data, and switching preserves edits',async t=>{
  const tracking=trackingFixture();
  const view=await mount(t,{respond:r=>r.url.startsWith('/tracking')?{body:tracking}:undefined});
  const {window,$,document,requests,clickLanguage}=view;
  assert.equal($('trend-table-body').children.length,30);
  for(const [id,color] of [['calorie-chart','#246149'],['weight-chart','#477f9b']]){
    const points=$(id).querySelectorAll('circle'),lines=$(id).querySelectorAll(`line[stroke="${color}"]`);
    assert.equal(points.length,2,'Only recorded dates get points');
    assert.equal(lines.length,1,'Connect the two records across the missing date');
    for(const [attribute,point,coordinate] of [['x1',0,'cx'],['y1',0,'cy'],['x2',1,'cx'],['y2',1,'cy']])
      assert.equal(lines[0].getAttribute(attribute),points[point].getAttribute(coordinate));
    assert.ok(Number(points[1].getAttribute('cx'))>Number(points[0].getAttribute('cx')));
  }
  assert.equal($('calorie-chart').querySelector('circle').getAttribute('cy'),'200','Explicit zero stays on the baseline');
  assert.equal($('trend-recorded').textContent,'2 / 30 天');
  assert.equal($('trend-average').textContent,'77.5');
  assert.equal($('trend-table-body').children[0].children[1].textContent,'0');
  assert.equal($('trend-table-body').children[1].children[1].textContent,'—');
  $('daily-calories').value='0';$('daily-weight').value='68.5';
  $('daily-weight').dispatchEvent(new window.Event('input',{bubbles:true}));
  const count=requests.length;await clickLanguage('en');
  assert.equal($('daily-calories').value,'0');assert.equal($('daily-weight').value,'68.5');
  assert.match($('tracking-title').textContent,/Daily check-in/);assert.match(document.querySelector('svg title').textContent,/30-day/);
  assert.match($('calorie-chart').querySelector('desc').textContent,/across missing dates without filling missing values/);
  assert.match(document.querySelector('.trend-note').textContent,/excluded from average calories.*zero values are included/);
  assert.equal(requests.length,count);
  $('daily-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await flush();
  const sent=requests.find(r=>r.method==='PUT'&&r.url.startsWith('/daily-records/'));
  assert.equal(sent.body.manual_calories,0);assert.equal(sent.body.weight_kg,68.5);assert.equal(sent.body.revision,0);
  assert.equal(sent.headers['X-NutriChat-Request'],'1');
});

test('Custom ingredient meal confirmation includes its chosen date and refreshes account trends',async t=>{
  const meal=ingredientRecipeFixture();
  const {window,$,requests,clickLanguage}=await mount(t,{meal,respond:r=>r.url.endsWith('/confirm')
    ?{body:{...meal,status:'confirmed',consumed_on:r.body.consumed_on,revision:meal.revision+1}}:undefined});
  $('meal-date').value='2026-10-27';await clickLanguage('en');
  assert.equal($('meal-date').value,'2026-10-27');
  const before=requests.filter(r=>r.url.startsWith('/tracking')).length;
  $('confirm').click();await flush();
  const sent=requests.find(r=>r.url.endsWith('/confirm'));
  assert.deepEqual(sent.body,{revision:meal.revision,consumed_on:'2026-10-27'});
  assert.equal(sent.headers['X-NutriChat-Request'],'1');
  assert.equal($('meal-date-editor').hidden,true);assert.match($('meal-confirmed-date').textContent,/2026-10-27/);
  assert.ok(requests.filter(r=>r.url.startsWith('/tracking')).length>before);
  assert.equal($('confirm').hidden,true);
});

test('Offline demo hides misleading chat and replaces the complete meal through PATCH before confirmation',async t=>{
  const meal={...clone(fixtures.tomato_egg_dish),food_text:'100g egg',calories:155,details:[],draft:[]};
  const {window,$,requests}=await mount(t,{meal,language:'en',respond:r=>{
    if(r.url==='/foods')return {body:{provider:'demo',catalogue:{foods:clone(foods)}}};
    if(r.method==='PATCH')return {body:{...meal,food_text:r.body.food_text,calories:310,revision:meal.revision+1}};
  }});
  assert.equal($('reply-form').hidden,true);assert.equal($('offline-correction').hidden,false);
  assert.equal($('dialogue').hidden,true);
  assert.match($('review-help').textContent,/Edit this meal.*full description/);
  $('edit-meal').click();
  assert.equal($('dialogue').hidden,false);
  $('offline-meal').value='200g egg';$('offline-correction').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await flush();
  assert.equal($('calories').textContent,'310');
  assert.equal($('confirm').disabled,false);
  assert.equal($('pending-edit-notice').hidden,true);
  const sent=requests.find(r=>r.method==='PATCH');
  assert.deepEqual(sent.body,{food_text:'200g egg',revision:meal.revision});
  assert.equal(sent.headers['X-NutriChat-Request'],'1');
  assert.equal(requests.filter(r=>r.url.endsWith('/reply')).length,0);
});

test('Restored meals are scoped to the signed-in user and legacy shared storage is removed',async t=>{
  const meal=clone(fixtures.tomato_egg_dish);
  const {window,$,requests}=await mount(t,{meal,storage:{'nutrichat.analysis':'shared-old','nutrichat.analysis.user.other':'private-other'}});
  assert.equal(window.localStorage.getItem('nutrichat.analysis'),null);
  assert.equal(window.localStorage.getItem('nutrichat.analysis.user.other'),'private-other');
  assert.ok(requests.some(r=>r.url==='/analyses/'+meal.id));
  assert.ok(requests.every(r=>!r.url.includes('shared-old')&&!r.url.includes('private-other')));
  assert.equal($('account-name').textContent,'UI user');
});

test('An in-flight meal response cannot restore private content after another tab changes the session',async t=>{
  let finish;const meal=clone(fixtures.tomato_egg_dish);
  const {window,$}=await mount(t,{respond:r=>r.method==='POST'&&r.url==='/analyses'
    ?new Promise(resolve=>{finish=resolve;}):undefined});
  $('meal').value='private meal';$('meal-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await flush();
  assert.equal(typeof finish,'function');
  window.dispatchEvent(new window.StorageEvent('storage',{key:'nutrichat.auth-change',newValue:'logout'}));
  finish({body:meal});await flush();
  assert.equal($('meal').value,'');assert.equal($('result').hidden,true);assert.equal($('history').textContent,'');
  assert.equal($('profile-reference').hidden,true);assert.equal($('trend-results').hidden,true);
  assert.equal($('estimate').disabled,true);
});

async function mountAccount(t){
  const dom=new JSDOM(fs.readFileSync(path.join(staticDir,'account.html'),'utf8'),{url:'http://localhost:8003/login',runScripts:'outside-only'});
  t.after(()=>dom.window.close());const {window}=dom, requests=[], errors=[];
  window.addEventListener('error',event=>errors.push(event.error||event.message));
  window.fetch=async(url,options={})=>{
    requests.push({url,options});const status=url==='/auth/config'?200:401;
    return {ok:status===200,status,headers:{get:()=> 'application/json'},json:async()=>url==='/auth/config'?{registration_enabled:true}:{detail:'Authentication required'}};
  };
  for(const script of ['i18n.js','account-i18n.js'])window.eval(fs.readFileSync(path.join(staticDir,script),'utf8'));
  const inline=Array.from(window.document.scripts).find(script=>!script.src);window.eval(inline.textContent);await flush();
  assert.deepEqual(errors,[]);return {window,$:id=>window.document.getElementById(id),requests,errors};
}

test('Account form switches language without losing credentials or changing the selected registration tab',async t=>{
  const {window,$,requests,errors}=await mountAccount(t);
  $('register-tab').click();$('username').value='tester';$('password').value='  keep spaces  ';$('confirm-password').value='  keep spaces  ';
  const count=requests.length;$('language-en').click();await flush();
  assert.equal($('password').value,'  keep spaces  ');assert.equal($('confirm-password').value,'  keep spaces  ');
  assert.equal($('register-tab').getAttribute('aria-selected'),'true');assert.match($('account-title').textContent,/Create/);
  assert.match($('password-hint').textContent,/Spaces/);assert.equal(requests.length,count);
  $('account-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await flush();
  const sent=requests.find(r=>r.url==='/auth/register');
  assert.equal(JSON.parse(sent.options.body).password,'  keep spaces  ');assert.equal(sent.options.headers['X-NutriChat-Request'],'1');
  assert.match($('message').textContent,/Incorrect username/);
  $('language-zh').click();await flush();assert.match($('message').textContent,/用户名或密码/);assert.deepEqual(errors,[]);
});


test('Workspace starts at meals, exposes every task and supports keyboard navigation', async t => {
  const {window,document,$,requests}=await mount(t);
  const views=['meal','diary','trends','profile'];
  const before=requests.length;
  assert.equal($('panel-meal').hidden,false);
  for(const name of views.slice(1))assert.equal($('panel-'+name).hidden,true);
  assert.ok($('panel-meal').contains($('meal-form')));
  assert.ok($('panel-diary').contains($('daily-form')));
  assert.ok($('panel-diary').contains($('recent-form')));
  assert.ok($('panel-trends').contains($('trend-form')));
  assert.ok($('panel-profile').contains($('profile-form')));
  $('tab-meal').focus();
  $('tab-meal').dispatchEvent(new window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
  assert.equal(document.activeElement,$('tab-diary'));
  assert.equal($('tab-diary').getAttribute('aria-selected'),'true');
  assert.equal($('panel-diary').hidden,false);assert.equal($('panel-meal').hidden,true);
  $('tab-diary').dispatchEvent(new window.KeyboardEvent('keydown',{key:'End',bubbles:true}));
  assert.equal(document.activeElement,$('tab-profile'));
  $('tab-profile').dispatchEvent(new window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
  assert.equal(document.activeElement,$('tab-meal'));
  assert.equal(document.querySelectorAll('[role=tab][tabindex="0"]').length,1);
  assert.equal(requests.length,before,'Navigation must not request or submit data');
});

test('Navigation and translation preserve all drafts and disclosure states without requests',async t=>{
  const {window,document,$,requests,clickLanguage}=await mount(t);
  $('meal').value='我的午餐';$('reply').value='补充细节';
  $('profile-weight').value='72.8';$('profile-weight').dispatchEvent(new window.Event('input',{bubbles:true}));
  $('daily-weight').value='71.2';$('daily-weight').dispatchEvent(new window.Event('input',{bubbles:true}));
  $('daily-calories').value='0';$('daily-exercise').value='250';$('coverage-lunch').checked=true;
  $('manual-intake').open=true;$('coverage-panel').open=true;$('profile-editor').open=true;
  const before=requests.length;
  for(const view of ['diary','profile','meal','trends','diary'])$('tab-'+view).click();
  await clickLanguage('en');await clickLanguage('zh');
  assert.equal($('panel-diary').hidden,false);
  for(const [id,value] of Object.entries({meal:'我的午餐',reply:'补充细节','profile-weight':'72.8','daily-weight':'71.2','daily-calories':'0','daily-exercise':'250'}))assert.equal($(id).value,value);
  assert.equal($('coverage-lunch').checked,true);
  for(const id of ['manual-intake','coverage-panel','profile-editor'])assert.equal($(id).open,true);
  assert.equal(document.querySelector('.skip-link').getAttribute('href'),'#panel-diary');
  assert.equal(requests.length,before);
});

test('Catalogue is bounded, searchable across all foods and progressively expanded',async t=>{
  const {window,$,clickLanguage}=await mount(t);
  assert.equal($('food-list').children.length,20);
  $('foods-more').click();assert.equal($('food-list').children.length,40);
  const target=foods[foods.length-1];
  $('search').value=target.name;$('search').dispatchEvent(new window.Event('input',{bubbles:true}));
  assert.ok($('food-list').textContent.includes(target.name));
  assert.equal($('foods-more').hidden,true);
  await clickLanguage('en');assert.match($('food-count').textContent,/Showing/);
  $('search').value='';$('search').dispatchEvent(new window.Event('input',{bubbles:true}));
  assert.equal($('food-list').children.length,20);
});

test('Food evidence starts compact but expanding it survives language changes',async t=>{
  const {$,clickLanguage}=await mount(t,{meal:clone(fixtures.tomato_egg_dish)});
  const disclosure=$('evidence').querySelector('details');
  assert.equal(disclosure.open,false);
  disclosure.open=true;
  await clickLanguage('en');
  assert.equal($('evidence').querySelector('details').open,true);
  assert.match($('evidence').textContent,/reference|portion|recipe/i);
  assert.equal($('record').closest('details').open,false);
});

test('Reference portions and recipes remain labelled with a visible warning while evidence is collapsed',async t=>{
  for (const kind of ['default_portion','portion_reference']) {
    const meal = clone(fixtures.tomato_egg_dish);
    meal.draft[0].recipe_assumed = true;
    meal.draft.push({food_id:'rice',name:'白米饭',grams:100});
    meal.details.push({food_id:'rice',name:'白米饭',grams:100,
      nutrients:{calories:130,protein_g:2.7,fat_g:0.3,carbs_g:28},sources:[],assumptions:[],
      quantity_provenance:{kind,calculated_grams:100,portion_count:1,reference_grams:100}});
    const {$,clickLanguage} = await mount(t,{meal,language:'en'});
    const evidence = [...$('evidence').children];
    assert.ok(evidence.every(item => item.tagName === 'DETAILS' && !item.open));
    assert.match(evidence[0].querySelector('summary').textContent,/Reference recipe.*210\.2 kcal/);
    assert.match(evidence[1].querySelector('summary').textContent,/Reference portion.*130 kcal/);
    assert.ok(evidence.every(item => item.querySelector('summary .food-badge.reference')),
      'Reference labels must remain in the visible summary');
    assert.equal($('estimate-basis').hidden,false);
    assert.equal($('estimate-basis').closest('[hidden],details'),null);
    assert.match($('estimate-basis').textContent,/reference estimate.*not been individually verified/i);
    await clickLanguage('zh');
    assert.match($('evidence').children[0].querySelector('summary').textContent,/参考配方/);
    assert.match($('evidence').children[1].querySelector('summary').textContent,/参考份量/);
    assert.match($('estimate-basis').textContent,/参考估算.*尚未逐项核实/);
    assert.ok([...$('evidence').children].every(item => !item.open));
  }
});

test('Reviewed recipes and entered ingredient quantities have distinct badges without an unverified-reference warning',async t=>{
  const meal = clone(fixtures.tomato_egg_dish);
  meal.draft[0].recipe_confirmed = true;
  meal.draft[0].recipe_assumed = false;
  meal.details[0].quantity_provenance = {kind:'user_grams',input_grams:200,calculated_grams:200};
  const {$,clickLanguage} = await mount(t,{meal,language:'en'});
  const summary = $('evidence').querySelector('summary');
  assert.match(summary.textContent,/Entered grams/);
  assert.match(summary.textContent,/Reviewed recipe/);
  assert.equal(summary.querySelector('.reference'),null);
  assert.equal($('estimate-basis').hidden,true);
  await clickLanguage('zh');
  assert.match($('evidence').querySelector('summary').textContent,/按填写克数.*已核对配方/);
  assert.equal($('estimate-basis').hidden,true);
  const custom = await mount(t,{meal:ingredientRecipeFixture(),language:'en'});
  assert.match(custom.$('evidence').querySelector('summary').textContent,/Entered ingredients/);
  assert.equal(custom.$('estimate-basis').hidden,true);
});

test('Confirming a reference estimate preserves its warning but only suggests actions available on a saved meal',async t=>{
  const meal = clone(fixtures.tomato_egg_dish);
  meal.draft[0].recipe_assumed = true;
  const {$,requests,clickLanguage} = await mount(t,{meal,respond:request =>
    request.url.endsWith('/confirm')
      ? {body:{...meal,status:'confirmed',revision:meal.revision+1,
        consumed_on:request.body.consumed_on}} : undefined});
  assert.equal($('edit-meal').hidden,false);
  assert.equal($('switch-mode').hidden,false);
  assert.match($('estimate-basis').textContent,/可以修改这餐或切换进阶版/);
  await clickLanguage('en');
  assert.match($('estimate-basis').textContent,/Edit the meal or switch to Advanced/);
  $('meal-date').value = '2026-10-27';
  $('confirm').click();
  await flush();
  assert.equal(requests.filter(request => request.url.endsWith('/confirm')).length,1);
  assert.equal($('edit-meal').hidden,true);
  assert.equal($('switch-mode').hidden,true);
  assert.equal($('estimate-basis').hidden,false);
  assert.match($('estimate-basis').textContent,/not been individually verified.*confirmed and saved.*Start a new meal/i);
  assert.doesNotMatch($('estimate-basis').textContent,/Edit the meal|switch to Advanced/i);
  const requestCount = requests.length;
  await clickLanguage('zh');
  assert.match($('estimate-basis').textContent,/尚未逐项核实.*已确认保存.*开始新的一餐/);
  assert.doesNotMatch($('estimate-basis').textContent,/可以修改这餐|切换进阶版/);
  await clickLanguage('en');
  assert.equal(requests.length,requestCount,'Changing saved-meal copy must not send new requests');
  assert.match($('estimate-basis').textContent,/Start a new meal/);
  assert.equal($('calories').textContent,String(meal.calories));
  assert.equal($('evidence').querySelector('details').open,false);
});

test('Opening a saved meal returns to its visible workspace, then new meal focuses input',async t=>{
  const meal=clone(fixtures.tomato_egg_dish);
  const {window,document,$}=await mount(t,{meal});
  $('tab-diary').click();$('recent').value=meal.id;
  $('recent-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await flush();
  assert.equal($('panel-meal').hidden,false);assert.equal($('panel-diary').hidden,true);
  assert.equal($('result').hidden,false);
  assert.equal(document.activeElement,$('heading-meal'));
  $('new').click();assert.equal(document.activeElement,$('meal'));
  assert.equal($('meal').value,'');assert.equal($('step-describe').getAttribute('aria-current'),'step');
});

test('Queued meal polling never switches the selected view or resets diary edits',async t=>{
  const completed=clone(fixtures.tomato_egg_dish),queued={...completed,status:'queued',details:[]};
  let next=queued;
  const {$,requests,timers,clickLanguage}=await mount(t,{meal:queued,respond:r=>r.url==='/analyses/'+queued.id?{body:next}:undefined});
  $('tab-diary').click();$('daily-weight').value='71.5';
  next=completed;const poll=Array.from(timers.values())[0];assert.ok(poll);await poll();await flush();
  assert.equal($('panel-diary').hidden,false);assert.equal($('panel-meal').hidden,true);
  assert.equal($('daily-weight').value,'71.5');
  const before=requests.length;await clickLanguage('en');assert.equal(requests.length,before);
  $('tab-meal').click();assert.equal($('result').hidden,false);
});

test('Example chips fill the description without sending it or erasing an active estimate',async t=>{
  const {$,document,requests}=await mount(t);
  const before=requests.length;
  document.querySelector('[data-example]').click();
  assert.match($('meal').value,/番茄炒蛋/);assert.equal(requests.length,before);
  const active=await mount(t,{meal:clone(fixtures.tomato_egg_dish)});
  assert.equal(active.$('meal-examples').hidden,true);
});

test('Reloading a conflicted profile refreshes saved balance while preserving dirty diary drafts',async t=>{
  let latest=false;
  const profile=profileFixture();
  const {window,$,requests}=await mount(t,{respond:r=>{
    if(r.url==='/profile'){
      if(r.method==='PUT')return {status:409,body:{detail:'Profile changed'}};
      const value=clone(profile);if(latest){value.profile.revision=2;value.reference.resting_kcal=1880;}
      return {body:value};
    }
    if(r.url.startsWith('/daily-records/'))return {body:{date:'2026-11-03',revision:1,manual_calories:2000,calories:2000,calorie_source:'manual',weight_kg:70,meal_count:0,meal_calories:null,exercise_calories:0,intake_coverage:{},baseline_expenditure_kcal:latest?2256:2136,balance_type:'deficit',balance_kcal:latest?256:136}};
  }});
  $('profile-height').value='185';$('profile-height').dispatchEvent(new window.Event('input',{bubbles:true}));
  $('profile-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await flush();
  assert.equal($('profile-reload').hidden,false);latest=true;$('profile-reload').click();await flush();
  assert.match($('daily-balance-value').textContent,/256/);
  assert.equal($('manual-intake').open,true,'An existing manual override must be discoverable');
  $('daily-weight').value='72.2';$('daily-weight').dispatchEvent(new window.Event('input',{bubbles:true}));
  const before=requests.filter(r=>r.url.startsWith('/daily-records/')).length;
  $('profile-reload').click();await flush();
  assert.equal($('daily-weight').value,'72.2');
  assert.equal(requests.filter(r=>r.url.startsWith('/daily-records/')).length,before);
});


test('Returning after Hong Kong midnight refreshes allowed dates without overwriting a diary draft',async t=>{
  let day='2026-11-03';
  const {window,$,requests}=await mount(t,{respond:r=>r.url.startsWith('/tracking')
    ?{body:{...trackingFixture(),today:day}}:undefined});
  $('tab-diary').click();$('daily-weight').value='73.4';
  $('daily-weight').dispatchEvent(new window.Event('input',{bubbles:true}));
  const before=requests.filter(r=>r.url.startsWith('/daily-records/')).length;
  day='2026-11-04';const OriginalDate=window.Date;
  window.Date=class extends OriginalDate{constructor(...args){super(...(args.length?args:['2026-11-04T01:00:00Z']));}};
  window.dispatchEvent(new window.Event('focus'));await flush();
  assert.equal($('daily-date').max,'2026-11-04');assert.equal($('meal-date').max,'2026-11-04');
  assert.equal($('daily-weight').value,'73.4');assert.equal($('daily-date').value,'2026-11-03');
  assert.equal($('panel-diary').hidden,false);
  assert.equal(requests.filter(r=>r.url.startsWith('/daily-records/')).length,before);
});

test('Skip link focuses the active task, and logout failure remains visible from any panel',async t=>{
  const {document,$}=await mount(t,{respond:r=>r.url==='/auth/logout'?{status:500,body:{detail:'unavailable'}}:undefined});
  $('tab-profile').click();document.querySelector('.skip-link').click();
  assert.equal(document.activeElement,$('heading-profile'));assert.equal($('panel-profile').hidden,false);
  $('logout').click();await flush();
  assert.equal($('panel-meal').hidden,false);
  assert.match($('message').textContent,/退出登录未完成/);
  assert.equal($('logout').disabled,false);
});


test('Failed recent-meal opening keeps current meal and visibly reports the failure in Diary',async t=>{
  const meal=clone(fixtures.tomato_egg_dish);let fail=false;
  const {window,$,clickLanguage}=await mount(t,{meal,respond:r=>r.url==='/analyses/'+meal.id&&fail
    ?{status:503,body:{detail:'暂时无法完成营养估算，请稍后再试'}}:undefined});
  $('reply').value='尚未发送的更正';$('tab-diary').click();$('recent').value=meal.id;fail=true;
  $('recent-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await flush();
  assert.equal($('panel-diary').hidden,false);assert.equal($('recent-message').classList.contains('error'),true);
  assert.ok($('recent-message').textContent.length>0);
  assert.equal($('meal').value,meal.food_text);assert.equal($('reply').value,'尚未发送的更正');
  await clickLanguage('en');assert.equal($('recent-message').classList.contains('error'),true);
  fail=false;$('recent-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await flush();
  assert.equal($('panel-meal').hidden,false);assert.equal($('recent-message').classList.contains('error'),false);
  assert.equal($('message').textContent,'Your meal record is open.');
  await clickLanguage('zh');assert.equal($('message').textContent,'已打开你的餐食记录。');
});

test('Invalid manual calories reveal their closed disclosure before native validation',async t=>{
  const {window,$,requests,clickLanguage}=await mount(t);
  $('tab-diary').click();$('daily-calories').value='-1';
  $('daily-calories').dispatchEvent(new window.Event('input',{bubbles:true}));
  $('manual-intake').open=false;
  assert.equal($('daily-form').checkValidity(),false);
  assert.equal($('manual-intake').open,true);
  assert.equal($('panel-diary').hidden,false);
  assert.equal($('daily-calories').value,'-1');
  assert.equal($('daily-message').classList.contains('error'),true);
  assert.match($('daily-message').textContent,/允许范围/);
  await clickLanguage('en');assert.match($('daily-message').textContent,/allowed range/);
  assert.equal(requests.some(r=>r.method==='PUT'),false);
});
