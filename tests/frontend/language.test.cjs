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

test('Unknown-food selection is translated and preserves its original catalogue ID', async t => {
  const meal = clone(fixtures.missing_weight);
  meal.draft[0].food_id = null;
  meal.draft[0].name = 'mysterious pastry';
  meal.questions = [{key:'0.food_id',kind:'food',
    label:'“mysterious pastry”尚未匹配。请选择准确食物；没有合适选项请用下方对话补充食材。',
    options:foods.map(food => ({value:food.id,label:food.name}))}];
  const {document, $, clickLanguage} = await mount(t, {meal});
  document.querySelector('#questions select').value = 'dish_004';
  await clickLanguage('en');
  const select = document.querySelector('#questions select');
  assert.equal(select.value, 'dish_004');
  assert.match(select.selectedOptions[0].textContent, /Mapo/i);
  assert.match($('questions').textContent, /mysterious pastry/);
  assert.doesNotMatch($('questions').textContent, /尚未匹配|请选择准确食物/);
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
