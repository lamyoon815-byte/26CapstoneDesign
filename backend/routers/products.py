from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from backend.db import engine
from backend.dependencies import get_current_user
from backend.models import (
    Ingredient, Product, ProductIngredient, User, UserIngredientPreference,
)
from backend.schemas import (
    PersonalIngredientAnalysis, ProductAnalysisResponse, ProductAlternativesResponse,
    ProductDetailResponse, ProductIngredientInfo,
)
from backend.services.recommendations import get_recommendations
from backend.services.suspects import analyze_suspects

router = APIRouter(tags=["상품 상세"])


def get_product_or_404(session: Session, product_id: int) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail={
            "code": "PRODUCT_NOT_FOUND",
            "message": "상품을 찾을 수 없어요.",
        })
    return product


def load_product_ingredients(session: Session, product_id: int) -> list[Ingredient]:
    return list(session.exec(
        select(Ingredient)
        .join(ProductIngredient, ProductIngredient.ingredient_id == Ingredient.id)
        .where(ProductIngredient.product_id == product_id)
        .order_by(Ingredient.id)
    ).all())


@router.get("/api/products/{product_id}", response_model=ProductDetailResponse)
def product_detail(product_id: int):
    with Session(engine) as session:
        product = get_product_or_404(session, product_id)
        ingredients = load_product_ingredients(session, product_id)
        return ProductDetailResponse(
            product_id=product.id,
            brand=product.brand,
            name=product.name,
            category=product.category,
            price=product.price,
            image_url=product.image_url,
            color_hex=product.color_hex,
            ingredients=[ProductIngredientInfo(
                ingredient_id=i.id, ingredient_name=i.name, is_sample=i.is_sample,
            ) for i in ingredients],
            has_ingredient_data=bool(ingredients),
        )


@router.get(
    "/api/me/products/{product_id}/analysis",
    response_model=ProductAnalysisResponse,
)
def product_analysis(product_id: int, user: User = Depends(get_current_user)):
    with Session(engine) as session:
        get_product_or_404(session, product_id)
        ingredients = load_product_ingredients(session, product_id)
        recommendations = get_recommendations(
            session, user.id, category=None, page=1, page_size=1,
            product_id=product_id,
        )
        classified = (
            recommendations.items + recommendations.excluded_items
            + recommendations.unassessed_items
        )
        if len(classified) != 1:
            raise HTTPException(status_code=500, detail={
                "code": "PRODUCT_ANALYSIS_FAILED",
                "message": "상품 분석 결과를 만들지 못했어요.",
            })
        preferences = session.exec(
            select(UserIngredientPreference).where(
                UserIngredientPreference.user_id == user.id
            )
        ).all()
        preference_map = {p.ingredient_id: p.preference for p in preferences}
        suspects = analyze_suspects(session, user.id)
        suspect_map = {i.ingredient_id: i for i in suspects.items}
        ingredient_analysis = []
        for ingredient in ingredients:
            evidence = suspect_map.get(ingredient.id)
            ingredient_analysis.append(PersonalIngredientAnalysis(
                ingredient_id=ingredient.id,
                ingredient_name=ingredient.name,
                is_sample=ingredient.is_sample,
                manual_preference=preference_map.get(ingredient.id),
                review_state=evidence.state if evidence else None,
                review_evidence=evidence,
            ))
        return ProductAnalysisResponse(
            assessment=classified[0],
            ingredient_analysis=ingredient_analysis,
            rule_version=recommendations.rule_version,
            notice=recommendations.notice + " 성분별 표시가 없다는 것이 안전성을 뜻하지는 않습니다.",
        )


@router.get(
    "/api/me/products/{product_id}/alternatives",
    response_model=ProductAlternativesResponse,
)
def product_alternatives(
    product_id: int,
    limit: int = Query(default=3, ge=1, le=12),
    user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        product = get_product_or_404(session, product_id)
        result = get_recommendations(
            session=session,
            user_id=user.id,
            category=product.category,
            page=1,
            page_size=limit,
            exclude_product_id=product.id,
        )
        return ProductAlternativesResponse(
            source_product_id=product.id,
            category=product.category,
            items=result.items,
            total=result.total,
            limit=limit,
            rule_version=result.rule_version,
            notice=(
                result.notice
                + " 같은 카테고리에서 기준 상품을 제외한 후보입니다."
                + " 기준 상품보다 안전하거나 더 잘 맞는다는 의미는 아닙니다."
            ),
        )
