"""Account-scoped, explicitly accepted approximate recipe references."""
from copy import deepcopy
import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from services.api.app.auth import get_current_user
from services.common.config import get_settings
from services.common.db import get_db
from services.common.meal_engine import catalogue
from services.common.models import User
from services.common.recipe_references import (
    reference_candidate, reference_shortlist, validate_reference_ingredients,
    validated_reference_candidates,
    validated_reference_inference,
)
from services.common.schemas import (
    AnalysisRead, AnalysisReferenceCandidates, AnalysisReferenceInference,
    AnalysisReferenceSelection, RecipeInferenceRequest, RecipeRecommendationRequest,
)


router = APIRouter()


def request_recommendations(payload, settings):
    try:
        response = httpx.post(
            settings.ai_service_url.rstrip('/') + '/recommend-recipes',
            json=payload.model_dump(), timeout=max(
                settings.worker_request_timeout_seconds, settings.llm_timeout_seconds,
                settings.qwen_timeout_seconds) + 5,
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError):
        raise RuntimeError('参考菜谱推荐暂时不可用，请稍后重试或填写实际食材。') from None


def request_reference_inference(payload, settings):
    try:
        response = httpx.post(
            settings.ai_service_url.rstrip('/') + '/infer-reference-facts',
            json=payload.model_dump(), timeout=max(
                settings.worker_request_timeout_seconds, settings.llm_timeout_seconds,
                settings.qwen_timeout_seconds) + 5,
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError):
        raise RuntimeError('菜名推测暂时不可用，请稍后重试或自行选择食材和做法。') from None


def _unknown_item(db, analysis_id, payload, user_id):
    from services.api.app.main import get_analysis
    analysis = get_analysis(db, analysis_id, user_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail='Analysis not found')
    if analysis.revision != payload.revision or analysis.status not in (
            'needs_input', 'completed', 'failed'):
        raise HTTPException(status_code=409, detail='记录已更新或已确认，请重新读取。')
    if payload.item_index >= len(analysis.draft):
        raise HTTPException(status_code=422, detail='找不到要处理的食物。')
    item = analysis.draft[payload.item_index]
    if item.get('food_id') is not None or 'custom_recipe' in item:
        raise HTTPException(status_code=422, detail='此入口只用于尚未匹配的食物。')
    return analysis, item


def _save_draft(db, analysis_id, revision, draft, user_id):
    from services.api.app.main import change_analysis, get_analysis
    # Repeat the revision/state/ownership predicate after the potentially slow model call.
    change_analysis(db, analysis_id, revision, ['needs_input', 'completed', 'failed'], {
        'draft': draft, 'status': 'needs_input', 'details': [], 'calories': None,
        'protein_g': None, 'fat_g': None, 'carbs_g': None,
        'interpreted_food_text': None, 'error_message': None,
    }, user_id=user_id)
    db.commit()
    db.expire_all()
    return AnalysisRead.model_validate(get_analysis(db, analysis_id, user_id))


