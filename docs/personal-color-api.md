# 퍼스널컬러 AI 연결

## 로컬 API
- POST `/api/me/personal-color`: 로그인 필요. multipart/form-data의 `file`로 사진 전송. 성공 결과를 해당 계정의 최신 결과로 저장.
- GET `/api/me/personal-color`: 로그인 필요. `{ "result": null }` 또는 `{ "result": { ...진단 결과 } }`.
- 재진단 성공 시 최신 결과 교체. 실패 시 기존 결과 유지. 다음 서버 시작 때 결과 테이블 자동 생성; 기존 테이블 삭제 불필요.

## 응답 예시 (POST)
```json
{"season":"autumn","season_ko":"가을웜","season_full":"autumn-warm","tone":"autumn_warm","confidence":null,"confidence_level":"low","diagnosed_at":"2026-10-30T00:00:00Z"}
```
외부 AI의 confidence는 low/medium/high 등급입니다. 숫자 확률이 아니므로 confidence는 null로 두고 confidence_level에 보존합니다. low를 0.3 같은 수치로 변환하거나 백분율로 표시하지 않습니다. 표시명은 season_ko를 사용합니다.

## FE 연결 예시
```javascript
const form = new FormData();
form.append("file", fileInput.files[0]);
const response = await fetch("/api/me/personal-color", {
  method: "POST",
  credentials: "same-origin",
  body: form,
});
const data = await response.json();
if (!response.ok) throw new Error(data.message);
// data.season_ko 표시, data.confidence_level === "low"면 낮은 신뢰도 안내
```
Content-Type을 직접 지정하지 마세요. 브라우저가 multipart boundary를 생성합니다. 업로드 중 버튼을 비활성화하고 완료/실패 시 해제하세요. 기존 api.js가 JSON 전용이면 위처럼 FormData 경로를 사용해야 합니다.

## 사진과 대기 시간
JPG/PNG/WebP/BMP, 최대 10 MiB(10 * 1024 * 1024 바이트). 로컬은 파일 시그니처 확인, 실제 이미지 디코딩과 얼굴 검출은 AI 서버가 수행합니다. 사진은 외부 https://personal-color-api-nqrx.onrender.com/predict 에 전송됩니다. 로컬 DB에는 결과만 저장하며 업로드 임시 파일은 닫습니다. 외부 AI 서버의 보관 정책은 AI 담당에게 확인해야 합니다. 화면에 외부 AI로 사진이 전송됨을 안내하세요.

외부 요청 연결 대기는 20초, 응답 읽기 대기는 120초입니다. 무료 서버 첫 요청은 지연될 수 있으므로 FE에 짧은 요청 제한이 있다면 조정하고 대기 안내를 표시하세요. 자동 재시도는 하지 않습니다.

## 오류
공통 `{code, message}`: 401 로그인 필요, 400 빈 파일, 413 크기 초과, 415 지원하지 않는 형식, 422 파일 누락/AI 분석 불가, 502 AI 연결/응답 오류, 503 AI 혼잡, 504 AI 시간 초과.

## 검증
`python -B -m unittest scripts.test_personal_color -v`
임시 SQLite와 HTTP 모의 응답을 사용하며 외부 사진 전송과 실제 DB 수정 없이 검사합니다. 실제 사진을 이용한 AI 진단은 Swagger에서 별도로 확인해야 합니다. 현재 단계에는 톤 기반 상품 적합도 계산이 포함되지 않습니다.
