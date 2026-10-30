from itertools import combinations

from sqlmodel import Session, select

from backend.models import Ingredient, IngredientRule, Product, ProductIngredient
from backend.schemas import CartConflictItem, CartConflictMatch, CartDuplicateProduct

# 적용 조건을 구현한 시연 규칙만 사용합니다.
SUPPORTED_SAMPLE_RULE_CODES = {"demo-c-d-v1"}


def analyze_cart_conflicts(
    session: Session,
    cart_products: list[Product],
    ingredient_rows: list[tuple[ProductIngredient, Ingredient]],
) -> list[CartConflictItem]:
    products_by_id = {p.id: p for p in cart_products}
    if len(products_by_id) < 2:
        return []

    ingredient_ids_by_product = {pid: set() for pid in products_by_id}
    ingredients_by_id = {}
    for link, ingredient in ingredient_rows:
        if link.product_id not in ingredient_ids_by_product:
            continue
        ingredient_ids_by_product[link.product_id].add(ingredient.id)
        ingredients_by_id[ingredient.id] = ingredient

    rules = session.exec(
        select(IngredientRule)
        .where(
            IngredientRule.enabled == True,
            IngredientRule.is_sample == True,
            IngredientRule.code.in_(sorted(SUPPORTED_SAMPLE_RULE_CODES)),
        )
        .order_by(IngredientRule.id)
    ).all()

    results = []
    for left_id, right_id in combinations(sorted(products_by_id), 2):
        left_ingredients = ingredient_ids_by_product[left_id]
        right_ingredients = ingredient_ids_by_product[right_id]
        for rule in rules:
            a_id, b_id = rule.ingredient_a_id, rule.ingredient_b_id
            a, b = ingredients_by_id.get(a_id), ingredients_by_id.get(b_id)
            # 실제 성분이 섞인 경우 시연 규칙을 적용하지 않습니다.
            if a is None or b is None or not a.is_sample or not b.is_sample:
                continue
            directions = []
            if a_id in left_ingredients and b_id in right_ingredients:
                directions.append((a_id, b_id))
            if b_id in left_ingredients and a_id in right_ingredients:
                directions.append((b_id, a_id))
            if not directions:
                continue

            matches = [
                CartConflictMatch(
                    left_product_id=left_id,
                    left_ingredient_id=left_ingredient_id,
                    left_ingredient_name=ingredients_by_id[left_ingredient_id].name,
                    right_product_id=right_id,
                    right_ingredient_id=right_ingredient_id,
                    right_ingredient_name=ingredients_by_id[right_ingredient_id].name,
                )
                for left_ingredient_id, right_ingredient_id in directions
            ]
            results.append(
                CartConflictItem(
                    warning_id=f"cart-conflict:{left_id}:{right_id}:{rule.id}",
                    rule_id=rule.id,
                    rule_code=rule.code,
                    rule_name=rule.name,
                    condition_text=rule.condition_text,
                    source_url=rule.source_url,
                    is_sample=rule.is_sample,
                    products=[
                        CartDuplicateProduct(product_id=left_id, product_name=products_by_id[left_id].name),
                        CartDuplicateProduct(product_id=right_id, product_name=products_by_id[right_id].name),
                    ],
                    matches=matches,
                    message=rule.message,
                )
            )
    return results
