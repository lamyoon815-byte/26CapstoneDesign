from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, SQLModel, select

from backend.db import engine
from backend.models import Product, ProductListResponse


ROOT = Path(__file__).resolve().parent.parent


def initialize_database():
    # Product 모델에 정의한 테이블을 생성합니다.
    # 이미 테이블이 있으면 그대로 사용합니다.
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # 이미 상품이 있으면 샘플을 다시 넣지 않습니다.
        existing = session.exec(select(Product).limit(1)).first()

        if existing is not None:
            return

        # 연결 확인용 가상 상품입니다.
        # 가격·색상은 실제 상품 정보가 아닙니다.
        samples = [
            Product(
                brand="시연용 브랜드",
                name="샘플 틴트",
                category="lip",
                price=9900,
                image_url="/site/img/9_product8.jpg",
                color_hex="#C96A76",
            ),
            Product(
                brand="시연용 브랜드",
                name="샘플 파운데이션",
                category="base",
                price=33500,
                image_url="/site/img/9_product7.jpg",
                color_hex="#E8C3A6",
            ),
            Product(
                brand="시연용 브랜드",
                name="샘플 아이 팔레트",
                category="eye",
                price=20900,
                image_url="/site/img/9_product10.jpg",
                color_hex=None,
            ),
        ]

        session.add_all(samples)
        session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="PERSONGAL API",
    lifespan=lifespan,
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/products", response_model=ProductListResponse)
def get_products():
    with Session(engine) as session:
        products = session.exec(
            select(Product).order_by(Product.id)
        ).all()

        return ProductListResponse(
            items=products,
            total=len(products),
        )


@app.get("/")
def home():
    return RedirectResponse("/site/persongal_home.html")


app.mount(
    "/site",
    StaticFiles(directory=str(ROOT / "site")),
    name="site",
)