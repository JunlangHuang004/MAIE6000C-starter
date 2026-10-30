/* Isolated DOM checks; no network or model requests are sent.
 * npm install --prefix /tmp/nutrichat-ui-tests --no-audit --no-fund jsdom@26.1.0
 * NODE_PATH=/tmp/nutrichat-ui-tests/node_modules node --test tests/frontend/language.test.cjs
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const {JSDOM} = require('jsdom');

const root = path.resolve(__dirname, '../..');
const staticDir = path.join(root, 'services/api/app/static');
const foods = JSON.parse(fs.readFileSync(path.join(root, 'services/common/data/catalogue.json'))).foods;
const fixtures = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/meal-display.json')));
const clone = value => JSON.parse(JSON.stringify(value));
const flush = async () => { for (let i = 0; i < 4; i++) await new Promise(setImmediate); };

async function mount(t, {meal = null, language, storageBlocked = false, respond} = {}) {
  const dom = new JSDOM(fs.readFileSync(path.join(staticDir, 'index.html'), 'utf8'), {
    url:'http://localhost:8003/app', runScripts:'outside-only', pretendToBeVisual:true,
  });
  t.after(() => dom.window.close());
  const {window} = dom;
  const document = window.document;
  const errors = [];
  window.addEventListener('error', event => errors.push(event.error || event.message));
  if (storageBlocked) {
    Object.defineProperty(window, 'localStorage', {get() {throw new Error('Storage disabled');}});
  } else {
    if (language !== undefined) window.localStorage.setItem('nutrichat.language', language);
    if (meal) window.localStorage.setItem('nutrichat.analysis', meal.id);
  }
  let nextTimer = 0;
  const timers = new Map();
  window.setTimeout = callback => {timers.set(++nextTimer, callback); return nextTimer;};
  window.clearTimeout = id => timers.delete(id);
  const requests = [];
  window.fetch = async (url, options = {}) => {
    const request = {url:String(url), method:options.method || 'GET',
      body:options.body ? JSON.parse(options.body) : undefined};
    requests.push(request);
    let response = respond ? respond(request) : undefined;
    if (response === undefined) {
      if (request.url === '/foods') response = {body:{provider:'qwen', catalogue:{foods:clone(foods)}}};
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
  for (const script of ['catalogue-en.js', 'i18n.js', 'app.js']) {
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

test('English display names cover every food, and every recipe retains an English method', async t => {
  const {window} = await mount(t);
  const entries = window.NUTRICHAT_EN_CATALOGUE;
  assert.deepEqual(Object.keys(entries).sort(), foods.map(food => food.id).sort());
  for (const food of foods) {
    assert.ok(entries[food.id].name.trim(), food.id + ' needs an English name');
    assert.doesNotMatch(entries[food.id].name, /[\u3400-\u9fff]/u, food.id);
    if (food.kind === 'recipe') {
      assert.ok(entries[food.id].method.trim(), food.id + ' needs an English method');
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
  assert.equal(window.localStorage.getItem('nutrichat.analysis'), meal.id);
  assert.equal(requests.length, before);
});

test('Unsaved recipe quantities and approval survive repeated language switches and submit unchanged', async t => {
  const meal = clone(fixtures.mapo_tofu);
  const completed = clone(fixtures.tomato_egg_dish);
  completed.id = meal.id;
  const {window, document, $, requests, clickLanguage} = await mount(t, {meal,
    respond:request => request.method === 'POST' ? {body:{analysis:completed}} : undefined});
  const ingredient = document.querySelector('[data-ingredient="oil"]');
  ingredient.value = '7.5';
  document.querySelector('[data-yield]').value = '700';
  document.querySelector('[data-accept]').checked = true;
  $('reply').value = 'Still editing this reply';
  const before = requests.length;
  await clickLanguage('en');
  assert.equal(document.querySelector('[data-ingredient="oil"]').value, '7.5');
  assert.equal(document.querySelector('[data-yield]').value, '700');
  assert.equal(document.querySelector('[data-accept]').checked, true);
  assert.match($('questions').textContent, /Mapo/i);
  assert.doesNotMatch($('questions').textContent, /整锅|请选择|配方|豆瓣酱/);
  await clickLanguage('zh');
  assert.equal(document.querySelector('[data-ingredient="oil"]').value, '7.5');
  assert.equal(document.querySelector('[data-yield]').value, '700');
  assert.equal(document.querySelector('[data-accept]').checked, true);
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
    meal.food_text = '200克豉油鸡';
    meal.draft = [{food_id:null,name:'豉油鸡',source_text:'豉油鸡',grams:200}];
    const label = '数据库未找到“豉油鸡”的对应食物记录，暂不能估算。请核对菜名，或在下方提供实际食材及各自克数；不会使用其他食物代替。';
    meal.questions = [{key:'0.food_id',kind:'unsupported',label}];
    meal.conversation = [{role:'user',content:meal.food_text},{role:'assistant',content:label}];
    const corrected = {...clone(fixtures.tomato_egg_dish),id:meal.id,mode,revision:meal.revision+1};
    const {window, document, $, requests, clickLanguage} = await mount(t, {meal,
      respond:request => request.method === 'POST' ? {body:{analysis:corrected}} : undefined});
    assert.match($('questions').textContent, /数据库未找到.*豉油鸡.*对应食物记录/);
    assert.equal(document.querySelector('#questions select'), null);
    assert.equal($('answer-submit').hidden, true);
    assert.equal($('answer-submit').disabled, true);
    assert.equal($('reply-form').hidden, false);
    assert.equal($('result').hidden, true);
    assert.equal($('confirm').disabled, true);
    const before = requests.length;
    $('reply').value = '更正：200克番茄炒蛋';
    await clickLanguage('en');
    assert.match($('questions').textContent, /豉油鸡: no corresponding food record/);
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
  meal.draft.push({food_id:null,name:'豉油鸡',grams:200});
  meal.questions.push({key:'1.food_id',kind:'unsupported',
    label:'数据库未找到“豉油鸡”的对应食物记录，暂不能估算。请核对菜名，或在下方提供实际食材及各自克数；不会使用其他食物代替。'});
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
  await clickLanguage('en');
  assert.equal($('confirm').hidden, true);
  assert.equal($('reply-form').hidden, true);
  assert.equal($('switch-mode').hidden, true);
  assert.match($('status').textContent, /confirmed/i);
  assert.match($('history').textContent, /我吃了番茄炒蛋，请保留我的原文。/);
  assert.match($('record').textContent, /3/);
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
  meal.conversation = [{role:'user',content:attack}];
  meal.details[0].sources.push({name:attack,id:'attack',license:'test',url:'javascript:window.__injected=true'});
  const {window, document, $, clickLanguage} = await mount(t, {meal});
  await clickLanguage('en');
  assert.match($('history').textContent, /<img src=x/);
  assert.equal(document.querySelector('#history img'), null);
  assert.equal(document.querySelector('#evidence img'), null);
  assert.equal(document.querySelector('a[href^="javascript:"]'), null);
  assert.equal(window.__injected, undefined);
});

function unsupportedIngredientMeal() {
  const meal = clone(fixtures.missing_weight);
  meal.mode = 'basic'; meal.food_text = '100克熟米饭，200克豉油鸡';
  meal.draft = [{food_id:'rice',name:'熟米饭',grams:100}, {food_id:null,name:'豉油鸡',grams:200}];
  meal.questions = [{key:'1.food_id',kind:'unsupported',label:'数据库未找到“豉油鸡”的对应食物记录，暂不能估算。'}];
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
  assert.match($('ingredient-builder-target').textContent,/第 2 项.*豉油鸡/);
  assert.equal($('ingredient-name').value,'豉油鸡');
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
  assert.equal($('confirm').disabled,true,'Do not confirm an old estimate while editing ingredients');
  $('ingredient-cancel').click();
  $('confirm').click(); await flush();
  assert.equal($('ingredient-builder').hidden,true);
  assert.equal(document.querySelector('[data-edit-ingredients]'),null);
  assert.equal($('reply-form').hidden,true);
  assert.equal($('confirm').hidden,true);
  $('ingredient-form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));
  await flush();
  assert.equal(view.requests.filter(request => request.url.endsWith('/ingredients')).length,0);
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
