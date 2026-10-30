from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from backend.db import engine
from backend.dependencies import get_current_user
from backend.models import User
from backend.schemas import RecommendationResponse
from backend.services.recommendations import get_recommendations

router = APIRouter(prefix="/api/me", tags=["성분 기반 추천"])


@router.get("/recommendations", response_model=RecommendationResponse)
def recommendations(
    category: str | None = Query(default=None, max_length=50),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    user: User = Depends(get_current_user),
):
    normalized_category = category.strip() if category else None
    with Session(engine) as session:
        return get_recommendations(
            session=session,
            user_id=user.id,
            category=normalized_category or None,
            page=page,
            page_size=page_size,
        )
