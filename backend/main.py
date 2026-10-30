import os

from dotenv import load_dotenv
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, SQLModel, select

from backend.db import engine
from backend.models import Product, ProductListResponse

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.routers.auth import router as auth_router
from backend.routers.purchases import router as purchases_router
from backend.routers.ingredients import router as ingredients_router
from backend.routers.profile import router as profile_router
from backend.routers.cart import router as cart_router
from backend.routers.recommendations import router as recommendations_router
from backend.routers.products import router as products_router

ROOT = Path(__file__).resolve().parent.parent

load_dotenv(ROOT / ".env")
SESSION_SECRET = os.getenv("SESSION_SECRET")
if not SESSION_SECRET or len(SESSION_SECRET) < 32:
    raise RuntimeError(".env에 충분히 긴 SESSION_SECRET을 설정해주세요.")


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

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="persongal_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=False,  # 로컬 HTTP용. HTTPS 배포 시 True로 변경.
)

app.include_router(auth_router)
app.include_router(purchases_router)
app.include_router(ingredients_router)
app.include_router(profile_router)
app.include_router(cart_router)
app.include_router(recommendations_router)
app.include_router(products_router)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request, exc):
    content = (
        exc.detail if isinstance(exc.detail, dict)
        else {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail)}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=exc.headers,
    )


ALLOWED_ORIGINS = {
    "http://127.0.0.1:8000",
    "http://localhost:8000",
}


@app.middleware("http")
async def check_request_origin(request, call_next):
    is_api_change = (
        request.url.path.startswith("/api/")
        and request.method in {"POST", "PUT", "PATCH", "DELETE"}
    )
    if is_api_change:
        origin = request.headers.get("origin")
        fetch_site = request.headers.get("sec-fetch-site")
        if (
            (origin is not None and origin not in ALLOWED_ORIGINS)
            or fetch_site == "cross-site"
        ):
            return JSONResponse(
                status_code=403,
                content={
                    "code": "ORIGIN_NOT_ALLOWED",
                    "message": "허용되지 않은 주소에서 보낸 요청이에요.",
                },
            )

    response = await call_next(request)
    if request.url.path.startswith(("/api/auth/", "/api/me/")):
        response.headers["Cache-Control"] = "no-store"
    return response



@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "입력값의 형식과 허용된 값을 확인해주세요.",
        },
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