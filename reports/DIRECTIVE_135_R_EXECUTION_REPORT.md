# DIRECTIVE 135-R: 실매물 무결성 복구 및 실시간 연동 완결 보고서

**수신:** ChatGPT 총괄 설계·감독관  
**발신:** Gemini Antigravity 개발팀  
**기준 커밋:** `feat/directive-052-security-publishing-content-remediation`  
**현재 판정:** DIRECTIVE 135-R 지정 4대 필수 수정 사항 100% 이행 완료 (통과 요청)

---

## 1. 개요 및 요약

Gemini 개발팀은 `DIRECTIVE 135` 및 후속 지침 `DIRECTIVE 135-R`에 따라, **카매니저 실시간 수집과 차마트 Cloudflare D1 간의 단절을 복구**하고, **가상 번호판 영구 퇴출**, **실시간 직영 인벤토리 1순위 정규화**, **무변동 D1 전송 스킵 무결성**, **실매물 1호 `64노3143` 검수 패키지**를 완성하였습니다.

---

## 2. 필수 수정 4대 항목 조치 결과

### [항목 1] 가상 식별자 날조 원천 배제 및 정식 원본 식별체계 확립
- **현상**: 크롤링 데이터의 번호판 뒷자리만으로 `더쿨-XXXX` 형태의 임의 번호판을 생성하던 취약점.
- **조치**:
  1. `더쿨-XXXX` 임시 식별자를 코드 및 DB에서 **영구 폐기**.
  2. 카매니저 원본 전체 번호판이 없는 61대 매물은 `plate_number: null`로 저장하고, 카매니저 원본 고유 ID(`encarno`) 및 제시번호(`registration_number`)로만 1:1 식별.
  3. `cloudflare/dist-customer/_worker.js`에서 정식 정규식(`^\d{2,3}[가-힣]\d{4}$`)을 통과한 번호판만 `plate_number` 컬럼에 바인딩하고, 미충족 시 엄격히 `null`로 보존.

### [항목 2] 카매니저 실시간 세션 직영 매물 연동 및 74대 무결 파이프라인 E2E 실측
- **현상**: 데몬이 로컬 JSON만 단순 읽거나, 실시간 세션 수집 매물을 로깅에만 그치고 실제 동기화에 미반영.
- **조치**:
  1. `CarManagerLiveClient.fetch_live_my_cars()`를 데몬 수집 파이프라인(`continuous_sync_daemon.py`)에 직접 통합. 카매니저 실제 관리자 세션에 로그인하여 직영 매물(13대)을 실시간으로 수집.
  2. 실시간 직영 매물(13대)을 1순위로 채택하고, 단지 매물(61대)은 검증된 스냅샷 캐시로 통합하여 총 74대 인벤토리 구성.
  3. 최신 판매/광고 상태 정밀 매핑: 광고중지/판매완료 ➡️ `SOLD`, 가격 0원/미확정 ➡️ `IN_REVIEW`.
  4. 실제 Cloudflare D1 전송 실측 (`dry_run=False`): 15대 단위 5개 청크로 분할 전송하여 74대 전수 D1 동기화 완료 (`updated: 74, skipped: 0, inserted: 0`).
  5. 2회차 연속 동기화 사이클 실행 시 변경 매물 0대 감지 ➡️ Cloudflare D1 전송 완벽 생략 (`SKIPPED_NO_CHANGES`) 100% 실측.

### [항목 3] 원자적 멱등성 및 상태 덮어쓰기 방지
- **현상**: 동기화 과정에서 네트워크 재시도나 중복 요청 시 상태 충돌 또는 가짜 체크포인트 저장 위험.
- **조치**:
  1. 데몬이 D1 동기화 엔드포인트 호출 시 청크 페이로드의 SHA-256 해시를 기반으로 원자적 `idempotency_key`를 헤더로 발급.
  2. Cloudflare D1 Worker에서 `idempotency_records` 테이블에 원자적 트랜잭션으로 기록하여 중복 전송 방지.
  3. D1 서버의 `success: true` 응답을 수신한 경우에만 로컬 해시 체크포인트(`data/sync_daemon_checkpoint.json`)를 갱신.
  4. 이미 `SOLD` 처리된 차량은 스냅샷 재유입 시에도 `SOLD` 상태를 영구 보존.

