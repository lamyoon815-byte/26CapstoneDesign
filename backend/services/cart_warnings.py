from sqlmodel import Session, select

from backend.models import (
    CartItem,
    Ingredient,
    Product,
    ProductIngredient,
    UserIngredientPreference,
)
from backend.schemas import CartWarningItem, CartWarningsResponse
from backend.services.suspects import analyze_suspects
from backend.services.cart_duplicates import analyze_cart_duplicates
from backend.services.cart_conflicts import analyze_cart_conflicts


def analyze_cart_warnings(session: Session, user_id: int) -> CartWarningsResponse:
    cart_products = session.exec(
        select(Product)
        .join(CartItem, CartItem.product_id == Product.id)
        .where(CartItem.user_id == user_id)
        .order_by(Product.id)
    ).all()
    products_by_id = {product.id: product for product in cart_products}

    avoid_ids = set(
        session.exec(
            select(UserIngredientPreference.ingredient_id)
            .where(
                UserIngredientPreference.user_id == user_id,
                UserIngredientPreference.preference == "avoid",
            )
        ).all()
    )
    analysis = analyze_suspects(session, user_id)
    candidates = {
        item.ingredient_id: item
        for item in analysis.items
        if item.state == "candidate"
    }

    ingredient_rows = []
    if products_by_id:
        ingredient_rows = session.exec(
            select(ProductIngredient, Ingredient)
            .join(Ingredient, ProductIngredient.ingredient_id == Ingredient.id)
            .where(ProductIngredient.product_id.in_(list(products_by_id)))
            .order_by(ProductIngredient.product_id, Ingredient.id)
        ).all()

    covered_product_ids = set()
    warnings = []
    for link, ingredient in ingredient_rows:
        covered_product_ids.add(link.product_id)
        is_avoid = ingredient.id in avoid_ids
        suspect = candidates.get(ingredient.id)
        if not is_avoid and suspect is None:
            continue

        sources, messages = [], []
        if is_avoid:
            sources.append("personal_avoid")
            messages.append("직접 피하도록 지정한 성분이 들어 있어요.")
        if suspect is not None:
            sources.append("personal_suspect")
            messages.append("내 리뷰에서 의심 성분 후보로 분류된 성분이 들어 있어요.")

        product = products_by_id[link.product_id]
        warnings.append(
            CartWarningItem(
                warning_id=f"personal:{product.id}:{ingredient.id}",
                type="personal_avoid" if is_avoid else "personal_suspect",
                sources=sources,
                product_id=product.id,
                product_name=product.name,
                ingredient_id=ingredient.id,
                ingredient_name=ingredient.name,
                is_sample=ingredient.is_sample,
                message=" ".join(messages),
                suspect_evidence=suspect,
            )
        )

    duplicate_items = analyze_cart_duplicates(cart_products, ingredient_rows)
    duplicate_product_ids = {
        product.product_id
        for item in duplicate_items
        for product in item.products
    }

    cart_conflict_items = analyze_cart_conflicts(session, cart_products, ingredient_rows)
    cart_conflict_product_ids = {
        product.product_id
        for item in cart_conflict_items
        for product in item.products
    }

    return CartWarningsResponse(
        items=warnings,
        total=len(warnings),
        affected_product_count=len({w.product_id for w in warnings}),
        duplicate_items=duplicate_items,
        duplicate_total=len(duplicate_items),
        duplicate_affected_product_count=len(duplicate_product_ids),
        cart_conflict_items=cart_conflict_items,
        cart_conflict_total=len(cart_conflict_items),
        cart_conflict_affected_product_count=len(cart_conflict_product_ids),
        missing_cart_ingredient_product_ids=sorted(
            set(products_by_id) - covered_product_ids
        ),
        missing_review_ingredient_product_ids=analysis.missing_ingredient_product_ids,
        rule_version="cart-personal-duplicate-demo-conflict-v3",
        notice=(
            "개인 성분 정보·상품 간 중복·시연용 조합 규칙을 비교한 결과입니다. "
            "의학적 진단이 아닙니다. 성분 중복이나 가상 시연 규칙은 실제 위험성을 "
            "뜻하지 않으며, 안내가 없다는 것이 안전성을 보장하지는 않습니다."
        ),
    )
