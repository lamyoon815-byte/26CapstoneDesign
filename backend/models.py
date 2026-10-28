from datetime import datetime, timezone

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


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)

    email: str = Field(
        unique=True,
        index=True,
        max_length=320,
    )

    password_hash: str

    name: str = Field(max_length=50)

    marketing_consent: bool = Field(default=False)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )