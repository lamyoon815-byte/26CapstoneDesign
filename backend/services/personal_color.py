"""External AI adapter. Image bytes are forwarded, never stored in the DB."""
import httpx
from fastapi import HTTPException

AI_URL = "https://personal-color-api-nqrx.onrender.com/predict"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
SEASONS = {
    "spring": ("봄웜", "spring-warm", "spring_warm"),
    "summer": ("여름쿨", "summer-cool", "summer_cool"),
    "autumn": ("가을웜", "autumn-warm", "autumn_warm"),
    "winter": ("겨울쿨", "winter-cool", "winter_cool"),
}


def fail(status: int, code: str, message: str):
    raise HTTPException(status_code=status, detail={"code": code, "message": message})


def image_format(data: bytes) -> tuple[str, str]:
    if not data:
        fail(400, "EMPTY_IMAGE", "사진 파일이 비어 있어요.")
    if len(data) > MAX_IMAGE_BYTES:
        fail(413, "IMAGE_TOO_LARGE", "사진은 최대 10MB까지 업로드할 수 있어요.")
    # 확장자/MIME만 신뢰하지 않고 파일 시그니처를 확인합니다.
    # 이미지 디코딩 및 얼굴 검출은 AI 서버에서 수행합니다.
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    if data.startswith(b"BM"):
        return "bmp", "image/bmp"
    fail(415, "UNSUPPORTED_IMAGE", "JPG, PNG, WebP, BMP 사진을 올려주세요.")


def predict_personal_color(data: bytes) -> dict:
    extension, content_type = image_format(data)
    try:
        with httpx.Client(timeout=httpx.Timeout(120.0, connect=20.0)) as client:
            response = client.post(
                AI_URL,
                files={"file": (f"photo.{extension}", data, content_type)},
            )
    except httpx.TimeoutException:
        fail(504, "AI_TIMEOUT", "AI 서버 응답이 늦어지고 있어요. 잠시 후 다시 시도해주세요.")
    except httpx.RequestError:
        fail(502, "AI_UNAVAILABLE", "AI 서버에 연결하지 못했어요. 잠시 후 다시 시도해주세요.")

    if response.status_code in (400, 413, 415, 422):
        fail(422, "AI_IMAGE_REJECTED", "AI가 사진을 분석하지 못했어요. 얼굴이 잘 보이는 다른 사진으로 시도해주세요.")
    if response.status_code == 429:
        fail(503, "AI_BUSY", "AI 서버가 혼잡해요. 잠시 후 다시 시도해주세요.")
    if not 200 <= response.status_code < 300:
        fail(502, "AI_UPSTREAM_ERROR", "AI 서버에서 오류가 발생했어요. 잠시 후 다시 시도해주세요.")
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if not isinstance(payload, dict):
        fail(502, "AI_INVALID_RESPONSE", "AI 응답 형식을 확인할 수 없어요.")
    season = payload.get("season")
    confidence = payload.get("confidence")
    if not isinstance(season, str) or season not in SEASONS:
        fail(502, "AI_INVALID_RESPONSE", "AI의 계절 분류 값을 확인할 수 없어요.")
    ko, full, tone = SEASONS[season]
    if (
        not isinstance(confidence, str)
        or confidence not in ("low", "medium", "high")
        or payload.get("season_ko") != ko
        or payload.get("season_full") != full
    ):
        fail(502, "AI_INVALID_RESPONSE", "AI의 진단 응답 형식이 합의된 형식과 달라요.")
    return {
        "season": season, "season_ko": ko, "season_full": full,
        "tone": tone, "confidence_level": confidence,
    }
