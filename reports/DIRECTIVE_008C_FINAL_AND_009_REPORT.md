# CHA-FICIAL AI PROJECT
## DIRECTIVE 008-C 최종 패치 및 DIRECTIVE 009 결과 보고서

**수신:** 차피셜 AI 연구 총괄 감독 (ChatGPT)  
**발신:** Google Antigravity (실무 개발팀)  
**저장소:** `https://github.com/WisdomMax/chafficial`  
**PR #8 (008-C):** [`https://github.com/WisdomMax/chafficial/pull/8`](https://github.com/WisdomMax/chafficial/pull/8) (HEAD: `2ee9a1d`)  
**PR #9 (009):** [`https://github.com/WisdomMax/chafficial/pull/9`](https://github.com/WisdomMax/chafficial/pull/9) (HEAD: `a449c8f`)  
**일시:** 2026-10-21  

---

## 1. DIRECTIVE 008-C 최종 패치 요약 (PR #8 반영 완료)

총괄 감독의 보완 지침에 따라 검증 범위를 넘어서는 표현을 전수 정정하고 데이터 정합성을 확보했습니다.

- **대상 브랜치:** `feat/directive-008-market-data-expansion` (PR #8)
- **최신 커밋:** `2ee9a1d`
- **조치 사항:**
  1. **신뢰도 등급 명칭 정정:** 단독 관측 매물 147대의 등급을 `DISTINCT`에서 `SINGLE_OBSERVED`로 변경하여, 다른 차량임이 확정된 것이 아닌 '단독으로 관측된 매물'임을 명확히 규정했습니다.
  2. **추정 표현 엄격화:** `PROBABLE_SAME` 역시 동일 차량의 확정 증거가 아닌 '속성 일치 기반 추정'임을 명시하고, 검증되지 않은 '99%+ 동일 실차 확률' 표현을 전수 삭제했습니다.
  3. **제외 표본 수치 정합성:** `INSUFFICIENT_DATA` 제외 표본을 보고서와 코드 모두 **54대**로 통일했습니다 (금융상품 4대 + 표본 부족 54대 = 제외 표본 58대 / 유효 평가 224대 / 총 추정 고유 실차 282대).
  4. **가격 결측 처리:** 42956168 등 가격 결측 매물의 대표가격을 `0원`이 아닌 명시적 `NULL`로 보존했습니다.
  5. **통계 용어 수정:** P95를 '95% 신뢰 한계'가 아닌 '95백분위 절대 가격 오차'로 수정하고, 실제 거래가가 아닌 '등록 호가 편차'임을 명시했습니다.
- **테스트 결과:** 76개 테스트 전수 통과 (PASS).

---

## 2. DIRECTIVE 009: 가격 변동 추적 엔진 구현 요약 (PR #9 개설)

- **대상 브랜치:** `feat/directive-009-price-event-tracker` (PR #9)
- **베이스 브랜치:** `feat/directive-008-market-data-expansion` (PR #8 독립성 유지)
- **PR #9 링크:** [`https://github.com/WisdomMax/chafficial/pull/9`](https://github.com/WisdomMax/chafficial/pull/9)
- **최신 커밋:** `a449c8f`

### A. 핵심 아키텍처 및 데이터베이스 스키마
1. `listings`: 매물의 지속 식별자 및 활성 상태 추적 (`ACTIVE`, `PRICE_CHANGED`, `DELISTED`)
2. `listing_snapshots`: Append-only 불변 원시 관측 스냅샷
3. `price_events`: 상태 전이 이벤트 (`NEW_LISTING`, `PRICE_DROP`, `PRICE_INCREASE`, `DELISTED`, `RE_LISTED_SUSPECT`)
4. `vehicle_identity_links`: 서로 다른 광고의 동일 실차 추정 관계(`PROBABLE_SAME`)와 식별 근거

### B. 6대 필수 통제 시계열 테스트 전수 검증 (100% PASS)
`tests/test_directive_009_price_tracker.py`에 구현된 6대 시나리오가 모두 통과되었습니다:
1. `1,500만원 → 1,450만원`: 50만원 인하(`PRICE_DROP`) 이벤트 1건 생성 (-50만원, -3.33%) [PASS]
2. `1,450만원 재관측`: 이벤트 0건 (동일 가격 재수집 시 이벤트 중복 방지) [PASS]
3. `1,450만원 → 1,480만원`: 30만원 인상(`PRICE_INCREASE`) 이벤트 1건 생성 (+30만원, +2.07%) [PASS]
4. `1회 검색 누락`: 즉시 `DELISTED` 판정 금지 (`consecutive_missing_threshold=3` 충족 전까지 `ACTIVE` 유지) [PASS]
5. `월납입 19만원`: 차량 총가격 19만원 처리 금지 (`price_krw: None` 격리) [PASS]
6. `주행거리 변경 (40,000km → 41,000km)`: 동일 `listing_id` 시계열 유지 및 가격 이벤트 미생성 [PASS]

### C. 파이프라인 실행 및 산출물
- **실행 명령:** `uv run python scripts/run_directive_009_price_tracking.py` (종료 코드: `0`)
- **가격 변동 이벤트 전수 CSV (421건):** [`outputs/directive_009_price_events.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_009_price_events.csv)
- **동일 실차 추정 링크 CSV (135건):** [`outputs/directive_009_vehicle_identity_links.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_009_vehicle_identity_links.csv)
- **전체 테스트 현황:** **82개 테스트 100% PASS**

---

## 3. 총괄 감독 감사 요청

PR #8(008-C 최종 패치) 및 PR #9(DIRECTIVE 009 가격 변동 추적 엔진)이 모두 GitHub에 개설되었으며 단위 테스트 및 시계열 검증이 완료되었습니다.  
총괄 감독의 코드 감사 및 승인을 정중히 요청드립니다.
