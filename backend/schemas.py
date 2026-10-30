from datetime import date, datetime
from typing import Literal

# 가입·로그인 입력, 사용자 응답 형식

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=50)
    marketing_consent: bool = False

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("이름을 입력해주세요.")

        return value


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    marketing_consent: bool


class SignupResponse(BaseModel):
    user: UserResponse


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class AuthResponse(BaseModel):
    user: UserResponse



class PurchaseResponse(BaseModel):
    id: int
    product_id: int
    brand: str
    name: str
    image_url: str
    purchased_at: date
    paid_price: int
    review_status: Literal["good", "bad"] | None
    reviewed_at: datetime | None
    is_sample: bool


class PurchaseListResponse(BaseModel):
    items: list[PurchaseResponse]
    total: int


class ReviewRequest(BaseModel):
    review_status: Literal["good", "bad"] | None


class ReviewResponse(BaseModel):
    purchase_id: int
    review_status: Literal["good", "bad"] | None
    reviewed_at: datetime | None



class SuspectEvidence(BaseModel):
    purchase_id: int
    product_id: int
    product_name: str
    image_url: str
    review_status: Literal["good", "bad"]


class SuspectItem(BaseModel):
    ingredient_id: int
    ingredient_name: str
    is_sample: bool
    state: Literal["candidate", "pending"]
    bad_count: int
    good_count: int
    score: float
    reason: str
    products: list[SuspectEvidence]


class SuspectListResponse(BaseModel):
    items: list[SuspectItem]
    total: int
    evaluated_product_count: int
    missing_ingredient_product_ids: list[int]
    rule_version: str
    notice: str



class IngredientPreferenceRequest(BaseModel):
    preference: Literal["avoid", "prefer"]


class IngredientPreferenceResponse(BaseModel):
    ingredient_id: int
    ingredient_name: str
    preference: Literal["avoid", "prefer"]
    source: Literal["manual"] = "manual"
    is_sample: bool


class ProfileResponse(BaseModel):
    user: UserResponse
    avoid_ingredients: list[IngredientPreferenceResponse]
    preferred_ingredients: list[IngredientPreferenceResponse]



class CartItemRequest(BaseModel):
    quantity: int = Field(ge=1, le=99, strict=True)


class CartItemResponse(BaseModel):
    product_id: int
    brand: str
    name: str
    image_url: str
    unit_price: int
    quantity: int
    line_total: int


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    item_count: int
    total_quantity: int
    subtotal: int



class CartWarningItem(BaseModel):
    warning_id: str
    type: Literal["personal_avoid", "personal_suspect"]
    sources: list[Literal["personal_avoid", "personal_suspect"]]
    product_id: int
    product_name: str
    ingredient_id: int
    ingredient_name: str
    is_sample: bool
    message: str
    suspect_evidence: SuspectItem | None = None


class CartDuplicateProduct(BaseModel):
    product_id: int
    product_name: str


class CartDuplicateIngredient(BaseModel):
    ingredient_id: int
    ingredient_name: str
    is_sample: bool


class CartDuplicateItem(BaseModel):
    warning_id: str
    type: Literal["cart_duplicate"] = "cart_duplicate"
    level: Literal["info"] = "info"
    products: list[CartDuplicateProduct]
    ingredients: list[CartDuplicateIngredient]
    message: str


class CartConflictMatch(BaseModel):
    left_product_id: int
    left_ingredient_id: int
    left_ingredient_name: str
    right_product_id: int
    right_ingredient_id: int
    right_ingredient_name: str


class CartConflictItem(BaseModel):
    warning_id: str
    type: Literal["cart_conflict"] = "cart_conflict"
    level: Literal["info"] = "info"
    rule_id: int
    rule_code: str
    rule_name: str
    condition_text: str
    source_url: str | None
    is_sample: bool
    products: list[CartDuplicateProduct]
    matches: list[CartConflictMatch]
    message: str


class CartWarningsResponse(BaseModel):
    items: list[CartWarningItem]
    total: int
    affected_product_count: int
    duplicate_items: list[CartDuplicateItem] = Field(default_factory=list)
    duplicate_total: int = 0
    duplicate_affected_product_count: int = 0
    cart_conflict_items: list[CartConflictItem] = Field(default_factory=list)
    cart_conflict_total: int = 0
    cart_conflict_affected_product_count: int = 0
    missing_cart_ingredient_product_ids: list[int]
    missing_review_ingredient_product_ids: list[int]
    rule_version: str
    notice: str



class IngredientRuleResponse(BaseModel):
    id: int
    code: str
    name: str
    ingredient_a_id: int
    ingredient_a_name: str
    ingredient_b_id: int
    ingredient_b_name: str
    condition_text: str
    message: str
    source_url: str | None
    is_sample: bool
    enabled: bool


class IngredientRuleListResponse(BaseModel):
    items: list[IngredientRuleResponse]
    total: int
