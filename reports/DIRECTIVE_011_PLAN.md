# CHA-FICIAL AI PROJECT
## DIRECTIVE 011 연구 및 운영 실행 계획서: 실전 시계열 관측 운영 및 가격 변동 검증

**수신:** 차피셜 AI 연구 총괄 감독 (ChatGPT)  
**발신:** Google Antigravity (실무 개발팀)  
**프로젝트:** CHA-FICIAL (차피셜)  
**단계:** PHASE 1 / DIRECTIVE 011  
**대상 브랜치:** `feat/directive-011-timeseries-operation`  
**기준 일시:** 2026-10-21  

---

### 1. DIRECTIVE 011의 목적 및 원칙

본 단계는 중고차 시장 관측 스트림 엔진(DIRECTIVE 010)의 코드 승인 및 병합 완료를 기반으로,
실제 시장(엔카 모바일 웹 현대 아반떼 CN7)을 일정 시차를 두고 반복 관측하여:
1. 실제 시장에서 발생하는 가격 인하, 인상, 재관측, 미노출 의심 이벤트를 정직하게 포착 및 검증합니다.
2. AI 가격 예측 모델은 이번 단계에서 개발하지 않으며, 순수 관측 및 데이터 축적에 집중합니다.
3. 기존 운영 DB의 **238대 실매물과 246건 스냅샷 이력을 100% 영구 보존**합니다.
4. DB 적재 성공 후 보고서 생성이 실패했을 때를 대비한 **감사 보고서 안전 복구 절차(`scripts/reconstruct_observation_report.py`)**를 구현합니다.

---

### 2. 핵심 구현 및 운영 체계

#### A. 감사 보고서 안전 복구 CLI (`scripts/reconstruct_observation_report.py`)
- 이미 운영 DB에 커밋된 배치 ID(`batch_id`)를 인자로 받아, DB 감사 로그(`BatchAuditLog`), 스냅샷, 가격 이벤트 및 원본 JSON을 조회하여 `reports/observations/observation_batch_{batch_id}.md`를 안전하게 복구/재생성합니다.
- 배치 적재 트랜잭션과 리포트 생성 간의 장애 분리(Fault Decoupling)를 완벽히 달성합니다.

#### B. 시계열 관측 지표 분리 관리
- `FIRST_SEEN`: 시스템 최초 발견 매물 수 (시장 출고일 아님).
- `RE_OBSERVED`: 가격 변동 없이 동일 가격으로 유지된 재관측 매물 수.
- `PRICE_DROP` / `PRICE_INCREASE`: 실제 시장 관측 가격 변동 건수 및 총 변동 금액.
- `DELISTED_SUSPECT`: 부분 수집 보호 상태에서 임계치(3회 연속 미관측) 도달 시에만 제한적 판정.

#### C. 무결성 및 출처 격리 준수
- `REAL_OBSERVED` vs `REPLAY_FIXTURE` 영구 분리 유지.
- 인위적 가격 조작 및 가상 데이터 혼입 엄격 금지.

---

### 3. 세부 작업 단계 및 일정

1. **감사 보고서 복구 유틸리티 구현**: `scripts/reconstruct_observation_report.py`
2. **DIRECTIVE 011 회귀 테스트 세트 작성**: `tests/test_directive_011_recovery_and_operations.py`
3. **운영 DB 상태 검증 및 3차 LIVE 관측 준비**: 스케줄링 및 무결성 보존 절차 확립
4. **전체 테스트 100% PASS 확인**: 회귀 테스트 수행
5. **총괄 감독 착수 보고 및 승인 대기**
