"""실행: python -m scripts.seed_ingredient_rules (시연용 가상 규칙)."""
from sqlmodel import Session, SQLModel, select

from backend.db import engine
from backend.models import Ingredient, IngredientRule

RULE_CODE = "demo-c-d-v1"


def seed_ingredient_rules():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        ingredients = []
        for code in ("demo-c", "demo-d"):
            ingredient = session.exec(
                select(Ingredient).where(Ingredient.code == code)
            ).first()
            if ingredient is None:
                raise SystemExit(
                    "시연 성분이 없습니다. 먼저 seed_ingredients를 실행해주세요."
                )
            if not ingredient.is_sample:
                raise SystemExit("실제 성분에는 시연 규칙을 연결하지 않습니다.")
            ingredients.append(ingredient)

        a_id, b_id = sorted(i.id for i in ingredients)
        existing = session.exec(
            select(IngredientRule).where(IngredientRule.code == RULE_CODE)
        ).first()
        if existing is not None:
            if (
                existing.ingredient_a_id != a_id
                or existing.ingredient_b_id != b_id
                or not existing.is_sample
            ):
                raise SystemExit(
                    "기존 규칙과 시연 규칙 설정이 다릅니다. 자동 변경하지 않았습니다."
                )
            print("시연 규칙이 이미 있어 추가하지 않았습니다. 기존 활성화 상태도 유지합니다.")
            return

        same_pair = session.exec(
            select(IngredientRule).where(
                IngredientRule.ingredient_a_id == a_id,
                IngredientRule.ingredient_b_id == b_id,
            )
        ).first()
        if same_pair is not None:
            raise SystemExit("같은 성분 조합의 규칙이 이미 있습니다. 중복 추가하지 않았습니다.")

        session.add(
            IngredientRule(
                code=RULE_CODE,
                name="시연용 C–D 조합 규칙",
                ingredient_a_id=a_id,
                ingredient_b_id=b_id,
                condition_text=(
                    "서로 다른 두 상품에 시연 성분 C와 D가 "
                    "각각 포함된 경우를 검증하는 가상 규칙"
                ),
                message=(
                    "시연용 성분 조합 규칙에 해당해요. "
                    "실제 성분의 위험성을 의미하지 않습니다."
                ),
                source_url=None,
                is_sample=True,
                enabled=True,
            )
        )
        session.commit()
        print("시연용 C–D 조합 규칙 1개를 저장했습니다.")


if __name__ == "__main__":
    seed_ingredient_rules()
