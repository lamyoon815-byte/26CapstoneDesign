from datetime import date, datetime, timezone

from sqlalchemy import CheckConstraint

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


class Purchase(SQLModel, table=True):
    __tablename__ = "purchases"
    __table_args__ = (
        CheckConstraint(
            "review_status IS NULL OR review_status IN ('good', 'bad')",
            name="ck_purchase_review_status",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    purchased_at: date
    paid_price: int = Field(ge=0)
    review_status: str | None = Field(default=None)
    # 리뷰 시각은 UTC 시간대를 포함해 저장·응답합니다.
    reviewed_at: datetime | None = Field(default=None)
    is_sample: bool = Field(default=False)



class Ingredient(SQLModel, table=True):
    __tablename__ = "ingredients"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    name: str
    is_sample: bool = Field(default=False)


class ProductIngredient(SQLModel, table=True):
    __tablename__ = "product_ingredients"

    product_id: int = Field(foreign_key="products.id", primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredients.id", primary_key=True)



class UserIngredientPreference(SQLModel, table=True):
    __tablename__ = "user_ingredient_preferences"
    __table_args__ = (
        CheckConstraint(
            "preference IN ('avoid', 'prefer')",
            name="ck_user_ingredient_preference",
        ),
    )

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredients.id", primary_key=True)
    preference: str