@router.post('/analyses/{analysis_id}/reference-inference', response_model=AnalysisRead)
def reference_inference(
    analysis_id: str, payload: AnalysisReferenceInference,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    analysis, original = _unknown_item(db, analysis_id, payload, user.id)
    settings = get_settings()
    try:
        request = RecipeInferenceRequest(
            original_name=original.get('original_name') or original['name'])
        result = validated_reference_inference(request_reference_inference(request, settings))
        if result['provider'] != settings.effective_nutrition_provider:
            raise ValueError('Inference provider differs from configured provider')
    except (RuntimeError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=502,
                            detail='未采用菜名推测，请重试或自行选择食材和做法。') from exc
    draft = deepcopy(analysis.draft)
    item = draft[payload.item_index]
    for key in ('reference_suggestions', 'reference_selection', 'reference_template'):
        item.pop(key, None)
    item['reference_inference'] = {
        **result, 'inferred': True, 'issued_revision': payload.revision + 1,
        'catalogue_version': catalogue()['version'],
    }
    return _save_draft(db, analysis_id, payload.revision, draft, user.id)


@router.post('/analyses/{analysis_id}/reference-candidates', response_model=AnalysisRead)
def reference_candidates(
    analysis_id: str, payload: AnalysisReferenceCandidates,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    analysis, original = _unknown_item(db, analysis_id, payload, user.id)
    try:
        validate_reference_ingredients(payload.ingredient_ids)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    questions = []
    if not payload.ingredient_ids:
        questions.append({'key': 'ingredient_ids', 'label_zh': '请先选择主要食材。',
                          'label_en': 'Select the main ingredients first.'})
    if payload.preparation is None:
        questions.append({'key': 'preparation', 'label_zh': '请先说明主要做法。',
                          'label_en': 'Select the main preparation method first.'})
    settings = get_settings()
    result = {'provider': settings.effective_nutrition_provider, 'candidates': []}
    if not questions:
        facts = RecipeRecommendationRequest(
            original_name=original.get('original_name') or original['name'],
            ingredient_ids=payload.ingredient_ids, preparation=payload.preparation)
        try:
            if reference_shortlist(payload.ingredient_ids, payload.preparation):
                result = validated_reference_candidates(
                    request_recommendations(facts, settings), payload.ingredient_ids,
                    payload.preparation)
                if result['provider'] != settings.effective_nutrition_provider:
                    raise ValueError('Recommendation provider differs from configured provider')
        except (RuntimeError, ValueError, TypeError, KeyError) as exc:
            raise HTTPException(status_code=502,
                                detail='未采用推荐结果，请重试或使用实际食材配方。') from exc
    draft = deepcopy(analysis.draft)
    item = draft[payload.item_index]
    item.pop('reference_selection', None)
    item.pop('reference_template', None)
    item['reference_suggestions'] = {
        'offer_id': secrets.token_urlsafe(24), 'issued_revision': payload.revision + 1,
        'catalogue_version': catalogue()['version'],
        'status': 'needs_clarification' if questions else (
            'candidates' if result['candidates'] else 'no_match'),
        'ingredient_ids': payload.ingredient_ids, 'preparation': payload.preparation,
        'questions': questions, **result,
    }
    return _save_draft(db, analysis_id, payload.revision, draft, user.id)


@router.post('/analyses/{analysis_id}/reference-selection', response_model=AnalysisRead)
def reference_selection(
    analysis_id: str, payload: AnalysisReferenceSelection,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    analysis, original = _unknown_item(db, analysis_id, payload, user.id)
    offer = original.get('reference_suggestions') or {}
    if (offer.get('offer_id') != payload.offer_id
            or offer.get('issued_revision') != payload.revision
            or offer.get('catalogue_version') != catalogue()['version']):
        raise HTTPException(status_code=409, detail='推荐列表已过期，请重新请求。')
    candidate = next((row for row in offer.get('candidates', [])
                      if row['food_id'] == payload.food_id), None)
    if candidate is None or offer.get('status') != 'candidates':
        raise HTTPException(status_code=422, detail='只能选择本次已提供的参考菜谱。')
    allowed = {food['id']: food for food in reference_shortlist(
        offer['ingredient_ids'], offer['preparation'])}
    food = allowed.get(payload.food_id)
    if food is None:
        raise HTTPException(status_code=409, detail='参考目录已变化，请重新请求。')
    # Older offers may contain model-written explanations; refresh them from the
    # current catalogue rather than carrying unverified prose into provenance.
    candidate = reference_candidate(food, offer['ingredient_ids'], offer['provider'])
    original_name = original.get('original_name') or original['name']
    selection = {
        'original_name': original_name, 'source_food_id': food['id'],
        'source_name': food['name'], 'provider': offer['provider'],
        'catalogue_version': offer['catalogue_version'],
        'ingredient_ids': offer['ingredient_ids'], 'preparation': offer['preparation'],
        'acknowledged': True,
        'original_quantity': {key: original.get(key) for key in (
            'grams', 'weight_basis', 'weight_includes_inedible')},
        **{key: candidate[key] for key in (
            'reason_zh', 'reason_en', 'differences_zh', 'differences_en')},
    }
    draft = deepcopy(analysis.draft)
    draft[payload.item_index]['reference_selection'] = selection
    draft[payload.item_index]['reference_template'] = {
        'name': original_name, 'basis': 'batch', 'accepted': False,
        'ingredients': [{'food_id': food_id, 'grams': grams}
                        for food_id, grams in food['recipe']['ingredients'].items() if grams > 0],
        'batch_yield_g': food['recipe']['yield_g'],
        'consumed_g': (None if original.get('weight_includes_inedible')
                       or original.get('weight_basis') == 'raw' else original.get('grams')),
    }
    # Keep the unsupported food and its uncertainty until the user reviews and
    # accepts ingredient amounts through the existing structured /ingredients API.
    return _save_draft(db, analysis_id, payload.revision, draft, user.id)
