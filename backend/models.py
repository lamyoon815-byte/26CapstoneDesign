# 상품 한 개에 어떤 정보를 저장할지 정의

from sqlmodel import Field, SQLModel


class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: int | None = Field(default=None, primary_key=True)
    brand: str
    name: str
    category: str
    price: int
    image_url: str
    color_hex: str | None = None


class ProductListResponse(SQLModel):
    items: list[Product]
    total: int