from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session, select

from backend.db import engine
from backend.dependencies import get_current_user
from backend.models import Ingredient, User, UserIngredientPreference
from backend.schemas import (
    IngredientPreferenceRequest,
    IngredientPreferenceResponse,
    ProfileResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/me", tags=["프로필·직접 지정 성분"])


def preference_response(
    ingredient: Ingredient, preference: str,
) -> IngredientPreferenceResponse:
    return IngredientPreferenceResponse(
        ingredient_id=ingredient.id,
        ingredient_name=ingredient.name,
        preference=preference,
        source="manual",
        is_sample=ingredient.is_sample,
    )


@router.get("/profile", response_model=ProfileResponse)
def get_profile(user: User = Depends(get_current_user)):
    with Session(engine) as session:
        rows = session.exec(
            select(UserIngredientPreference, Ingredient)
            .join(
                Ingredient,
                UserIngredientPreference.ingredient_id == Ingredient.id,
            )
            .where(UserIngredientPreference.user_id == user.id)
            .order_by(Ingredient.id)
        ).all()
        avoid, preferred = [], []
        for preference, ingredient in rows:
            item = preference_response(ingredient, preference.preference)
            if preference.preference == "avoid":
                avoid.append(item)
            else:
                preferred.append(item)
        return ProfileResponse(
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                marketing_consent=user.marketing_consent,
            ),
            avoid_ingredients=avoid,
            preferred_ingredients=preferred,
        )


@router.put("/ingredients/{ingredient_id}", response_model=IngredientPreferenceResponse)
def set_ingredient_preference(
    ingredient_id: int,
    payload: IngredientPreferenceRequest,
    user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        ingredient = session.get(Ingredient, ingredient_id)
        if ingredient is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "INGREDIENT_NOT_FOUND",
                    "message": "성분을 찾을 수 없어요.",
                },
            )
        # 반복·동시 요청에서도 사용자/성분당 한 행만 생성합니다.
        statement = insert(UserIngredientPreference).values(
            user_id=user.id,
            ingredient_id=ingredient_id,
            preference=payload.preference,
        ).on_conflict_do_update(
            index_elements=["user_id", "ingredient_id"],
            set_={"preference": payload.preference},
        )
        session.execute(statement)
        session.commit()
        return preference_response(ingredient, payload.preference)


@router.delete("/ingredients/{ingredient_id}")
def delete_ingredient_preference(
    ingredient_id: int,
    user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        preference = session.get(UserIngredientPreference, (user.id, ingredient_id))
        if preference is not None:
            session.delete(preference)
            session.commit()
        return {
            "ingredient_id": ingredient_id,
            "message": "직접 지정을 해제했어요.",
        }
