from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session, select

from backend.db import engine
from backend.dependencies import get_current_user
from backend.models import CartItem, Product, User
from backend.schemas import CartItemRequest, CartItemResponse, CartResponse, CartWarningsResponse
from backend.services.cart_warnings import analyze_cart_warnings

router = APIRouter(prefix="/api/me/cart", tags=["장바구니"])


def build_cart_response(session: Session, user_id: int) -> CartResponse:
    rows = session.exec(
        select(CartItem, Product)
        .join(Product, CartItem.product_id == Product.id)
        .where(CartItem.user_id == user_id)
        .order_by(Product.id)
    ).all()
    items = [
        CartItemResponse(
            product_id=product.id,
            brand=product.brand,
            name=product.name,
            image_url=product.image_url,
            unit_price=product.price,
            quantity=cart_item.quantity,
            line_total=product.price * cart_item.quantity,
        )
        for cart_item, product in rows
    ]
    return CartResponse(
        items=items,
        item_count=len(items),
        total_quantity=sum(item.quantity for item in items),
        subtotal=sum(item.line_total for item in items),
    )


@router.get("", response_model=CartResponse)
def get_cart(user: User = Depends(get_current_user)):
    with Session(engine) as session:
        return build_cart_response(session, user.id)


@router.put("/items/{product_id}", response_model=CartResponse)
def set_cart_item(
    product_id: int,
    payload: CartItemRequest,
    user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        product = session.get(Product, product_id)
        if product is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "PRODUCT_NOT_FOUND",
                    "message": "상품을 찾을 수 없어요.",
                },
            )
        # 수량은 추가분이 아니라 최종 수량입니다.
        statement = (
            insert(CartItem)
            .values(user_id=user.id, product_id=product_id, quantity=payload.quantity)
            .on_conflict_do_update(
                index_elements=["user_id", "product_id"],
                set_={"quantity": payload.quantity},
            )
        )
        session.execute(statement)
        session.commit()
        return build_cart_response(session, user.id)


@router.delete("/items/{product_id}", response_model=CartResponse)
def delete_cart_item(
    product_id: int,
    user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        item = session.get(CartItem, (user.id, product_id))
        if item is not None:
            session.delete(item)
            session.commit()
        return build_cart_response(session, user.id)



@router.get("/warnings", response_model=CartWarningsResponse)
def get_cart_warnings(user: User = Depends(get_current_user)):
    with Session(engine) as session:
        return analyze_cart_warnings(session, user.id)
