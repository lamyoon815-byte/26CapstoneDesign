from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from backend.db import engine
from backend.dependencies import get_current_user
from backend.models import Ingredient, Product, ProductIngredient, User
from backend.schemas import SuspectListResponse
from backend.services.suspects import analyze_suspects

router = APIRouter(tags=["성분 분석"])


@router.get("/api/products/{product_id}/ingredients")
def get_product_ingredients(product_id: int):
    with Session(engine) as session:
        product = session.get(Product, product_id)
        if product is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "PRODUCT_NOT_FOUND", "message": "상품을 찾을 수 없어요."},
            )
        ingredients = session.exec(
            select(Ingredient)
            .join(ProductIngredient, Ingredient.id == ProductIngredient.ingredient_id)
            .where(ProductIngredient.product_id == product_id)
            .order_by(Ingredient.id)
        ).all()
        return {
            "product_id": product.id,
            "product_name": product.name,
            "items": [
                {"id": i.id, "name": i.name, "is_sample": i.is_sample}
                for i in ingredients
            ],
            "total": len(ingredients),
            "has_ingredient_data": bool(ingredients),
        }


@router.get("/api/me/suspects", response_model=SuspectListResponse)
def get_my_suspects(user: User = Depends(get_current_user)):
    with Session(engine) as session:
        return analyze_suspects(session, user.id)



@router.get("/api/ingredients")
def search_ingredients(q: str = Query(default="", max_length=100)):
    keyword = q.strip()
    with Session(engine) as session:
        statement = select(Ingredient)
        if keyword:
            statement = statement.where(
                Ingredient.name.contains(keyword, autoescape=True)
            )
        rows = session.exec(statement.order_by(Ingredient.id).limit(50)).all()
        return {
            "items": [
                {"id": i.id, "name": i.name, "is_sample": i.is_sample}
                for i in rows
            ],
            "count": len(rows),
        }