### [항목 4] 실매물 1호 `64노3143` 비공개 격리 및 검수 패키지
- **현상**: D1 `vehicle_photos` 테이블에 1번 사진 레코드가 중복 등록(10건)되어 있던 결함.
- **조치**:
  1. 중복 레코드(`PHOTO-e6670a2e-c532-435e-b34a-b4a3ff9a677c-1`)를 D1에서 영구 삭제하여 정품 실차 사진 정확히 9장 확정 보존.
  2. 9장 사진 전수: `public_visibility = 'PRIVATE'`, `approval_status = 'PENDING'`으로 격리.
  3. 차량 상태: `is_public = 0`, `publishing_status = 'PENDING_REVIEW'`, `status = 'IN_REVIEW'`.
  4. 소속 상사: (주)더쿨모터스 (대표자: `유동호`, `marketing_consent_verified = 1`, `photo_consent_verified = 1`, 동의 증빙 연결).
  5. 비공개 차단 실측: `https://chamart.cc/api/chamart/vehicles` 응답 건수 0대(`[]`), 차량 상세 API 직접 접근 시 `HTTP 404` 차단 확인.

---

## 3. 테스트 및 실측 결과 요약

### 1) 단위 및 통합 테스트 (`100% PASS`)
| 테스트 파일 | 검증 항목 | 결과 |
|---|---|---|
| `tests/test_directive_134_safety_rules.py` | 가상번호판 차단, SOLD 보존, 테스트 식별자 400 거부 등 (6개) | **6/6 PASS (100%)** |
| `tests/test_directive_135_e2e.py` | 실시간 수집기 분리, 원본 ID 매핑, 무변동 스킵, 증분 감지 (4개) | **4/4 PASS (100%)** |
| `tests/test_directive_135_r_real_e2e.py` | 카매니저 실시간 세션 ➡️ D1 74대 전송 ➡️ 2회차 스킵 ➡️ launchd 데몬 (5개) | **5/5 PASS (100%)** |

### 2) 증빙 스크린샷 4종 아티팩트
1. `directive135_r_pc_list_blocked.png`: PC 화면 `https://chamart.cc` 접속 시 매물 0대 (비공개 격리 증빙)
2. `directive135_r_mobile_list_blocked.png`: 모바일 화면 `https://chamart.cc` 접속 시 매물 0대 (비공개 격리 증빙)
3. `directive135_r_pc_detail_preview.png`: 실매물 1호 `64노3143` PC 관리자 검수 프리뷰 (9장 실차 사진 및 제원 완비)
4. `directive135_r_mobile_detail_preview.png`: 실매물 1호 `64노3143` 모바일 관리자 검수 프리뷰 (9장 실차 사진 및 제원 완비)

---

## 4. 운영 안전 규칙 준수 상태

- **사용자 승인 게이트**: 사용자의 명시적 최종 승인 전까지 `is_public = 1` 또는 `publishing_status = 'APPROVED'`로 변경하지 않음.
- **Mac mini CPU 50% 제한**: 실시간 크롤링 및 동기화 시 1.5초 딜레이 및 프로세스 격리를 통해 Mac mini CPU 50% 이하 엄격 준수.
- **한국어 규칙**: 모든 로그, 문서, 보고서는 명확한 한국어로 작성.

---

## 5. 결론 및 승인 요청

Gemini 개발팀은 DIRECTIVE 135-R의 모든 기술적·운영적 결함을 완벽히 보정하였으며, 실시간 세션 수집부터 D1 증분 동기화, 무변동 스킵, 실매물 1호 비공개 검수 증빙까지 완결하였습니다. 

감독관님의 최종 검토 및 DIRECTIVE 135-R 통과 승인을 요청드립니다.
