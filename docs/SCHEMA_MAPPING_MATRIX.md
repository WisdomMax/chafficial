# 🧩 기존 데이터 엔진 ORM 스키마 매핑 매트릭스 (SCHEMA MAPPING MATRIX - REVISED)

본 문서는 `templates/PARTNER_LISTING_INTAKE_TEMPLATE.csv`를 통해 인입된 정규화 데이터가 기존 차피셜 데이터 엔진 V0.1의 핵심 ORM 테이블과 어떻게 연동되는지 정의한 기술 명세입니다. 실제 DB 스키마 제약조건(NOT NULL, CHECK, FK)을 100% 충족하도록 보정되었습니다.

---

## 1. ORM 테이블 매핑 상세 명세

### A. `VehicleCatalog` (차량 표준 카탈로그)
| 인입 템플릿 필드 | 기존 ORM 컬럼 | 타입 및 제약조건 | 매핑 방식 / 정합성 규칙 |
| :--- | :--- | :--- | :--- |
| *(미지정)* | `catalog_id` | Integer, PK, Autoincrement | **임의 문자열 생성 금지**. DB 자동 증가 정수 PK 사용. |
| `manufacturer` | `manufacturer` | String(50), NOT NULL | 직접 1:1 매핑 |
| `model_name` | `model_name` | String(50), NOT NULL | 직접 1:1 매핑 |
| `sub_model` | `generation` | String(50), NOT NULL | 세대 미확정 시 `sub_model` 또는 'UNKNOWN'으로 보정 |
| `sub_model` | `sub_model` | String(50), NULL 허용 | 직접 1:1 매핑 |
| `trim` | `trim` | String(50), NOT NULL | 트림명 매핑 (공백 시 '기본형') |
| `model_year` | `model_year` | Integer, NOT NULL | 정수형 연식 매핑 (CHECK: 1970~2050) |
| `fuel_type` | `fuel_type` | String(30), NOT NULL | '가솔린', '디젤', 'LPG' 등 매핑 |
| `transmission` | `transmission` | String(30), NOT NULL | '오토', '수동' 매핑 (기본값 '오토') |
| *(기본값)* | `displacement_cc` | Integer, NULL 허용 | 1999 (시연 기본값) |
| *(기본값)* | `seating_capacity` | Integer, NULL 허용 | 5 (시연 기본값) |

### B. `VehicleIdentity` (차량 식별 객체)
| 인입 템플릿 필드 | 기존 ORM 컬럼 | 타입 및 제약조건 | 매핑 방식 / 정합성 규칙 |
| :--- | :--- | :--- | :--- |
| `anonymous_vehicle_code` | `vehicle_id` | String(36), PK | 비식별 익명 코드 직접 매핑 (없을 시 UUID) |
| *(원천 미수집)* | `plate_number` | String(20), NULL 허용 | **NULL 유지** (개인정보 보호 및 비식별화 준수) |
| *(원천 미수집)* | `vin` | String(30), NULL 허용 | **NULL 유지** (비식별화 준수) |
| *(고정값)* | `identity_status` | String(20), NOT NULL | **`UNCONFIRMED`** (CHECK 제약: CONFIRMED, UNCONFIRMED, AMBIGUOUS 중 비식별 코드 규격 준수) |
| *(기본값)* | `identity_confidence` | Float, NOT NULL | **`0.5`** (식별 증빙 미확정 기본 신뢰도; 근거 없는 0.95 부여 차단) |

