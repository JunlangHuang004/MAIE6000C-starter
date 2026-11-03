/* The UI language changes presentation only; API payloads and saved facts stay unchanged. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const I = window.NutriI18n;
  let analysis = null, busy = false, timer = null, catalogue = [];
  let questionVersion = '', notice = {raw:'', error:false};
  let ingredientEditor = null;
  let currentUser=null,sessionVersion=0,loggingOut=false,recentVersion=0,provider=null,recentRecords=[];
  const A=window.NutriAccountI18n.text;
let profile=null,profileReference=null,profileLoaded=false,profileLoading=false,profileSaving=false,profileDirty=false,profileConflict=false,profileRequest=0;
let tracking=null,trackingToday=null,trackingLoading=false,trackingRequest=0;
let dailyRecord=null,dailyLoaded=false,dailyLoading=false,dailySaving=false,dailyDirty=false,dailyConflict=false,dailyRequest=0,mealDateAnalysisId=null;
const profileFields={age_years:'profile-age',height_cm:'profile-height',weight_kg:'profile-weight',sex:'profile-sex',goal:'profile-goal',activity_level:'profile-activity'};
const authEventKey='nutrichat.auth-change';
const stored={get:I.storageGet,set:I.storageSet,remove:I.storageRemove};
const analysisKey=()=>currentUser?'nutrichat.analysis.user.'+currentUser.id:null;
const interrupted=()=>Object.assign(Error(A('登录状态已改变')),{silent:true});

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
    let value = notice.key ? I.t(notice.key, notice.values) : notice.raw ? I.systemText(notice.raw) : '';
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
    window.NutriAccountI18n.apply();
  }
  function changeLanguage(language) {
    I.setLanguage(language);
    applyStaticLanguage();
    render();
    translateIngredientEditor();
    showFoods();
    $('profile-editor-title').textContent=A(profile?'修改个人资料':'填写个人资料');
    $('profile-badge').textContent=A(profileConflict?'资料已在别处更新':profileDirty?'有未保存修改':!profileLoaded?'正在读取':!profile?'尚未填写':profileReference?.status==='estimated'?'已保存 · 参考估算':'已保存 · 需评估');
    $('profile-reload').textContent=A(profileConflict?'载入最新资料':'重新读取资料');
    renderProfileReference();renderDailySource();if(tracking)renderTracking(tracking);renderRecent();
  }
function clearSession(){sessionVersion++;clearTimeout(timer);timer=null;analysis=null;currentUser=null;busy=false;
 clearProfile();clearTracking();closeIngredientEditor();questionVersion='';recentVersion++;recentRecords=[];provider=null;$('offline-meal').value='';
 for(const id of ['meal','reply'])$(id).value='';
 for(const id of ['history','questions','evidence'])$(id).replaceChildren();
 for(const id of ['record','interpreted','status'])$(id).textContent='';
 for(const id of ['calories','protein_g','carbs_g','fat_g'])$(id).textContent='—';
 $('recent').replaceChildren(el('option',A('请先登录')));$('recent-message').textContent='';message('');
 $('account-name').textContent=A('已退出当前账号');render();
}
function goToLogin(){clearSession();location.replace('/login?expired=1')}
async function api(path,method='GET',body){
 const version=sessionVersion;
 const headers={'Content-Type':'application/json'};
 if(method!=='GET'&&method!=='HEAD')headers['X-NutriChat-Request']='1';
 let res;try{res=await fetch(path,{method,headers,credentials:'same-origin',cache:'no-store',...(body!==undefined?{body:JSON.stringify(body)}:{})})}catch(e){if(version!==sessionVersion)throw interrupted();throw Error(A('连接暂时不可用，请检查网络后重试'))}
 if(version!==sessionVersion)throw interrupted();
 if(res.status===401||(res.redirected&&new URL(res.url).pathname==='/login')){goToLogin();throw interrupted()}
 if(res.status===204)return null;
 const type=res.headers.get('content-type')||'';if(!type.includes('application/json'))throw Error('连接暂时不可用，请稍后重试');
 const data=await res.json();if(version!==sessionVersion)throw interrupted();
 if(!res.ok)throw Object.assign(Error(Array.isArray(data.detail)?data.detail.map(x=>x.msg).join('\n'):data.detail||'请求失败'),{status:res.status});return data;
}

  function controls() {
    const locked = !currentUser || busy || analysis?.status === 'queued';
    profileControls();trackingControls();$('meal-date').disabled=locked||analysis?.status!=='completed';
    $('recent').disabled=locked;$('recent-open').disabled=locked||!$('recent').value;$('recent-refresh').disabled=!currentUser||busy;
    $('offline-meal').disabled=locked;$('offline-submit').disabled=locked;
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
    $('mode').disabled = !currentUser || !!analysis || busy;
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
function profileMessage(text,error=false){window.NutriAccountI18n.message('profile-message',text,error);}
function profileControls(){const locked=!currentUser||!profileLoaded||profileLoading||profileSaving||profileConflict;
 for(const id of Object.values(profileFields))$(id).disabled=locked;
 $('profile-save').disabled=locked||(!profileDirty&&!!profile);$('profile-save').textContent=profileSaving?A('正在保存…'):A('保存并计算参考');
 $('profile-reload').disabled=!currentUser||profileLoading||profileSaving;
 $('profile-form').setAttribute('aria-busy',String(profileLoading||profileSaving));
}
function clearProfile(){profileRequest++;profile=null;profileReference=null;profileLoaded=false;profileLoading=false;profileSaving=false;profileDirty=false;profileConflict=false;
 $('profile-form').reset();$('profile-editor').open=true;$('profile-editor-title').textContent=A('填写个人资料');$('profile-badge').textContent=A('请先登录');profileMessage('');$('profile-reload').hidden=true;
 $('profile-reference').hidden=true;$('profile-review').hidden=true;$('profile-review').replaceChildren();$('profile-notes').replaceChildren();
 for(const id of ['profile-energy-basis','profile-goal-basis','profile-macro-basis'])$(id).textContent='';
 for(const id of ['profile-calories','profile-protein','profile-fat','profile-carbs'])$(id).textContent='—';$('profile-target-title').textContent=A('每天的大概参考');profileControls();
}
const activityNames={sedentary:'久坐',light:'轻度活动',moderate:'中度活动',high:'高度活动'};
const profileNumber=(value,digits=0)=>Number.isFinite(value)?value.toLocaleString(I.getLanguage(),{maximumFractionDigits:digits,minimumFractionDigits:0}):'—';
function renderProfileReference(){const reference=profileReference;$('profile-reference').hidden=!profile||!reference||profileDirty;if(!profile||!reference||profileDirty)return;
 const estimated=reference.status==='estimated';$('profile-target-title').textContent=(profile.goal==='gain_muscle'?A('增肌'):A('减脂'))+A(' · 每日参考');$('profile-targets').hidden=!estimated;$('profile-review').hidden=estimated;
 for(const [id,key] of [['profile-calories','calories'],['profile-protein','protein_g'],['profile-fat','fat_g'],['profile-carbs','carbs_g']])$(id).textContent=estimated?'≈ '+profileNumber(reference[key],key==='calories'?0:1):'—';
 $('profile-energy-basis').textContent=A('采用 Mifflin–St Jeor 公式估计静息需求约 ')+profileNumber(reference.resting_kcal)+A(' kcal / 天；按')+(A(activityNames[profile.activity_level])||A('所选活动量'))+A('（系数 ')+profileNumber(reference.activity_factor,3)+A('）估计，维持当前体重约需 ')+profileNumber(reference.maintenance_kcal)+A(' kcal / 天。');
 $('profile-goal-basis').textContent=profile.goal==='gain_muscle'?A('增肌参考：在估计维持热量上增加约 5%。'):A('减脂参考：在估计维持热量上减少约 10%。');
 $('profile-macro-basis').textContent=A('营养比例暂按蛋白质 25%、脂肪 30%、碳水 45% 的热量分配。这是通用的起点，实际需要会因训练、身体状况和生活习惯而变化。');
 $('profile-notes').replaceChildren();for(const note of reference.notes||[])$('profile-notes').append(el('p',A(note)));
 $('profile-review').replaceChildren();if(!estimated){$('profile-review').append(el('strong',A('资料已保存，暂不提供减脂或增肌目标数值。')));const reasons=new Set();for(const code of reference.reason_codes||[]){reasons.add(code==='underweight_fat_loss'?A('按当前身高体重推算，暂不自动生成减脂参考；建议先咨询专业人士。'):A('计算结果超出本工具自动估算范围，请核对资料并咨询专业人士。'));}if(!reasons.size)reasons.add(A('当前资料需要进一步评估，不能仅靠通用公式给出合适目标。'));for(const reason of reasons)$('profile-review').append(el('p',reason));$('profile-review').append(el('p',A('你仍可照常使用餐食估算。')));}
}
function applyProfile(data){profile=data.profile;profileReference=data.reference;profileLoaded=true;profileDirty=false;profileConflict=false;$('profile-form').reset();
 if(profile)for(const [key,id] of Object.entries(profileFields))$(id).value=profile[key];
 $('profile-editor').open=!profile;$('profile-editor-title').textContent=profile?A('修改个人资料'):A('填写个人资料');$('profile-badge').textContent=!profile?A('尚未填写'):profileReference?.status==='estimated'?A('已保存 · 参考估算'):A('已保存 · 需评估');$('profile-reload').hidden=true;renderProfileReference();
}
async function loadProfile(){if(!currentUser||profileSaving)return;const version=sessionVersion,request=++profileRequest;profileLoading=true;$('profile-reference').hidden=true;profileMessage(A('正在读取个人资料…'));profileControls();
 try{const data=await api('/profile');if(version!==sessionVersion||request!==profileRequest)return;applyProfile(data);profileMessage(profile?A('已载入当前账号的资料。'):A('填写并保存后，会在这里显示你的每日参考。'));}
 catch(e){if(!e.silent&&version===sessionVersion&&request===profileRequest){profileLoaded=false;profileMessage(e.message+A(' 餐食估算仍可照常使用。'),true);$('profile-badge').textContent=A('暂未读取');$('profile-reload').hidden=false;$('profile-reload').textContent=A('重新读取资料');}}
 finally{if(version===sessionVersion&&request===profileRequest){profileLoading=false;profileControls();}}
}
for(const id of Object.values(profileFields))$(id).addEventListener('input',()=>{if(!profileLoaded||profileSaving||profileConflict)return;profileDirty=true;$('profile-badge').textContent=A('有未保存修改');$('profile-reference').hidden=true;profileMessage(A('资料尚未保存。保存后将按新资料重新计算参考。'));profileControls()});
$('profile-reload').addEventListener('click',()=>loadProfile());
$('profile-form').addEventListener('submit',async event=>{event.preventDefault();if(!currentUser||!profileLoaded||profileLoading||profileSaving||profileConflict||!$('profile-form').reportValidity())return;
 const version=sessionVersion,request=++profileRequest;const body={revision:profile?.revision??0};for(const [key,id] of Object.entries(profileFields))body[key]=['age_years','height_cm','weight_kg'].includes(key)?Number($(id).value):$(id).value;
 profileSaving=true;profileMessage(A('正在保存并计算…'));profileControls();
 try{const data=await api('/profile','PUT',body);if(version!==sessionVersion||request!==profileRequest)return;applyProfile(data);profileMessage(A('资料已保存。')+(data.reference?.status==='estimated'?A('下方为每日参考值。'):A('请查看下方的适用范围提示。')));}
 catch(e){if(!e.silent&&version===sessionVersion&&request===profileRequest){if(e.status===409){profileConflict=true;$('profile-badge').textContent=A('资料已在别处更新');profileMessage(A('资料已在其他页面更新。请先载入最新资料，再重新修改；重新载入会替换当前未保存的内容。'),true);$('profile-reload').hidden=false;$('profile-reload').textContent=A('载入最新资料');}else profileMessage(e.message+A(' 当前修改还没有保存，请重试。'),true);}}
 finally{if(version===sessionVersion&&request===profileRequest){profileSaving=false;profileControls();}}
});
function dailyMessage(text,error=false){window.NutriAccountI18n.message('daily-message',text,error);}
function trendMessage(text,error=false){window.NutriAccountI18n.message('trend-message',text,error);}
function trackingControls(){
 const locked=!currentUser||!dailyLoaded||dailyLoading||dailySaving||dailyConflict;
 for(const id of ['daily-calories','daily-weight'])$(id).disabled=locked;
 $('daily-date').disabled=!currentUser||!trackingToday||dailySaving;
 $('daily-save').disabled=locked||!dailyDirty;$('daily-save').textContent=dailySaving?A('正在保存…'):A('保存当天记录');
 $('daily-reload').disabled=!currentUser||dailyLoading||dailySaving;
 $('daily-reload').textContent=dailyConflict?A('载入最新记录'):A('重新读取当天');
 $('daily-form').setAttribute('aria-busy',String(dailyLoading||dailySaving));
 $('trend-end').disabled=!currentUser||!trackingToday||trackingLoading;
 $('trend-refresh').disabled=!currentUser||trackingLoading;$('trend-today').disabled=!currentUser||!trackingToday||trackingLoading;
 $('trend-refresh').textContent=trackingLoading?A('正在读取…'):A('查看趋势');
 $('trend-results').setAttribute('aria-busy',String(trackingLoading));
}
function clearTracking(){
 trackingRequest++;dailyRequest++;tracking=null;trackingToday=null;trackingLoading=false;
 dailyRecord=null;dailyLoaded=false;dailyLoading=false;dailySaving=false;dailyDirty=false;dailyConflict=false;mealDateAnalysisId=null;
 $('daily-form').reset();$('trend-form').reset();$('meal-date').value='';$('meal-date-editor').hidden=true;$('meal-confirmed-date').hidden=true;$('meal-confirmed-date').textContent='';
 for(const id of ['daily-source','trend-period','trend-table-caption','trend-weight-count'])$(id).textContent='';
 for(const id of ['trend-recorded','trend-average','trend-weight-change'])$(id).textContent='—';
 for(const id of ['calorie-chart','weight-chart','trend-table-body'])$(id).replaceChildren();
 $('trend-results').hidden=true;dailyMessage('');trendMessage('');trackingControls();
}
function renderMealDate(){
 const state=analysis?.status;$('meal-date-editor').hidden=state!=='completed';$('meal-confirmed-date').hidden=state!=='confirmed';
 if(analysis&&mealDateAnalysisId!==analysis.id){mealDateAnalysisId=analysis.id;$('meal-date').value=analysis.consumed_on||trackingToday||'';}
 $('meal-confirmed-date').textContent=state==='confirmed'?(analysis.consumed_on?A('食用日期：')+analysis.consumed_on+A('（香港时间）'):A('这条旧记录未提供食用日期。')):'';
}
function dateIsValid(value,min='2000-01-01'){
 if(!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
 const d=new Date(value+'T00:00:00Z');return !Number.isNaN(d.valueOf())&&d.toISOString().slice(0,10)===value&&value>=min&&(!trackingToday||value<=trackingToday);
}
function renderDailySource(){
 if(!dailyRecord){$('daily-source').textContent='';return;}
 const count=dailyRecord.meal_count;const meals=count?count+A(' 餐已确认 · 合计 ')+profileNumber(dailyRecord.meal_calories,1)+' kcal':A('还没有已确认餐食');
 $('daily-source').textContent=dailyRecord.calorie_source==='manual'
  ?A('已保存：手动总量 ')+profileNumber(dailyRecord.calories,1)+' kcal。'+meals+A('；餐食汇总不再叠加。')
  :dailyRecord.calorie_source==='meals'?A('已保存：自动汇总 ')+profileNumber(dailyRecord.calories,1)+A(' kcal，来自 ')+count+A(' 餐已确认记录。'):A('当天暂无热量记录。确认餐食或填写当天总量后，会显示在趋势中。');
}
function applyDaily(data){
 dailyRecord=data;dailyLoaded=true;dailyDirty=false;dailyConflict=false;
 $('daily-calories').value=data.manual_calories??'';$('daily-weight').value=data.weight_kg??'';renderDailySource();
}
async function loadDaily(date=$('daily-date').value){
 if(!currentUser||dailySaving)return;
 if(!dateIsValid(date)){dailyRequest++;dailyLoaded=false;dailyLoading=false;dailyRecord=null;dailyDirty=false;dailyConflict=false;$('daily-calories').value='';$('daily-weight').value='';$('daily-source').textContent='';dailyMessage(A('请选择 2000-01-01 至今天之间的有效日期。'),true);trackingControls();return;}
 const version=sessionVersion,request=++dailyRequest;dailyLoading=true;dailyLoaded=false;dailyRecord=null;dailyDirty=false;dailyConflict=false;
 $('daily-calories').value='';$('daily-weight').value='';$('daily-source').textContent='';dailyMessage(A('正在读取 ')+date+A(' 的记录…'));trackingControls();
 try{const data=await api('/daily-records/'+encodeURIComponent(date));if(version!==sessionVersion||request!==dailyRequest||$('daily-date').value!==date)return;
  applyDaily(data);dailyMessage(A('已载入 ')+date+A('。填写需要记录的数值，然后保存；留空体重并保存可清除当天体重。'));
 }catch(e){if(!e.silent&&version===sessionVersion&&request===dailyRequest){dailyMessage(e.message+A(' 请点击「重新读取当天」重试。'),true);}}
 finally{if(version===sessionVersion&&request===dailyRequest){dailyLoading=false;trackingControls();}}
}
const svgNode=(tag,attrs={},text)=>{const node=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [key,value]of Object.entries(attrs))node.setAttribute(key,String(value));if(text!==undefined)node.textContent=text;return node;};
function drawTrend(containerId,days,key,unit,color){
 const container=$(containerId);container.replaceChildren();const points=days.map((day,index)=>({date:day.date,index,value:day[key]}));const recorded=points.filter(p=>Number.isFinite(p.value));
 if(!recorded.length){const empty=el('div',unit==='kg'?A('这 30 天还没有体重记录'):A('这 30 天还没有热量记录'));empty.className='chart-empty';container.append(empty);return;}
 const width=640,height=240,left=62,right=20,top=23,bottom=40,plotWidth=width-left-right,plotHeight=height-top-bottom;
 const values=recorded.map(p=>p.value);let low=0,high=Math.max(100,Math.ceil(Math.max(...values)/500)*500);
 if(unit==='kg'){low=Math.floor(Math.min(...values)-1);high=Math.ceil(Math.max(...values)+1);}
 const x=index=>left+index/Math.max(1,days.length-1)*plotWidth,y=value=>top+(high-value)/(high-low)*plotHeight;
 const titleId=containerId+'-title',descId=containerId+'-description';const svg=svgNode('svg',{viewBox:'0 0 '+width+' '+height,role:'img','aria-labelledby':titleId+' '+descId});
 svg.append(svgNode('title',{id:titleId},unit==='kg'?A('30 天体重记录'):A('30 天热量摄入记录')));
 svg.append(svgNode('desc',{id:descId},A('从 ')+days[0].date+A(' 到 ')+days[days.length-1].date+A('，共 ')+recorded.length+A(' 个有数据的日期。单位 ')+unit+A('。缺少记录的日期不连接；完整数值可在下方每日明细中查看。')));
 for(let i=0;i<=4;i++){const value=low+(high-low)*i/4,py=y(value);svg.append(svgNode('line',{x1:left,y1:py,x2:width-right,y2:py,stroke:'#e3e9e1','stroke-width':1}));svg.append(svgNode('text',{x:left-9,y:py+4,'text-anchor':'end',fill:'#587268','font-size':12},profileNumber(value,unit==='kg'?1:0)));}
 const ticks=[0,7,14,21,days.length-1];for(const index of ticks){const px=x(index);svg.append(svgNode('text',{x:px,y:height-12,'text-anchor':index===0?'start':index===days.length-1?'end':'middle',fill:'#587268','font-size':12},days[index].date.slice(5).replace('-','/')));}
 let previous=null;for(const point of points){if(!Number.isFinite(point.value)){previous=null;continue;}if(previous)svg.append(svgNode('line',{x1:x(previous.index),y1:y(previous.value),x2:x(point.index),y2:y(point.value),stroke:color,'stroke-width':2.5}));
  const circle=svgNode('circle',{cx:x(point.index),cy:y(point.value),r:4,fill:color,stroke:'#fff','stroke-width':1.5});circle.append(svgNode('title',{},point.date+' · '+profileNumber(point.value,1)+' '+unit));svg.append(circle);previous=point;}
 container.append(svg);
}
function renderTracking(data){
 const summary=data.summary;$('trend-period').textContent=data.start_date+' — '+data.end_date+A(' · 连续 30 天');
 $('trend-recorded').textContent=summary.recorded_days+A(' / 30 天');$('trend-average').textContent=summary.average_calories==null?'—':profileNumber(summary.average_calories,1);
 $('trend-weight-change').textContent=summary.weight_change_kg==null?'—':(summary.weight_change_kg>0?'+':'')+profileNumber(summary.weight_change_kg,2)+' kg';
 $('trend-weight-count').textContent=summary.weight_entries>=2?summary.weight_entries+A(' 次 · ')+profileNumber(summary.first_weight_kg,2)+' → '+profileNumber(summary.last_weight_kg,2)+' kg':summary.weight_entries+A(' 次记录 · 至少需要两次');
 drawTrend('calorie-chart',data.days,'calories','kcal','#246149');drawTrend('weight-chart',data.days,'weight_kg','kg','#477f9b');
 $('trend-table-body').replaceChildren();for(const day of data.days){const row=el('tr');const dateCell=el('th',day.date);dateCell.scope='row';row.append(dateCell);
  for(const value of [day.calories==null?'—':profileNumber(day.calories,1),day.calorie_source==='manual'?A('手动总量'):day.calorie_source==='meals'?A('餐食汇总'):'—',day.meal_count+A(' 餐'),day.weight_kg==null?'—':profileNumber(day.weight_kg,2)])row.append(el('td',value));$('trend-table-body').append(row);}
 $('trend-table-caption').textContent=data.start_date+A(' 至 ')+data.end_date+A('。— 表示没有数据；手动总量替代当天餐食汇总。');$('trend-results').hidden=false;
}
async function loadTracking(end){
 if(!currentUser)return false;const version=sessionVersion,request=++trackingRequest;trackingLoading=true;$('trend-results').hidden=true;trendMessage(A('正在读取 30 天记录…'));trackingControls();
 try{const data=await api('/tracking'+(end?'?end='+encodeURIComponent(end):''));if(version!==sessionVersion||request!==trackingRequest)return false;
  tracking=data;trackingToday=data.today;for(const id of ['daily-date','trend-end','meal-date'])$(id).max=data.today;
  $('trend-end').value=data.end_date;if(!$('daily-date').value)$('daily-date').value=data.today;if(!$('meal-date').value)$('meal-date').value=data.today;
  renderTracking(data);trendMessage(A('统计仅包含当前账号已保存的记录。'));return true;
 }catch(e){if(!e.silent&&version===sessionVersion&&request===trackingRequest){trendMessage(e.message+A(' 请点击「查看趋势」重试。'),true);}}finally{if(version===sessionVersion&&request===trackingRequest){trackingLoading=false;trackingControls();}}
 return false;
}
async function initializeTracking(){if(await loadTracking())await loadDaily();else if(currentUser)dailyMessage(A('日期暂未读取，请点击「重新读取当天」重试。'),true);}
function refreshCurrentTracking(){const end=$('trend-end').value;if(!trackingToday)return loadTracking();if(!dateIsValid(end,'2000-01-30'))return Promise.resolve(false);return loadTracking(end);}
async function refreshTrackingAfterMeal(){
 const date=analysis?.consumed_on;await refreshCurrentTracking();
 if(!currentUser||$('daily-date').value!==date||dailySaving)return;
 if(dailyDirty){dailyMessage(A('餐食已确认。当前未保存的修改已保留；保存或重新读取当天后可查看最新汇总。'));return;}await loadDaily();
}
$('daily-date').addEventListener('change',()=>{if(!dailySaving)void loadDaily();});
for(const id of ['daily-calories','daily-weight'])$(id).addEventListener('input',()=>{if(!dailyLoaded||dailyLoading||dailySaving||dailyConflict)return;dailyDirty=true;dailyMessage(A('有未保存的修改。保存后更新当天记录和趋势。'));trackingControls();});
$('daily-reload').addEventListener('click',()=>trackingToday?loadDaily():initializeTracking());
$('daily-form').addEventListener('submit',async event=>{
 event.preventDefault();if(!currentUser||!dailyLoaded||dailyLoading||dailySaving||dailyConflict||!dailyDirty||!$('daily-form').reportValidity())return;
 const date=$('daily-date').value;if(!dateIsValid(date)||dailyRecord?.date!==date)return;
 const version=sessionVersion,request=++dailyRequest,body={revision:dailyRecord.revision,weight_kg:$('daily-weight').value===''?null:Number($('daily-weight').value),manual_calories:$('daily-calories').value===''?null:Number($('daily-calories').value)};
 dailySaving=true;dailyMessage(A('正在保存 ')+date+A(' 的记录…'));trackingControls();
 try{const data=await api('/daily-records/'+encodeURIComponent(date),'PUT',body);if(version!==sessionVersion||request!==dailyRequest||$('daily-date').value!==date)return;
  applyDaily(data);dailyMessage(A('已保存 ')+date+'。'+(data.calorie_source==='manual'?A('当天热量使用你填写的总量。'):A('当天热量使用已确认餐食汇总。')));void refreshCurrentTracking();
 }catch(e){if(!e.silent&&version===sessionVersion&&request===dailyRequest){if(e.status===409){dailyConflict=true;dailyMessage(A('这天的记录已在其他页面更新。请点击「载入最新记录」后重新修改；载入会替换当前未保存的内容。'),true);}else dailyMessage(e.message+A(' 当前修改尚未保存，请重试。'),true);}}
 finally{if(version===sessionVersion&&request===dailyRequest){dailySaving=false;trackingControls();}}
});
$('trend-form').noValidate=true;
$('trend-form').addEventListener('submit',event=>{event.preventDefault();if(!trackingToday){void initializeTracking();return;}if($('trend-form').reportValidity())void loadTracking($('trend-end').value);});
$('trend-today').addEventListener('click',()=>loadTracking());


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
    ingredientEditor = null; $('ingredient-builder').hidden = true;
    $('ingredient-form').reset();$('ingredient-rows').replaceChildren();
    $('ingredient-builder-target').textContent='';$('ingredient-editor-warning').hidden=true;controls();
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
    $('reply-form').hidden = provider === 'demo' || !['needs_input','completed','failed'].includes(state) || !!custom;
    $('offline-correction').hidden = provider !== 'demo' || !['completed','failed'].includes(state) || !!custom;
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
      $('review-help').textContent = I.t(state === 'confirmed' ? 'confirmedHelp' : provider==='demo' ? 'offlineReviewHelp' : 'reviewHelp');
      renderEvidence();
    }
    renderMealDate();
    controls();
  }
  function saved(data) {
    if (!currentUser) return;
    analysis = data.analysis || data;
    stored.set(analysisKey(),analysis.id);
    $('offline-meal').value = analysis.food_text;
    void refreshRecent(true);
    $('meal').value = analysis.food_text;
    render(); clearTimeout(timer);
    if (analysis.status === 'queued') {
      message({key:'parsing'}); timer = setTimeout(poll,1200);
    }
  }
  async function poll() {
    if (!currentUser || !analysis) return;
    const id=analysis.id;
    try {
      const next = await api('/analyses/' + encodeURIComponent(id));
      if (!currentUser || analysis?.id !== id) return;
      analysis = next; render();
      if (next.status === 'queued') timer = setTimeout(poll,1500);
      else if (next.status === 'needs_input') message({key:next.questions?.some(q => q.kind === 'unsupported') ? 'unsupportedMessage' : 'needsInputMessage'});
      else if (next.status === 'failed') message(next.error_message || {key:'failedMessage'},true);
      else message({key:'savedMessage'});
      if(next.status!=='queued')void refreshRecent(true);
    } catch (error) { if(!error.silent)message({raw:error.message,recovery:true},true); }
  }
async function submit(work){if(busy||!currentUser)return;const version=sessionVersion;busy=true;controls();try{await work()}catch(e){if(!e.silent&&version===sessionVersion)message(e.message,true)}finally{if(version===sessionVersion){busy=false;controls()}}}

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
$('confirm').addEventListener('click',()=>{
 if(!$('meal-date').reportValidity())return;
 const consumedOn=$('meal-date').value;
 submit(async()=>{
  saved(await api('/analyses/'+analysis.id+'/confirm','POST',{revision:analysis.revision,...(consumedOn?{consumed_on:consumedOn}:{})}));
  message(A('这餐的估算已确认，并计入 ')+(analysis.consumed_on||A('所选日期'))+A(' 的热量记录。'));
  void refreshTrackingAfterMeal();
 });
});
  $('new').addEventListener('click',() => {
    clearTimeout(timer); analysis = null; questionVersion = '';
    stored.remove(analysisKey());
    closeIngredientEditor();$('offline-meal').value='';
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
function renderRecent(){
 const selected=analysis?.id||$('recent').value;$('recent').replaceChildren();
 const empty=el('option',recentRecords.length?A('请选择餐食记录'):A('还没有餐食记录'));empty.value='';$('recent').append(empty);
 for(const record of recentRecords){const date=new Date(record.created_at);const label=(Number.isNaN(date.valueOf())?'':date.toLocaleDateString(I.getLanguage())+' · ')+record.food_text.slice(0,70)+' · '+I.t(record.status);const option=el('option',label);option.value=record.id;$('recent').append(option);}
 if(recentRecords.some(record=>record.id===selected))$('recent').value=selected;
 $('recent-message').textContent=recentRecords.length?A('仅显示当前账号的记录。'):A('开始估算第一餐后，记录会显示在这里。');controls();
}
async function refreshRecent(quiet=false){
 if(!currentUser)return;const version=++recentVersion;
 if(!quiet)$('recent-message').textContent=A('正在读取你的记录…');
 try{const records=await api('/analyses?limit=20');if(version!==recentVersion||!currentUser)return;
  if(!Array.isArray(records))throw Error(A('记录列表暂时不可用，请稍后重试。'));
  recentRecords=records;renderRecent();
 }catch(error){if(!error.silent&&version===recentVersion)$('recent-message').textContent=error.message;}
}
$('recent').addEventListener('change',controls);
$('recent-refresh').addEventListener('click',()=>refreshRecent());
$('recent-form').addEventListener('submit',event=>{event.preventDefault();const id=$('recent').value;if(!id)return;submit(async()=>{clearTimeout(timer);analysis=null;render();$('reply').value='';saved(await api('/analyses/'+encodeURIComponent(id)));if(analysis.status!=='queued')message(A('已打开你的餐食记录。'))})});

$('logout').addEventListener('click',async()=>{
 if(loggingOut)return;loggingOut=true;clearSession();message(A('正在退出登录…'));$('logout').disabled=true;
 try{
  const res=await fetch('/auth/logout',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'X-NutriChat-Request':'1'}});
  if(!res.ok&&res.status!==401)throw Error(A('退出登录未完成，请重试。'));
  stored.set(authEventKey,JSON.stringify({type:'logout',at:Date.now()}));location.replace('/login?logged_out=1');
 }catch(e){message(A('退出登录未完成，请检查网络并点击「重试退出」。'),true);$('logout').textContent=A('重试退出');$('logout').disabled=false;loggingOut=false}
});
window.addEventListener('storage',event=>{if(event.key===authEventKey&&event.newValue){clearSession();location.replace('/login')}});
window.addEventListener('pageshow',event=>{if(event.persisted){clearSession();location.reload()}});

  async function init() {
    applyStaticLanguage(); controls();stored.remove('nutrichat.analysis');
    try {
      currentUser=await api('/auth/me');$('account-name').textContent=currentUser.username;$('logout').disabled=false;controls();
      void refreshRecent();void loadProfile();void initializeTracking();
      const data=await api('/foods');catalogue=data.catalogue.foods;provider=data.provider;
      I.setCatalogue(catalogue);catalogueInfo();showFoods();
      if(provider==='demo')message({key:'demoMessage'});
      const id=stored.get(analysisKey());
      if(id){try{saved(await api('/analyses/'+encodeURIComponent(id)));if(analysis.status==='failed')message(analysis.error_message||{key:'failedMessage'},true);else if(analysis.status==='needs_input')message({key:analysis.questions?.some(q=>q.kind==='unsupported')?'unsupportedMessage':'needsInputMessage'});}catch(error){if(error.status===404){stored.remove(analysisKey());message(A('上次记录已不可用，可以开始新的一餐。'));}else throw error;}}
    } catch(error){if(!error.silent)message(error.message,true);}
  }
  $('offline-correction').addEventListener('submit',event=>{
    event.preventDefault();submit(async()=>{
      const food_text=$('offline-meal').value.trim();if(!food_text)return;
      saved(await api('/analyses/'+analysis.id,'PATCH',{revision:analysis.revision,food_text}));
    });
  });
  init();
})();
