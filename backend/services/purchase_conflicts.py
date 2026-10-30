from calendar import monthrange
from datetime import date, datetime, timedelta, timezone

from sqlmodel import Session, select

from backend.models import Ingredient, Product, ProductIngredient, Purchase
from backend.schemas import (
    PurchaseConflictAnalysis,
    PurchaseConflictEvidence,
    PurchaseConflictItem,
)
from backend.services.cart_conflicts import analyze_cart_conflicts

KST = timezone(timedelta(hours=9))


def korean_today() -> date:
    return datetime.now(KST).date()


def six_months_before(day: date) -> date:
    month_index = day.year * 12 + day.month - 1 - 6
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def analyze_purchase_conflicts(
    session: Session,
    user_id: int,
    cart_products: list[Product],
    *,
    today: date | None = None,
) -> PurchaseConflictAnalysis:
    # today는 날짜 경계 검증용이며 API 입력으로 받지 않습니다.
    window_end = today if today is not None else korean_today()
    window_start = six_months_before(window_end)
    recent_rows = session.exec(
        select(Purchase, Product)
        .join(Product, Purchase.product_id == Product.id)
        .where(
            Purchase.user_id == user_id,
            Purchase.purchased_at >= window_start,
            Purchase.purchased_at <= window_end,
        )
        .order_by(Purchase.purchased_at.desc(), Purchase.id.desc())
    ).all()

    cart_by_id = {p.id: p for p in cart_products}
    purchased_by_id = {}
    evidence_by_product = {}
    for purchase, product in recent_rows:
        purchased_by_id[product.id] = product
        evidence_by_product.setdefault(product.id, []).append(
            PurchaseConflictEvidence(
                purchase_id=purchase.id,
                purchased_at=purchase.purchased_at,
            )
        )

    all_products = {**purchased_by_id, **cart_by_id}
    ingredient_rows = []
    if all_products:
        ingredient_rows = session.exec(
            select(ProductIngredient, Ingredient)
            .join(Ingredient, ProductIngredient.ingredient_id == Ingredient.id)
            .where(ProductIngredient.product_id.in_(list(all_products)))
            .order_by(ProductIngredient.product_id, Ingredient.id)
        ).all()
    covered_product_ids = {link.product_id for link, ingredient in ingredient_rows}

    # 기존 시연 규칙 조건과 양방향 검사를 재사용합니다.
    pair_matches = analyze_cart_conflicts(
        session, list(all_products.values()), ingredient_rows,
    )
    results = []
    for match in pair_matches:
        left_id, right_id = [p.product_id for p in match.products]
        roles = []
        if left_id in cart_by_id and right_id in purchased_by_id:
            roles.append((left_id, right_id))
        if right_id in cart_by_id and left_id in purchased_by_id:
            roles.append((right_id, left_id))
        for cart_id, purchased_id in roles:
            results.append(
                PurchaseConflictItem(
                    **match.model_dump(exclude={"type", "warning_id"}),
                    warning_id=f"purchase-conflict:{cart_id}:{purchased_id}:{match.rule_id}",
                    cart_product_id=cart_id,
                    purchased_product_id=purchased_id,
                    purchases=evidence_by_product[purchased_id],
                )
            )
    results.sort(key=lambda i: (i.cart_product_id, i.purchased_product_id, i.rule_id))
    return PurchaseConflictAnalysis(
        items=results,
        window_start=window_start,
        window_end=window_end,
        missing_ingredient_product_ids=sorted(
            set(purchased_by_id) - covered_product_ids
        ),
    )
