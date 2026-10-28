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