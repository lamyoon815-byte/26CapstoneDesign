"""실행: python -m scripts.seed_ingredients (가상 성분 데이터만 입력)."""
from sqlmodel import Session, SQLModel, select
from backend.db import engine
from backend.models import Ingredient, Product, ProductIngredient

SAMPLE_INGREDIENTS = {
    "demo-a": "시연 성분 A",
    "demo-b": "시연 성분 B",
    "demo-c": "시연 성분 C",
    "demo-d": "시연 성분 D",
}
PRODUCT_MAPPING = {
    "샘플 틴트": ["demo-a", "demo-b"],
    "샘플 파운데이션": ["demo-a", "demo-c"],
    "샘플 아이 팔레트": ["demo-b", "demo-d"],
}


def seed_ingredients():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        products = {}
        for name in PRODUCT_MAPPING:
            matches = session.exec(
                select(Product).where(
                    Product.brand == "시연용 브랜드", Product.name == name,
                )
            ).all()
            if len(matches) != 1:
                raise SystemExit(f"샘플 상품을 하나로 찾을 수 없습니다: {name}")
            products[name] = matches[0]

        ingredients = {}
        for code, name in SAMPLE_INGREDIENTS.items():
            ingredient = session.exec(
                select(Ingredient).where(Ingredient.code == code)
            ).first()
            if ingredient is None:
                ingredient = Ingredient(code=code, name=name, is_sample=True)
                session.add(ingredient)
                session.flush()
            elif not ingredient.is_sample:
                raise SystemExit(f"실제 성분과 코드가 충돌합니다: {code}")
            ingredients[code] = ingredient

        added_links = 0
        for product_name, codes in PRODUCT_MAPPING.items():
            product = products[product_name]
            for code in codes:
                ingredient = ingredients[code]
                existing = session.get(ProductIngredient, (product.id, ingredient.id))
                if existing is None:
                    session.add(ProductIngredient(
                        product_id=product.id, ingredient_id=ingredient.id,
                    ))
                    added_links += 1
        session.commit()
        print("시연 성분 4개와 상품별 연결을 준비했습니다.")
        print(f"새로 추가한 연결 수: {added_links}")
        for name, product in products.items():
            print(f"상품 ID {product.id}: {name}")


if __name__ == "__main__":
    seed_ingredients()
