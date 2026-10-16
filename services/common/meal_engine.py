"""Source-backed catalogue arithmetic and deterministic clarification slots."""
import json
from functools import lru_cache
from copy import deepcopy
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

DATA = Path(__file__).with_name('data')
KEYS = ('calories', 'protein_g', 'carbs_g', 'fat_g')
PREPARATIONS = {'raw':'生食', 'as_served':'按所选食物的加工状态', 'boiled':'水煮',
                'steamed':'清蒸', 'roasted':'烤', 'stir_fried':'炒', 'fried':'煎／炸',
                'braised':'炖／红烧', 'other':'其他做法'}


@lru_cache(maxsize=1)
def catalogue():
    return json.loads((DATA / 'catalogue.json').read_text())


class ExtractedItem(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    food_id: str | None = Field(default=None, max_length=100)
    name: str = Field(min_length=1, max_length=120)
    grams: float | None = Field(default=None, gt=0, le=10000)
    weight_basis: Literal['raw', 'cooked', 'as_sold'] | None = None
    preparation: Literal['raw', 'as_served', 'boiled', 'steamed', 'roasted',
                         'stir_fried', 'fried', 'braised', 'other'] | None = None
    oil_g: float | None = Field(default=None, ge=0, le=1000)
    portion_count: float | None = Field(default=None, gt=0, le=100)
    portion_unit: Literal['bowl', 'piece', 'cup', 'serving'] | None = None
    recipe_ingredients: dict[str, Annotated[float, Field(ge=0, le=10000)]] | None = None
    recipe_yield_g: float | None = Field(default=None, gt=0, le=10000)
    uncertainty: str | None = Field(default=None, max_length=300)


class ExtractedMeal(BaseModel):
    model_config = ConfigDict(extra='forbid')
    items: list[ExtractedItem] = Field(min_length=1, max_length=30)


def question(key, label, kind='number', **kwargs):
    return dict(key=key, label=label, kind=kind, **kwargs)


def evaluate(draft):
    """Missing information never produces partial meal totals."""
    foods = {f['id']: f for f in catalogue()['foods']}
    questions, details = [], []
    totals = dict.fromkeys(KEYS, 0.0)
    for index, item in enumerate(draft):
        prefix = str(index) + '.'
        food = foods.get(item.get('food_id'))
        name = item['name']
        if not food:
            questions.append(question(prefix+'food_id',
                f'“{name}”尚未匹配。请选择准确食物；没有合适选项请用下方对话补充食材。',
                'food', options=[{'value': f['id'], 'label': f['name']} for f in foods.values()]))
            continue
        name = food['name']
        if (food['kind'] == 'ingredient' and food.get('preparations')
                and item.get('preparation') is not None
                and item['preparation'] not in food['preparations']):
            questions.append(question(prefix+'food_id',
                f'{name}的参考做法与你描述的不一致。请选择吻合的食物条目，'
                '或在下方说明原料生重及实际做法，不能套用另一种熟制数据。', 'food',
                options=[{'value':f['id'], 'label':f['name']} for f in foods.values()]))
            continue
        if item.get('uncertainty'):
            questions.append(question(prefix+'resolved', f'{name}：{item["uncertainty"]} '
                '请核对所选食物，或在下方补充更正。', 'confirm'))
        if item.get('grams') is None:
            questions.append(question(prefix+'grams', f'{name}吃了多少克？请填可食部分重量。',
                                      min=0.1, max=10000))
        if food['kind'] == 'recipe':
            if not item.get('recipe_confirmed'):
                reference = deepcopy(food['recipe'])
                reference['ingredients'].update(item.get('recipe_ingredients') or {})
                reference['yield_g'] = item.get('recipe_yield_g') or reference['yield_g']
                if item.get('oil_g') is not None and item.get('grams'):
                    reference['ingredients']['oil'] = (
                        item['oil_g'] * reference['yield_g'] / item['grams'])
                questions.append(question(prefix+'recipe',
                    f'{name}采用以下参考做法和整锅配方吗？可修改配料克数及成品总重。'
                    '这些是估算假设，不代表你的实际用量。', 'recipe',
                    recipe=reference, method=food['method'],
                    ingredients=[{'id': fid, 'name': foods[fid]['name'], 'grams': grams}
                        for fid, grams in reference['ingredients'].items()]))
            if item.get('weight_basis') != 'cooked':
                questions.append(question(prefix+'weight_basis',
                    f'{name}的食用克数是做熟后的成品重量吗？', 'choice',
                    options=[{'value':'cooked', 'label':'是，熟制成品的可食重量'}]))
        else:
            if item.get('weight_basis') != food['state']:
                states = {'raw':'烹调前的生重', 'cooked':'熟重', 'as_sold':'可食部分净重'}
                state = states[food['state']]
                questions.append(question(prefix+'weight_basis',
                    f'{name}的数据按{state}计算，你提供的是这个重量吗？'
                    '若不是，请在下方说明，不能将生熟重量直接互换。', 'choice',
                    options=[{'value':food['state'], 'label':f'确认，是{state}'}]))
            if item.get('preparation') is None:
                questions.append(question(prefix+'preparation', f'{name}是什么做法？', 'choice',
                    options=[{'value':v, 'label':n} for v,n in [
                        ('as_served','按食物名称所示直接食用'), ('raw','生食'),
                        ('boiled','水煮'), ('steamed','清蒸'), ('roasted','烤'),
                        ('stir_fried','炒'), ('fried','煎／炸'), ('braised','炖／红烧'),
                        ('other','其他做法')]]))
            prep = item.get('preparation')
            if (prep in ('stir_fried','fried','braised','roasted','other')
                    and item.get('oil_g') is None):
                questions.append(question(prefix+'oil_g',
                    f'{name}这一份实际吃进去的额外油脂有多少克？不是整锅用油量；无额外油填 0。'
                    '糖、酱料及其他配料请在下方补充。', min=0, max=1000))
        if any(q['key'].startswith(prefix) for q in questions):
            continue
        grams = item['grams']
        if food['kind'] == 'recipe':
            recipe = item.get('recipe') or food['recipe']
            nutrients = dict.fromkeys(KEYS, 0.0)
            components = []
            for fid, weight in recipe['ingredients'].items():
                ingredient = foods[fid]
                components.append(f'{ingredient["name"]} {weight:g}g')
                for key in KEYS:
                    nutrients[key] += ingredient['nutrients'][key] * weight / 100
            factor = grams / recipe['yield_g']
            nutrients = {key: value * factor for key, value in nutrients.items()}
            assumptions = [f'参考做法：{food["method"]}',
                f'整锅成品 {recipe["yield_g"]:g}g；本次食用 {grams:g}g',
                '整锅配料：'+'、'.join(components),
                ('基础版参考配方，未经逐项确认；不是实测菜肴营养。'
                 if item.get('recipe_assumed') else '参考配方已由用户确认；不是实测菜肴营养。')]
            sources = [foods[fid]['source'] for fid in recipe['ingredients']]
        else:
            nutrients = {k:food['nutrients'][k]*grams/100 for k in KEYS}
            oil = item.get('oil_g') or 0
            if oil:
                for key in KEYS:
                    nutrients[key] += foods['oil']['nutrients'][key]*oil/100
            assumptions = [f'按 {food["name"]} 的每100g可食部分数据计算',
                f'做法：{PREPARATIONS[item["preparation"]]}；另计食用油 {oil:g}g',
                '烹调失水不自动换算；额外糖、酱料需作为食材补充。']
            sources = [food['source']]
            if oil:
                sources.append(foods['oil']['source'])
        for key in KEYS:
            totals[key] += nutrients[key]
        details.append(dict(name=name, grams=grams, food_id=food['id'],
                            nutrients={k:round(v,1) for k,v in nutrients.items()},
                            assumptions=assumptions, sources=sources))
    return dict(draft=draft, questions=questions, details=details if not questions else [],
                **(dict.fromkeys(KEYS) if questions else {k:round(v,1) for k,v in totals.items()}),
                interpreted_food_text='；'.join(f'{d["name"]} {d["grams"]:g}g' for d in details)
                if not questions else None)


def apply_answers(draft, answers, mode='advanced'):
    """Only answer slots actually issued by the server; no client-provided nutrition."""
    draft = deepcopy(draft)
    pending = {q['key']:q for q in evaluate_mode(draft, mode)['questions']}
    if not answers or any(k not in pending for k in answers):
        raise ValueError('回答已过期或字段不正确，请刷新后重试。')
    for key,value in answers.items():
        q = pending[key]
        i, field = key.split('.',1)
        item = draft[int(i)]
        if q['kind'] in ('choice','food'):
            if value not in [opt['value'] for opt in q['options']]:
                raise ValueError('请选择提供的选项。')
            item[field] = value
            if field == 'food_id':
                item.update(weight_basis=None, preparation=None, oil_g=None,
                            uncertainty=None, recipe_confirmed=False)
        elif q['kind'] == 'number':
            if isinstance(value,bool) or not isinstance(value,(int,float)):
                raise ValueError('重量必须是数字。')
            if not q['min'] <= value <= q['max']:
                raise ValueError('重量超出允许范围。')
            item[field] = value
        elif q['kind'] == 'confirm':
            if value is not True:
                raise ValueError('请确认或补充说明。')
            item['uncertainty'] = None
        elif q['kind'] == 'recipe':
            if not isinstance(value,dict) or set(value) != {'ingredients','yield_g'}:
                raise ValueError('请提供完整配方和成品重量。')
            original = q['recipe']['ingredients']
            if (not isinstance(value['ingredients'],dict)
                    or set(value['ingredients']) != set(original)):
                raise ValueError('配方食材不匹配；新增食材请通过对话补充。')
            weights = [value['yield_g'], *value['ingredients'].values()]
            if any(isinstance(v,bool) or not isinstance(v,(int,float))
                   or not 0 <= v <= 10000 for v in weights):
                raise ValueError('配料重量必须在 0 到 10000 克之间。')
            if value['yield_g'] <= 0 or sum(value['ingredients'].values()) <= 0:
                raise ValueError('成品和配料总重必须大于 0。')
            item['recipe'] = value
            item['recipe_confirmed'] = True
    return draft


def evaluate_mode(draft, mode='advanced'):
    """Basic uses labelled assumptions on a copy, never saves them as user facts."""
    if mode == 'advanced':
        return evaluate(draft)
    assumed = deepcopy(draft)
    foods = {f['id']: f for f in catalogue()['foods']}
    assumptions = []
    for item in assumed:
        notes = []
        food = foods.get(item.get('food_id'))
        if not food:
            assumptions.append(notes)
            continue
        if item.get('grams') is None:
            per_portion = food.get('default_portion_g', 200 if food['kind']=='recipe' else 100)
            count = item.get('portion_count') or 1
            item['grams'] = min(per_portion * count, 10000)
            if per_portion * count > 10000:
                item['grams'] = None
                assumptions.append(['份量过大，请填写实际克数。'])
                continue
            notes.append(f'未提供克数，暂按 {count:g} 份、每份 {per_portion:g}g，'
                         f'共 {item["grams"]:g}g 估算。')
        if item.get('weight_basis') is None:
            item['weight_basis'] = food['state']
            state = {'raw':'生可食重量','cooked':'熟可食重量','as_sold':'可食净重'}[food['state']]
            notes.append(f'未说明重量状态，暂按{state}计算。')
        if item.get('uncertainty'):
            notes.append('待核实：'+item['uncertainty'])
            item['uncertainty'] = None
        if food['kind']=='recipe':
            recipe = deepcopy(food['recipe'])
            recipe['ingredients'].update(item.get('recipe_ingredients') or {})
            recipe['yield_g'] = item.get('recipe_yield_g') or recipe['yield_g']
            if item.get('oil_g') is not None:
                recipe['ingredients']['oil'] = item['oil_g']*recipe['yield_g']/item['grams']
            item['recipe'] = item.get('recipe') or recipe
            item['recipe_assumed'] = not item.get('recipe_confirmed', False)
            item['recipe_confirmed'] = True
            if item['recipe_assumed']:
                notes.append('基础版暂用参考配方及整锅成品重量；未逐项核实，可切换进阶版修改。')
        else:
            if item.get('preparation') is None:
                item['preparation'] = 'as_served'
                notes.append('做法不明确，暂按所选食材条目的加工状态计算；未另加烹调油。')
            if (item['preparation'] in ('stir_fried','fried','braised','roasted','other')
                    and item.get('oil_g') is None):
                item['oil_g'] = 10
                notes.append('未提供摄入油量，暂额外计入这一份食用油 10g。')
        assumptions.append(notes)
    result = evaluate(assumed)
    result['draft'] = deepcopy(draft)
    if not result['questions']:
        for detail, notes in zip(result['details'], assumptions):
            detail['assumptions'] = ['基础版快速参考估算', *notes, *detail['assumptions']]
    return result
