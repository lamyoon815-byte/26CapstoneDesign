from fastapi import HTTPException, Request
from sqlmodel import Session

from backend.db import engine
from backend.models import User


def get_current_user(request: Request) -> User:
    user_id = request.session.get("user_id")

    if type(user_id) is not int:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_REQUIRED",
                "message": "로그인이 필요해요.",
            },
        )

    with Session(engine) as session:
        user = session.get(User, user_id)
        if user is None:
            request.session.clear()
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "AUTH_REQUIRED",
                    "message": "로그인이 필요해요.",
                },
            )
        return user
