#회원가입·로그인·조회·로그아웃 인증 API 4개

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from backend.db import engine
from backend.models import User
from backend.schemas import (
    SignupRequest,
    SignupResponse,
    UserResponse,
)
from backend.security import hash_password, verify_password
from backend.dependencies import get_current_user
from backend.schemas import AuthResponse, LoginRequest


router = APIRouter(
    prefix="/api/auth",
    tags=["인증"],
)


def duplicate_email_response():
    return JSONResponse(
        status_code=409,
        content={
            "code": "EMAIL_ALREADY_EXISTS",
            "message": "이미 가입된 이메일이에요.",
        },
    )


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=201,
    responses={
        409: {"description": "이메일 중복"},
    },
)
def signup(payload: SignupRequest):
    email = str(payload.email)

    with Session(engine) as session:
        # 1. 같은 이메일이 있는지 확인합니다.
        existing_user = session.exec(
            select(User).where(User.email == email)
        ).first()

        if existing_user is not None:
            return duplicate_email_response()

        # 2. 비밀번호를 해시로 변환합니다.
        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            name=payload.name,
            marketing_consent=payload.marketing_consent,
        )

        # 3. DB에 저장합니다.
        session.add(user)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()

            # 동시에 같은 이메일로 가입한 경우도 처리합니다.
            duplicate = session.exec(
                select(User).where(User.email == email)
            ).first()

            if duplicate is not None:
                return duplicate_email_response()

            # 이메일 중복 외 DB 오류는 별도로 드러나게 합니다.
            raise

        session.refresh(user)

        # 4. 비밀번호 해시를 제외한 정보만 응답합니다.
        return SignupResponse(
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                marketing_consent=user.marketing_consent,
            )
        )


# 존재하지 않는 계정도 비밀번호 검증을 수행합니다.
DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing")


def make_auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            marketing_consent=user.marketing_consent,
        )
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request):
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.email == str(payload.email))
        ).first()
        stored_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        password_matches = verify_password(payload.password, stored_hash)

        if user is None or not password_matches:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "INVALID_CREDENTIALS",
                    "message": "이메일 또는 비밀번호를 확인해주세요.",
                },
            )

        request.session.clear()
        request.session["user_id"] = user.id
        return make_auth_response(user)


@router.get("/me", response_model=AuthResponse)
def me(user: User = Depends(get_current_user)):
    return make_auth_response(user)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"message": "로그아웃했어요."}
