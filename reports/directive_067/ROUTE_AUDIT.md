# 차마트·차피셜 차량 관련 실제 경로 전수 조사 보고서
## DIRECTIVE 067 P0 실제 엔드포인트 및 공개 승인 경계 감사

**일시:** 2026-10-28 23:57 KST  
**기준 커밋:** `86677be`  
**감사 대상:** `src/chaficial/platform/app.py`, `service.py`  

---

### 1. 전수 경로 매핑 및 공개 승인 경계 감사표

| 순번 | 엔드포인트 경로 | HTTP 메서드 | 인증 요건 | 대상 시스템 | 운영 공개 판정 (`is_vehicle_eligible_for_chamart_public`) | 데모/비공개 접근 결과 | 직접 URL 접근 결과 |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | `/api/chamart/vehicles` | `GET` | 공개 (None) | 차마트 쇼룸 | 적용 (`allow_demo=False` 강제) | 목록에서 100% 제외 (0건 반환) | 200 OK (빈 배열 `[]`) |
| 2 | `/api/chamart/vehicles/{id}` | `GET` | 공개 (None) | 차마트 쇼룸 | 적용 (`allow_demo=False` 강제) | **HTTP 404 Not Found** 차단 | 실차 승인 매물만 200 반환 |
| 3 | `/api/chamart/consultations` | `POST` | 공개 (None) | 차마트 쇼룸 | 적용 (`allow_demo=False` 강제) | **HTTP 400 Bad Request** 차단 및 DB 미생성 | 필수 입력 및 개인정보 동의 검증 |
| 4 | `/api/chamart/vehicles/{id}/inquiry` | `POST` | 공개 (None) | 차마트 쇼룸 | 적용 (`allow_demo=False` 강제) | **HTTP 400 Bad Request** 차단 및 DB 미생성 | 3번 엔드포인트 위임 처리 |
| 5 | `/api/staging/chamart/vehicles` | `GET` | 격리 (None) | 스테이징 쇼룸 | 적용 (`allow_demo=True` 고정) | 3대 시연 매물 정상 노출 | 200 OK (시연 3건 JSON) |
| 6 | `/api/staging/chamart/vehicles/{id}` | `GET` | 격리 (None) | 스테이징 쇼룸 | 적용 (`allow_demo=True` 고정) | 시연 매물 상세 200 반환 | 200 OK (시연 상세 JSON) |
| 7 | `/api/vehicles` | `GET` | **관리자 토큰 (`require_auth`)** | 차피셜 관리시스템 | 미적용 (내부 관리 마스터) | 401 Unauthorized (토큰 부재 시) | 비공개/데모/실차 전체 조회 가능 |
| 8 | `/api/vehicles/{id}` | `GET` | **관리자 토큰 (`require_auth`)** | 차피셜 관리시스템 | 미적용 (내부 관리 마스터) | 401 Unauthorized (토큰 부재 시) | 관리자 전용 상세 데이터 반환 |
| 9 | `/api/admin/vehicles/{id}/publish` | `POST` | **관리자 토큰 (`require_auth`)** | 차피셜 관리시스템 | 미적용 (승인 처리 주체) | 401 Unauthorized (토큰 부재 시) | 실차 검증 원장 확인 후 승인 |
| 10 | `/chamart` | `GET` | 공개 (HTML) | 차마트 고객 쇼룸 | 프런트엔드 연동 (`/api/chamart/vehicles`) | 데모 카드 0건, 표준 빈 상태 표출 | 상용 고객 쇼룸 렌더링 |
| 11 | `/staging/chamart` | `GET` | 격리 (HTML) | 스테이징 검수 쇼룸 | 프런트엔드 연동 (`/api/staging/...`) | 상단 `STAGING PREVIEW` 배너, 3대 시연 | 디자인 검수 전용 화면 |

---

### 2. 단일 DB·프로세스 구조의 한계 및 논리적 격리 명시

1. **인프라 구조**:
   - 현재 차마트(고객 쇼룸)와 차피셜(관리 시스템)은 **동일한 단일 FastAPI 서버 프로세스(포트 8501)**와 **동일한 로컬 SQLite 데이터베이스(`chaficial.db`)**를 공유하고 있습니다.
2. **논리적 격리 (Logical Isolation)**:
   - 본 시스템의 격리는 물리적 네트워크 망 분리나 별도 인프라 배포가 아닌, **애플리케이션 라우팅 및 서비스 계층의 단일 SSOT 가드 함수(`is_vehicle_eligible_for_chamart_public`)를 통한 논리적 격리**입니다.
3. **보안 및 무결성 경계**:
   - 클라이언트의 `mode=demo` 쿼리 파라미터 변조는 서버단에서 무조건 무시되며,
   - 비공개 또는 데모 매물의 ID로 운영 상세 API 접근 시 무조건 `HTTP 404`가 반환되고,
   - 상담 신청 시 `HTTP 400`으로 차단되어 DB `consultations`에 비승인 매물 레코드가 일절 생성되지 않도록 보호되고 있습니다.
