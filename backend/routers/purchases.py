from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.db import engine
from backend.dependencies import get_current_user
from backend.models import Product, Purchase, User
from backend.schemas import (
    PurchaseListResponse,
    PurchaseResponse,
    ReviewRequest,
    ReviewResponse,
)

router = APIRouter(prefix="/api/me/purchases", tags=["구매내역·리뷰"])


@router.get("", response_model=PurchaseListResponse)
def get_my_purchases(user: User = Depends(get_current_user)):
    with Session(engine) as session:
        statement = (
            select(Purchase, Product)
            .join(Product, Purchase.product_id == Product.id)
            .where(Purchase.user_id == user.id)
            .order_by(Purchase.purchased_at.desc(), Purchase.id.desc())
        )
        rows = session.exec(statement).all()
        items = [
            PurchaseResponse(
                id=purchase.id,
                product_id=product.id,
                brand=product.brand,
                name=product.name,
                image_url=product.image_url,
                purchased_at=purchase.purchased_at,
                paid_price=purchase.paid_price,
                review_status=purchase.review_status,
                reviewed_at=purchase.reviewed_at,
                is_sample=purchase.is_sample,
            )
            for purchase, product in rows
        ]
        return PurchaseListResponse(items=items, total=len(items))


@router.put("/{purchase_id}/review", response_model=ReviewResponse)
def save_review(
    purchase_id: int,
    payload: ReviewRequest,
    user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        purchase = session.exec(
            select(Purchase).where(
                Purchase.id == purchase_id,
                Purchase.user_id == user.id,
            )
        ).first()
        if purchase is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "PURCHASE_NOT_FOUND",
                    "message": "구매내역을 찾을 수 없어요.",
                },
            )

        # 동일 요청 재전송 시 수정 시각을 유지합니다.
        if purchase.review_status != payload.review_status:
            purchase.review_status = payload.review_status
            purchase.reviewed_at = (
                datetime.now(timezone.utc)
                if payload.review_status is not None
                else None
            )
            session.add(purchase)
            session.commit()
            session.refresh(purchase)

        return ReviewResponse(
            purchase_id=purchase.id,
            review_status=purchase.review_status,
            reviewed_at=purchase.reviewed_at,
        )
