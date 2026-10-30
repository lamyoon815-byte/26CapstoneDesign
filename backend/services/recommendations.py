from sqlmodel import Session, select

from backend.models import (
    Ingredient, Product, ProductIngredient, Purchase, UserIngredientPreference,
)
from backend.schemas import RecommendationItem, RecommendationResponse
from backend.services.suspects import analyze_suspects


def get_recommendations(
    session: Session,
    user_id: int,
    category: str | None,
    page: int,
    page_size: int,
    product_id: int | None = None,
    exclude_product_id: int | None = None,
) -> RecommendationResponse:
    statement = select(Product)
    if category:
        statement = statement.where(Product.category == category)
    if product_id is not None:
        statement = statement.where(Product.id == product_id)
    if exclude_product_id is not None:
        statement = statement.where(Product.id != exclude_product_id)
    products = session.exec(statement.order_by(Product.id)).all()

    preferences = session.exec(
        select(UserIngredientPreference).where(
            UserIngredientPreference.user_id == user_id
        )
    ).all()
    avoid_ids = {p.ingredient_id for p in preferences if p.preference == "avoid"}
    preferred_ids = {p.ingredient_id for p in preferences if p.preference == "prefer"}

    # 의심 성분 계산과 동일하게 최신 유효 리뷰를 상품별 한 번만 사용합니다.
    reviews = session.exec(
        select(Purchase)
        .where(
            Purchase.user_id == user_id,
            Purchase.review_status.in_(["good", "bad"]),
        )
        .order_by(
            Purchase.reviewed_at.desc(),
            Purchase.purchased_at.desc(),
            Purchase.id.desc(),
        )
    ).all()
    latest_status = {}
    for purchase in reviews:
        if purchase.product_id not in latest_status:
            latest_status[purchase.product_id] = purchase.review_status

    analysis = analyze_suspects(session, user_id)
    suspect_ids = {
        item.ingredient_id for item in analysis.items if item.state == "candidate"
    }
    ingredients_by_product = {p.id: {} for p in products}
    if products:
        rows = session.exec(
            select(ProductIngredient, Ingredient)
            .join(Ingredient, ProductIngredient.ingredient_id == Ingredient.id)
            .where(ProductIngredient.product_id.in_(list(ingredients_by_product)))
        ).all()
        for link, ingredient in rows:
            ingredients_by_product[link.product_id][ingredient.id] = ingredient

    eligible, excluded, unassessed = [], [], []
    for product in products:
        ingredients = ingredients_by_product[product.id]
        ingredient_ids = set(ingredients)
        matched_avoid = sorted(ingredient_ids & avoid_ids)
        matched_preferred = sorted(ingredient_ids & preferred_ids)
        matched_suspects = sorted(ingredient_ids & suspect_ids)
        review_status = latest_status.get(product.id)
        reasons, cautions = [], []

        if matched_avoid:
            names = ", ".join(ingredients[i].name for i in matched_avoid)
            reasons.append(f"직접 피하도록 지정한 성분이 있어 제외했어요: {names}")
        if review_status == "bad":
            reasons.append("이 상품의 최신 유효 리뷰가 '안 맞았어요'여서 제외했어요.")

        if matched_avoid or review_status == "bad":
            status = "excluded"
        elif not ingredient_ids:
            status = "unassessed"
            reasons.append("등록된 성분 정보가 없어 비교를 보류했어요.")
        else:
            status = "eligible"
            if matched_preferred:
                names = ", ".join(ingredients[i].name for i in matched_preferred)
                reasons.append(f"직접 선호하도록 지정한 성분이 들어 있어요: {names}")
            if review_status == "good":
                reasons.append("이 상품의 최신 유효 리뷰가 '잘 맞았어요'예요.")
            if avoid_ids:
                reasons.append(
                    "등록된 성분 중 직접 피하도록 지정한 성분과 일치하는 항목이 없어요."
                )
            if not reasons:
                reasons.append(
                    "현재 제외 규칙에 해당하지 않아 후보로 표시해요. 개인 맞춤 근거는 부족해요."
                )

        if matched_suspects:
            names = ", ".join(ingredients[i].name for i in matched_suspects)
            cautions.append(f"리뷰 기반 의심 성분 후보가 들어 있어요: {names}")
        item = RecommendationItem(
            product_id=product.id,
            brand=product.brand,
            name=product.name,
            category=product.category,
            price=product.price,
            image_url=product.image_url,
            status=status,
            reasons=reasons,
            cautions=cautions,
            avoid_ingredient_ids=matched_avoid,
            preferred_ingredient_ids=matched_preferred,
            suspect_ingredient_ids=matched_suspects,
            latest_review_status=review_status,
            has_ingredient_data=bool(ingredient_ids),
            has_sample_ingredients=any(i.is_sample for i in ingredients.values()),
        )
        if status == "excluded":
            excluded.append(item)
        elif status == "unassessed":
            unassessed.append(item)
        else:
            eligible.append(item)

    eligible.sort(key=lambda i: (
        bool(i.suspect_ingredient_ids),
        -len(i.preferred_ingredient_ids),
        i.product_id,
    ))
    start = (page - 1) * page_size
    return RecommendationResponse(
        items=eligible[start:start + page_size],
        total=len(eligible),
        page=page,
        page_size=page_size,
        excluded_items=excluded,
        excluded_total=len(excluded),
        unassessed_items=unassessed,
        unassessed_total=len(unassessed),
        rule_version="ingredient-recommendation-v1",
        notice=(
            "직접 지정 성분과 리뷰를 이용한 후보 목록입니다. 피부 적합성이나 안전성을 "
            "보장하지 않습니다. 퍼스널컬러와 최근 구매 조합은 아직 반영하지 않습니다."
        ),
    )
