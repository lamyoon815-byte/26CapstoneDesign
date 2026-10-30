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


class PurchaseConflictEvidence(BaseModel):
    purchase_id: int
    purchased_at: date


class PurchaseConflictItem(CartConflictItem):
    type: Literal["purchase_conflict"] = "purchase_conflict"
    cart_product_id: int
    purchased_product_id: int
    purchases: list[PurchaseConflictEvidence]


class PurchaseConflictAnalysis(BaseModel):
    items: list[PurchaseConflictItem]
    window_start: date
    window_end: date
    missing_ingredient_product_ids: list[int]


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
    purchase_conflict_items: list[PurchaseConflictItem] = Field(default_factory=list)
    purchase_conflict_total: int = 0
    purchase_conflict_affected_product_count: int = 0
    purchase_window_start: date | None = None
    purchase_window_end: date | None = None
    missing_recent_purchase_ingredient_product_ids: list[int] = Field(default_factory=list)
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



class RecommendationItem(BaseModel):
    product_id: int
    brand: str
    name: str
    category: str
    price: int
    image_url: str
    status: Literal["eligible", "excluded", "unassessed"]
    reasons: list[str]
    cautions: list[str]
    avoid_ingredient_ids: list[int]
    preferred_ingredient_ids: list[int]
    suspect_ingredient_ids: list[int]
    latest_review_status: Literal["good", "bad"] | None
    has_ingredient_data: bool
    has_sample_ingredients: bool


class RecommendationResponse(BaseModel):
    items: list[RecommendationItem]
    total: int
    page: int
    page_size: int
    excluded_items: list[RecommendationItem]
    excluded_total: int
    unassessed_items: list[RecommendationItem]
    unassessed_total: int
    rule_version: str
    notice: str


class ProductIngredientInfo(BaseModel):
    ingredient_id: int
    ingredient_name: str
    is_sample: bool


class ProductDetailResponse(BaseModel):
    product_id: int
    brand: str
    name: str
    category: str
    price: int
    image_url: str
    color_hex: str | None
    ingredients: list[ProductIngredientInfo]
    has_ingredient_data: bool


class PersonalIngredientAnalysis(BaseModel):
    ingredient_id: int
    ingredient_name: str
    is_sample: bool
    manual_preference: Literal["avoid", "prefer"] | None
    review_state: Literal["candidate", "pending"] | None
    review_evidence: SuspectItem | None


class ProductAnalysisResponse(BaseModel):
    assessment: RecommendationItem
    ingredient_analysis: list[PersonalIngredientAnalysis]
    rule_version: str
    notice: str


class ProductAlternativesResponse(BaseModel):
    source_product_id: int
    category: str
    items: list[RecommendationItem]
    total: int
    limit: int
    rule_version: str
    notice: str


class PersonalColorResponse(BaseModel):
    season: Literal["spring", "summer", "autumn", "winter"]
    season_ko: str
    season_full: str
    tone: Literal["spring_warm", "summer_cool", "autumn_warm", "winter_cool"]
    # AI가 확률을 제공하지 않으므로 임의로 수치로 변환하지 않습니다.
    confidence: float | None = None
    confidence_level: Literal["low", "medium", "high"]
    diagnosed_at: datetime


class PersonalColorLatestResponse(BaseModel):
    result: PersonalColorResponse | None
