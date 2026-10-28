"""프로젝트 루트에서 python -m scripts.seed_purchases --email EMAIL 실행."""
import argparse
from datetime import date, timedelta

from sqlmodel import Session, SQLModel, select

from backend.db import engine
from backend.models import Product, Purchase, User


def seed_purchases(email: str):
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.email == email.strip().lower())
        ).first()
        if user is None:
            raise SystemExit("해당 계정이 없습니다. 먼저 회원가입해주세요.")

        existing = session.exec(
            select(Purchase).where(Purchase.user_id == user.id).limit(1)
        ).first()
        if existing is not None:
            print("이 계정에는 이미 구매내역이 있어 샘플을 추가하지 않았습니다.")
            return

        products = session.exec(
            select(Product).order_by(Product.id).limit(3)
        ).all()
        if len(products) < 3:
            raise SystemExit("상품이 3개 이상 필요합니다. 상품 초기 데이터를 확인해주세요.")

        today = date.today()
        for product, days in zip(products, [10, 40, 200]):
            session.add(
                Purchase(
                    user_id=user.id,
                    product_id=product.id,
                    purchased_at=today - timedelta(days=days),
                    paid_price=product.price,
                    review_status=None,
                    reviewed_at=None,
                    is_sample=True,
                )
            )
        session.commit()
        print("지정한 계정에 샘플 구매내역 3개를 저장했습니다.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="이미 가입한 사용자의 이메일")
    args = parser.parse_args()
    seed_purchases(args.email)