### C. `Listing` (플랫폼 매물 엔티티)
| 인입 템플릿 필드 | 기존 ORM 컬럼 | 타입 및 제약조건 | 매핑 방식 / 정합성 규칙 |
| :--- | :--- | :--- | :--- |
| `internal_listing_id` | `listing_id` | String(36), PK | 파트너 내부 매물 ID 매핑 |
| *(고정값)* | `source_platform` | String(50), NOT NULL | `PARTNER_DIRECT_INTAKE` |
| `internal_listing_id` | `source_listing_id` | String(100), NOT NULL | 파트너 원천 ID 매핑 |
| `anonymous_vehicle_code` | `vehicle_id` | String(36), FK | `VehicleIdentity.vehicle_id` 참조 |
| `partner_dealer_code` | `seller_reference` | String(100), NULL 허용 | 딜러 식별 코드 매핑 |
| `first_observed_date` | `first_observed_at` | DateTime(tz=True), NOT NULL | 최초 관측일 매핑 (UTC) |
| *(확인된 위치)* | `raw_location` | String(200), NOT NULL | 실제 확인된 매물 소재지 (임의 생성 금지) |
| *(정규화 권역)* | `normalized_region_id`| String(50), FK | **`REGION_JANGANPYEONG`** (configs/regions.yaml 체계 준수) |
| `contract_closed_date` | `current_status` | String(30), NOT NULL | **`ACTIVE`** (미계약) 또는 **`DELISTED`** (판매 완료 시 전이) (CHECK: ACTIVE, PRICE_CHANGED, DELISTED, UNKNOWN 준수; 임의의 SOLD 금지) |

### D. `ListingSnapshot` (불변 시계열 스냅샷)
| 인입 템플릿 필드 | 기존 ORM 컬럼 | 타입 및 제약조건 | 매핑 방식 / 정합성 규칙 |
| :--- | :--- | :--- | :--- |
| *(자동생성)* | `snapshot_id` | String(36), PK | `SNAP_{listing_id}_INIT` |
| `internal_listing_id` | `listing_id` | String(36), FK | `Listing.listing_id` 참조 |
| `first_observed_date` | `observed_at` | DateTime(tz=True), NOT NULL | 시장 관측 시점 매핑 |
| *(시스템 시간)* | `ingested_at` | DateTime(tz=True), NOT NULL | 시스템 인입 시점 (시간 누출 차단) |
| `target_listing_price_krw` | `price_krw` | Integer, NOT NULL | 목표 등록가 (CHECK: price_krw >= 0) |
| `mileage_km` | `mileage_km` | Integer, NOT NULL | 주행거리 (CHECK: mileage_km >= 0) |
| `contract_closed_date` | `listing_status` | String(30), NOT NULL | **`ACTIVE`** 또는 **`DELISTED`** (CHECK 제약 준수) |
| *(정규화 권역)* | `normalized_region_id`| String(50), NULL 허용 | **`REGION_JANGANPYEONG`** |
| `outer_panel...` 외 | `raw_specs` | JSON, NULL 허용 | 성능점검 상세 스펙(사고/누유/점검자) 보존 |

---

## 2. 판매 후보(`SalesCandidate`) 연동 분리 원칙

- **인입과 후보 선정의 명확한 분리:**  
  인입된 모든 매물이 자동으로 판매 마케팅 후보가 되지 않습니다.
- **후보 선정 트리거:**  
  인입 및 데이터 무결성 검증 통과 후, 별도의 마케팅 적합성 알고리즘과 딜러 서면 위임 확인(`is_marketing_eligible == True`)을 거친 차량에 한해서만 독립적인 의사결정 모듈을 통해 `SalesCandidate` 레코드를 생성합니다.

---

## 3. SQLite 실제 INSERT/FLUSH 테스트 실증 완료

- `tests/test_partner_intake.py::test_synthetic_3_cars_actual_orm_insert_and_flush`를 통해 상기 매핑 규칙에 따라 생성된 ORM 객체가 실제 SQLite 인메모리 DB의 모든 NOT NULL, FK, CHECK 제약조건을 단 하나의 오류 없이 통과함을 실증하였습니다.
- 트랜잭션 종료 시 즉시 `ROLLBACK`하여 운영 DB 및 테스트 DB의 오염을 원천 방지하였습니다.
