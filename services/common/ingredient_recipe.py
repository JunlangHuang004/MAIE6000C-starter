"""Explicit user ingredient recipes; never model-generated food substitutions."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PositiveGrams = Annotated[float, Field(strict=True, gt=0, le=10000)]


class RecipeIngredient(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

    food_id: str = Field(strict=True, min_length=1, max_length=100)
    grams: PositiveGrams


class IngredientRecipe(BaseModel):
    """Amounts describe either consumed ingredients or an explicitly portioned batch."""
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

    name: str = Field(strict=True, min_length=1, max_length=120)
    basis: Literal['consumed', 'batch']
    ingredients: list[RecipeIngredient] = Field(min_length=1, max_length=30)
    batch_yield_g: PositiveGrams | None = None
    consumed_g: PositiveGrams | None = None
    accepted: bool = Field(strict=True)

    @field_validator('name', mode='before')
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode='after')
    def validate_recipe(self):
        if not self.accepted:
            raise ValueError('请先核对食材、重量状态及用量，并确认配方。')
        ids = [ingredient.food_id for ingredient in self.ingredients]
        if len(set(ids)) != len(ids):
            raise ValueError('同一食材只能添加一次，请合并其克数。')
        if self.basis == 'batch':
            if self.batch_yield_g is None or self.consumed_g is None:
                raise ValueError('整锅配方需要成品总重和本次食用重量。')
            if self.consumed_g > self.batch_yield_g:
                raise ValueError('本次食用重量不能超过整锅成品总重。')
        elif self.batch_yield_g is not None or self.consumed_g is not None:
            raise ValueError('本次食材用量模式不接受整锅重量；请选择整锅配方模式。')
        return self


def validate_ingredient_recipe(value, foods):
    """Recheck stored/internal input as well as the public API request."""
    recipe = IngredientRecipe.model_validate(value)
    if any(foods.get(row.food_id, {}).get('kind') != 'ingredient'
           for row in recipe.ingredients):
        raise ValueError('请选择目录中已有的食材记录；不能使用未知食物或整道参考菜谱。')
    return recipe


def recipe_detail(value, foods, nutrient_keys):
    """Return full-precision totals plus readable, source-backed calculation evidence."""
    recipe = validate_ingredient_recipe(value, foods)
    factor = recipe.consumed_g / recipe.batch_yield_g if recipe.basis == 'batch' else 1.0
    totals = dict.fromkeys(nutrient_keys, 0.0)
    ingredients = []
    sources = []
    for row in recipe.ingredients:
        food = foods[row.food_id]
        for key in nutrient_keys:
            totals[key] += food['nutrients'][key] * row.grams / 100 * factor
        ingredients.append({
            'food_id': row.food_id, 'name': food['name'], 'grams': row.grams,
            'state': food['state'], 'consumed_grams': row.grams * factor,
        })
        sources.append(food['source'])
    grams = (recipe.consumed_g if recipe.basis == 'batch'
             else sum(row.grams for row in recipe.ingredients))
    detail = {
        'kind': 'custom_recipe', 'food_id': None, 'name': recipe.name, 'grams': grams,
        'nutrients': {key: round(value, 1) for key, value in totals.items()},
        'assumptions': [
            '用户填写并确认的食材配方；不是数据库中的实测菜肴记录。',
            '食材按所选记录的生重、熟重或可食净重计算，不自动互换。',
            '油、糖及酱料需逐项列入；不自动估计未填写的配料或烹调损耗。',
        ],
        'sources': sources,
        'quantity_provenance': {
            'kind': 'custom_recipe', 'basis': recipe.basis,
            'ingredients': ingredients, 'batch_yield_g': recipe.batch_yield_g,
            'consumed_g': recipe.consumed_g, 'factor': factor,
        },
    }
    return totals, detail
