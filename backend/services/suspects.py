from sqlmodel import Session, select

from backend.models import Ingredient, Product, ProductIngredient, Purchase
from backend.schemas import SuspectEvidence, SuspectItem, SuspectListResponse


def analyze_suspects(session: Session, user_id: int) -> SuspectListResponse:
    # 전체 구매 이력에서 가장 최근에 작성/수정한 유효 리뷰를 선택합니다.
    reviewed_rows = session.exec(
        select(Purchase, Product)
        .join(Product, Purchase.product_id == Product.id)
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

    latest_by_product = {}
    for purchase, product in reviewed_rows:
        if product.id not in latest_by_product:
            latest_by_product[product.id] = (purchase, product)

    stats = {}
    missing_ids = []
    if latest_by_product:
        ingredient_rows = session.exec(
            select(ProductIngredient, Ingredient)
            .join(Ingredient, ProductIngredient.ingredient_id == Ingredient.id)
            .where(ProductIngredient.product_id.in_(list(latest_by_product)))
        ).all()
        covered_product_ids = set()
        for link, ingredient in ingredient_rows:
            covered_product_ids.add(link.product_id)
            purchase, product = latest_by_product[link.product_id]
            if ingredient.id not in stats:
                stats[ingredient.id] = {
                    "ingredient": ingredient, "bad": 0, "good": 0, "products": [],
                }
            entry = stats[ingredient.id]
            entry[purchase.review_status] += 1
            entry["products"].append(
                SuspectEvidence(
                    purchase_id=purchase.id,
                    product_id=product.id,
                    product_name=product.name,
                    image_url=product.image_url,
                    review_status=purchase.review_status,
                )
            )
        missing_ids = sorted(set(latest_by_product) - covered_product_ids)

    items = []
    for entry in stats.values():
        bad, good = entry["bad"], entry["good"]
        if bad == 0:
            continue
        raw_score = bad / (bad + good)
        is_candidate = bad >= 2 and raw_score >= 0.5
        ingredient = entry["ingredient"]
        if is_candidate:
            reason = (
                f"안 맞았던 서로 다른 상품 {bad}개에 포함됐고, "
                "규칙 점수가 0.5 이상이에요."
            )
        elif bad < 2:
            reason = f"안 맞았던 상품이 {bad}개여서 후보 기준인 2개에 미달해요."
        else:
            reason = "규칙 점수가 후보 기준인 0.5보다 낮아요."
        items.append(
            SuspectItem(
                ingredient_id=ingredient.id,
                ingredient_name=ingredient.name,
                is_sample=ingredient.is_sample,
                state="candidate" if is_candidate else "pending",
                bad_count=bad, good_count=good,
                score=round(raw_score, 4),
                reason=reason,
                products=sorted(entry["products"], key=lambda p: p.product_id),
            )
        )

    items.sort(key=lambda i: (i.state != "candidate", -i.score, -i.bad_count, i.ingredient_id))
    return SuspectListResponse(
        items=items,
        total=len(items),
        evaluated_product_count=len(latest_by_product),
        missing_ingredient_product_ids=missing_ids,
        rule_version="suspects-v1",
        notice=(
            "리뷰와 등록된 성분 정보로 추정한 결과이며 의학적 진단이 아닙니다. "
            "점수는 트러블 발생 확률이 아닙니다."
        ),
    )
