# 🚘 CHA-FICIAL AI PROJECT
## DIRECTIVE 002-B 결과 보고서
### 데이터 엔진 V0.1 최종 무결성 보완 및 PR 생성

**발신:** Google Antigravity 엔지니어링 / 연구팀  
**수신:** CHA-FICIAL AI 연구 총괄 감독 (ChatGPT)  
**저장소:** https://github.com/WisdomMax/chafficial  
**대상 브랜치:** `fix/directive-002a-audit-corrections`  
**PR 번호:** [#1 (Open)](https://github.com/WisdomMax/chafficial/pull/1)  
**기준 커밋:** `3f3cb49`  
**일자:** 2026-10-21  

---

### 1. 발견된 결함과 수정 원인

| 결함 영역 | 원인 분석 | 해결 및 조치 내역 |
| :--- | :--- | :--- |
| **1. 과거 시점 지역 누출** | 과거 시점 조회 시 `Listing.normalized_region_id`라는 현재 상태 필드를 사용하여, 사후에 매물 소재지가 장안평으로 확인/정정된 경우 과거 시점 조회에도 역방향으로 노출되는 누출 발생 | `ListingSnapshot.normalized_region_id` 컬럼을 신설하여 관측 시점마다 확인된 지역을 불변 스냅샷으로 기록. `get_eligible_listings_as_of`는 현재 매물 주소가 아닌 **당시 스냅샷에 기록된 지역 ID만을 엄격히 확인**하여 과거 누출 원천 차단. |
| **2. 일반 매물 풀과 실제 선정 후보 혼동** | `get_sales_candidates_as_of`가 `SalesCandidate` 테이블을 조회하지 않고 단순 활성 `Listing` 목록을 반환하여, '추천 풀'과 '실제 선정 후보'의 개념이 모호해짐 | 추천 대상 매물 풀 조회(`get_eligible_listings_as_of`)와 실제 AI/파트너가 선정한 후보 조회(`get_selected_candidates_as_of`)로 명확히 분리. `SalesCandidate`에 `created_at` 컬럼을 도입하여 사후 선정된 후보의 과거 시점 누출 방지. |
| **3. 지역 설정 버그 (빈 배열 및 검증 부재)** | `get_active_sales_region_ids()`에서 `sales_region_ids=[]` 빈 배열 입력 시 파이썬 `bool([]) == False` 판정으로 인해 기본 장안평으로 fallback 됨. 또한 유효성 검사 부재 | `cfg.sales_region_ids is not None` 판정으로 수정하여 빈 배열 설정 시 0건 조회를 정상 존중. `update_sales_regions`에서 존재하지 않는 지역(`InvalidRegionError`), 비활성 지역(`InactiveRegionError`) 차단 및 중복 자동 유일화 구현. |
| **4. 기존 DB에 대한 불변성 트리거 미적용** | SQLite DDL 트리거가 `after_create` 이벤트에만 걸려 있어, 이미 테이블이 생성된 레거시 DB 파일에는 트리거가 누락될 수 있음 | `ensure_snapshot_immutability_triggers(engine)` 멱등 함수를 구현하여 기존 데이터 손실 없이 트리거 유무를 검사·주입. `ListingSnapshot` DELETE 시 부모가 살아있을 때의 직접 삭제만 차단하고 부모 매물 삭제 시의 외래키 CASCADE는 정합성을 보장하도록 개선. |

---

### 2. 실제 변경 파일

* `src/chaficial/models/snapshot.py`: `normalized_region_id` 컬럼 추가, `ensure_snapshot_immutability_triggers` 구현, 직접 삭제 차단 및 부모 CASCADE 구분 트리거 DDL 정교화
* `src/chaficial/models/candidate.py`: `created_at` 컬럼 추가 (적재 시점 추적)
* `src/chaficial/models/listing.py`: `snapshots` 관계에 `cascade="all, delete-orphan", passive_deletes=True` 명시
* `src/chaficial/regions/manager.py`: `InvalidRegionError`, `InactiveRegionError` 정의, 빈 배열 정상 처리 및 중복/유효성 검증
* `src/chaficial/time_travel/query_engine.py`: `get_eligible_listings_as_of` (당시 스냅샷 지역 검사), `get_selected_candidates_as_of` (실제 SalesCandidate 시계열 조회) 신설
* `src/chaficial/synthetic/generator.py`: 스냅샷 생성 시 관측 시점 `normalized_region_id` 영구 기록
* `tests/test_directive_002a_corrections.py`: 스냅샷 지역 메타데이터 동기화
* `tests/test_directive_002b_corrections.py`: DIRECTIVE 002-B 전용 반례 검증 테스트 4종 신규 구현

---

### 3. 신규 반례 테스트 및 결과

* `test_time_travel_region_leakage_protection`: 10/1 지역 미확정 매물이 10/10 장안평으로 사후 정정되더라도, 10/5 시점 조회에는 장안평 매물로 나타나지 않고 10/11 시점에만 정상 반영됨을 검증 (**통과**)
* `test_distinction_between_eligible_listings_and_selected_candidates`: 매물 풀(`get_eligible_listings_as_of`)과 실제 선정 후보(`get_selected_candidates_as_of`)의 분리 및 10/5 선정 후보가 10/3 조회에 누출되지 않음을 검증 (**통과**)
* `test_region_configuration_edge_cases`: 기본값 장안평, 빈 배열 설정 시 0건 조회, 수원·인천 확장, 존재하지 않는 지역 차단, 비활성 지역 차단, 중복 지역 제거 등 6가지 엣지 케이스 검증 (**통과**)
* `test_existing_database_immutability_enforcement_and_cascade`: 트리거가 삭제된 레거시 DB에 무손실로 불변성 트리거를 주입하고, 기존 스냅샷의 직접 UPDATE/DELETE 차단 및 부모 CASCADE 안전성 검증 (**통과**)

---

### 4. 전체 pytest 실행 결과 (32개 테스트 100% 통과)

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.12, pytest-9.1.1, pluggy-1.7.0 -- /Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI
configfile: pyproject.toml
testpaths: tests
collected 32 items

tests/test_directive_002_all.py::test_01_listing_crud PASSED             [  3%]
tests/test_directive_002_all.py::test_02_price_history_preservation PASSED [  6%]
tests/test_directive_002_all.py::test_03_time_travel_leakage_prevention PASSED [  9%]
tests/test_directive_002_all.py::test_04_multi_platform_listing_separation PASSED [ 12%]
tests/test_directive_002_all.py::test_05_identity_unconfirmed_state PASSED [ 15%]
tests/test_directive_002_all.py::test_06_korean_generation_and_trim_separation PASSED [ 18%]
tests/test_directive_002_all.py::test_07_option_status_distinction PASSED [ 21%]
tests/test_directive_002_all.py::test_08_outer_panel_vs_structural_damage_distinction PASSED [ 25%]
tests/test_directive_002_all.py::test_09_unconfirmed_accident_insurance_handling PASSED [ 28%]
tests/test_directive_002_all.py::test_10_market_analysis_vs_sales_target_separation PASSED [ 31%]
tests/test_directive_002_all.py::test_11_region_expansion PASSED         [ 34%]
tests/test_directive_002_all.py::test_12_unconfirmed_region_filter PASSED [ 37%]
tests/test_directive_002_all.py::test_13_delisted_not_sold_confirmation PASSED [ 40%]
tests/test_directive_002_all.py::test_14_partner_availability_tracking PASSED [ 43%]
tests/test_directive_002_all.py::test_15_promotion_decision_logging PASSED [ 46%]
tests/test_directive_002_all.py::test_16_marketing_vs_outcome_separation PASSED [ 50%]
tests/test_directive_002_all.py::test_17_listing_vs_actual_deal_price_separation PASSED [ 53%]
tests/test_directive_002_all.py::test_18_settlement_unconfirmed_revenue_protection PASSED [ 56%]
tests/test_directive_002_all.py::test_19_source_permissions_verification PASSED [ 59%]
tests/test_directive_002_all.py::test_20_end_to_end_scenario PASSED      [ 62%]
tests/test_directive_002_all.py::test_integrity_negative_price_blocked PASSED [ 65%]
tests/test_directive_002_all.py::test_integrity_duplicate_settlement_blocked PASSED [ 68%]
tests/test_directive_002a_corrections.py::test_region_residential_address_not_misclassified_as_complex PASSED [ 71%]
tests/test_directive_002a_corrections.py::test_region_partner_verified_origin_preservation PASSED [ 75%]
tests/test_directive_002a_corrections.py::test_snapshot_orm_update_blocked PASSED [ 78%]
tests/test_directive_002a_corrections.py::test_snapshot_raw_sql_update_and_delete_blocked PASSED [ 81%]
tests/test_directive_002a_corrections.py::test_time_travel_candidate_lifecycle_and_delayed_ingest_protection PASSED [ 84%]
tests/test_directive_002a_corrections.py::test_region_configuration_dynamic_sales_regions PASSED [ 87%]
tests/test_directive_002b_corrections.py::test_time_travel_region_leakage_protection PASSED [ 90%]
tests/test_directive_002b_corrections.py::test_distinction_between_eligible_listings_and_selected_candidates PASSED [ 93%]
tests/test_directive_002b_corrections.py::test_region_configuration_edge_cases PASSED [ 96%]
tests/test_directive_002b_corrections.py::test_existing_database_immutability_enforcement_and_cascade PASSED [100%]

============================== 32 passed in 0.63s ==============================
```

---

### 5. Ruff 정적 검사 결과

```text
$ uv run ruff check .
All checks passed!
```

---

### 6. 기존 DB 스냅샷 보호 검증 결과

`test_existing_database_immutability_enforcement_and_cascade`를 통해 트리거가 누락된 채 생성되었던 레거시 SQLite 파일에 `ensure_snapshot_immutability_triggers()`를 실행한 후, 기존 데이터의 손실 없이 Raw SQL UPDATE 및 직접 DELETE가 모두 `OperationalError/IntegrityError`로 강력히 차단됨을 실증하였습니다.

---

### 7. Git 커밋 내역 및 상태

```text
commit 3f3cb490819d835cb452ca97bfff84330f73ca88 (HEAD -> fix/directive-002a-audit-corrections, origin/fix/directive-002a-audit-corrections)
Author: Wisdom Kim <wisdom@macmini.local>
Date:   Wed Oct 21 07:01:12 2026 +0900

    fix: DIRECTIVE 002-B 지역 누출 차단, 선정 후보 구분, 지역 설정 예외 처리, 기존 DB 불변성 강화
```

---

### 8. 원격 브랜치 및 실제 PR URL

* **원격 브랜치**: `origin/fix/directive-002a-audit-corrections`
* **실제 Pull Request**: **[https://github.com/WisdomMax/chafficial/pull/1](https://github.com/WisdomMax/chafficial/pull/1)** (PR #1, Open 상태)
* **원격 상태**: 감독의 최종 검토 및 승인 전까지 `main` 브랜치에 병합하지 않고 열린 상태로 유지 중입니다.

---

### 9. 남아 있는 결함 및 기술적 한계

1. **파트너 승인 이력의 시계열 추적 한계**:
   * 현재 `SalesCandidate.partner_review_status`는 후보 레코드의 필드로 관리됩니다. 파트너가 최초에 `PENDING`이었다가 사후에 `APPROVED`로 변경한 세부 타임스탬프 이력을 완벽히 재현하려면, 향후 `CandidateReviewHistory` 같은 별도의 이력 스냅샷 테이블을 추가 도입하는 것이 연구적으로 더욱 엄격할 수 있습니다.
2. **PostgreSQL 전환 시 DDL 고려**:
   * 현재 제공된 `ensure_snapshot_immutability_triggers`는 SQLite 전용(`sqlite_master`) 문법입니다. PostgreSQL 이전 시 동일한 로직을 PL/pgSQL 트리거 함수로 자동 분기할 수 있도록 마이그레이션 팩토리가 준비되어야 합니다.

---

DIRECTIVE 002-B COMPLETED
