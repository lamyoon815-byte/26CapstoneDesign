from itertools import combinations

from backend.models import Ingredient, Product, ProductIngredient
from backend.schemas import (
    CartDuplicateIngredient,
    CartDuplicateItem,
    CartDuplicateProduct,
)


def analyze_cart_duplicates(
    cart_products: list[Product],
    ingredient_rows: list[tuple[ProductIngredient, Ingredient]],
) -> list[CartDuplicateItem]:
    products_by_id = {p.id: p for p in cart_products}
    ingredient_ids_by_product = {pid: set() for pid in products_by_id}
    ingredients_by_id = {}

    for link, ingredient in ingredient_rows:
        if link.product_id not in ingredient_ids_by_product:
            continue
        ingredient_ids_by_product[link.product_id].add(ingredient.id)
        ingredients_by_id[ingredient.id] = ingredient

    results = []
    # 서로 다른 두 상품을 한 번씩만 비교합니다. 수량은 비교에 사용하지 않습니다.
    for left_id, right_id in combinations(sorted(products_by_id), 2):
        common_ids = (
            ingredient_ids_by_product[left_id]
            & ingredient_ids_by_product[right_id]
        )
        if not common_ids:
            continue
        left, right = products_by_id[left_id], products_by_id[right_id]
        shared_ingredients = [
            CartDuplicateIngredient(
                ingredient_id=ingredient_id,
                ingredient_name=ingredients_by_id[ingredient_id].name,
                is_sample=ingredients_by_id[ingredient_id].is_sample,
            )
            for ingredient_id in sorted(common_ids)
        ]
        results.append(
            CartDuplicateItem(
                warning_id=f"duplicate:{left_id}:{right_id}",
                products=[
                    CartDuplicateProduct(product_id=left.id, product_name=left.name),
                    CartDuplicateProduct(product_id=right.id, product_name=right.name),
                ],
                ingredients=shared_ingredients,
                message=(
                    f"두 상품에 같은 성분 {len(shared_ingredients)}개가 들어 있어요. "
                    "성분 중복만으로 위험성이나 사용량을 판단할 수는 없어요."
                ),
            )
        )
    return results
