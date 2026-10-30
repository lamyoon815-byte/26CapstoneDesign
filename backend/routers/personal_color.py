from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session

from backend.db import engine
from backend.dependencies import get_current_user
from backend.models import PersonalColorResult, User
from backend.schemas import PersonalColorLatestResponse, PersonalColorResponse
from backend.services.personal_color import MAX_IMAGE_BYTES, predict_personal_color

router = APIRouter(prefix="/api/me/personal-color", tags=["퍼스널컬러"])


@router.get("", response_model=PersonalColorLatestResponse)
def get_personal_color(user: User = Depends(get_current_user)):
    with Session(engine) as session:
        result = session.get(PersonalColorResult, user.id)
        return PersonalColorLatestResponse(
            result=PersonalColorResponse.model_validate(result, from_attributes=True)
            if result else None,
        )


@router.post("", response_model=PersonalColorResponse, description=(
    "업로드한 사진을 외부 Render AI 서버에 전송합니다. "
    "로컬 DB에는 사진 없이 최신 성공 결과만 저장합니다. 첫 응답은 지연될 수 있습니다."
))
def diagnose_personal_color(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    try:
        data = file.file.read(MAX_IMAGE_BYTES + 1)
    finally:
        file.file.close()
    prediction = predict_personal_color(data)
    result = PersonalColorResponse(
        **prediction, diagnosed_at=datetime.now(timezone.utc),
    )
    # 외부 요청 동안 DB 트랜잭션을 열어두지 않습니다.
    # 재진단 실패 시 기존 성공 결과는 그대로 유지합니다.
    values = result.model_dump(exclude={"confidence"})
    with Session(engine) as session:
        statement = insert(PersonalColorResult).values(user_id=user.id, **values)
        session.execute(statement.on_conflict_do_update(
            index_elements=["user_id"], set_=values,
        ))
        session.commit()
    return result
