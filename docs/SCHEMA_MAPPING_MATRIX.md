# 🧩 기존 데이터 엔진 ORM 스키마 매핑 매트릭스 (SCHEMA MAPPING MATRIX)

본 문서는 `templates/PARTNER_LISTING_INTAKE_TEMPLATE.csv`를 통해 인입된 정규화 데이터가 기존 차피셜 데이터 엔진 V0.1의 5대 핵심 ORM 테이블과 어떻게 연동되는지 정의한 기술 명세입니다.

---

## 1. 5대 핵심 ORM 테이블 매핑 현황

### A. `VehicleCatalog` (차량 표준 카탈로그)
| 인입 템플릿 필드 | 기존 ORM 컬럼 | 타입 | 매핑 방식 / 비고 |
| :--- | :--- | :--- | :--- |
| `manufacturer` | `manufacturer` | String | 직접 1:1 매핑 |
| `model_name` | `model_name` | String | 직접 1:1 매핑 |
| `sub_model` | `sub_model` | String | 직접 1:1 매핑 |
| `trim` | `trim` | String | 직접 1:1 매핑 |
| `model_year` | `model_year` | Integer | 직접 1:1 매핑 |
| `fuel_type` | `fuel_type` | String | 직접 1:1 매핑 |
| `transmission` | `transmission` | String | 직접 1:1 매핑 |
| *(템플릿 미포함)* | `generation` | String | V0.1 카탈로그 기본값(NULL 허용) |
| *(템플릿 미포함)* | `is_facelift` | Boolean | V0.1 카탈로그 기본값(False) |
| *(템플릿 미포함)* | `displacement_cc` | Integer | V0.1 카탈로그 기본값(NULL 허용) |
| *(템플릿 미포함)* | `seating_capacity` | Integer | V0.1 카탈로그 기본값(5) |

### B. `VehicleIdentity` (차량 식별 객체)
| 인입 템플릿 필드 | 기존 ORM 컬럼 | 타입 | 매핑 방식 / 비고 |
| :--- | :--- | :--- | :--- |
| `anonymous_vehicle_code` | `vehicle_id` | String | 익명 식별자 직접 매핑 |
| *(수집 원천 배제)* | `plate_number` | String | **NULL 유지** (개인정보보호 및 비식별화 원칙) |
| *(수집 원천 배제)* | `vin` | String | **NULL 유지** (비식별화 원칙) |
| *(내부 자동생성)* | `identity_status` | String | `ANONYMIZED_PARTNER_CODE`로 고정 |
| *(내부 자동생성)* | `identity_confidence` | Float | 0.95 (파트너 전산 코드 신뢰도) |

### C. `Listing` (플랫폼 매물 엔티티)
| 인입 템플릿 필드 | 기존 ORM 컬럼 | 타입 | 매핑 방식 / 비고 |
| :--- | :--- | :--- | :--- |
| `internal_listing_id` | `listing_id` | String | PK 직접 매핑 |
| *(고정값)* | `source_platform` | String | `PARTNER_DIRECT_INTAKE` |
| `internal_listing_id` | `source_listing_id` | String | 파트너 원천 ID로 매핑 |
| `anonymous_vehicle_code` | `vehicle_id` | String | 외래키 매핑 |
| `partner_dealer_code` | `seller_reference` | String | 딜러 식별자 매핑 |
| `first_observed_date` | `first_observed_at` | DateTime | 문자열 파싱 후 UTC 변환 |
| *(고정값)* | `raw_location` | String | `서울 성동구 장안평 중고차 매매단지` |
| *(고정값)* | `normalized_region_id`| String | `REG_SEOUL_JANGANPYEONG` |
| `contract_closed_date` | `current_status` | String | 계약일 존재 시 `SOLD`, 미존재 시 `ACTIVE` |

### D. `ListingSnapshot` (불변 시계열 스냅샷)
| 인입 템플릿 필드 | 기존 ORM 컬럼 | 타입 | 매핑 방식 / 비고 |
| :--- | :--- | :--- | :--- |
| *(자동생성)* | `snapshot_id` | String | `SNAP_{listing_id}_{observed_at}` |
| `internal_listing_id` | `listing_id` | String | 외래키 매핑 |
| `first_observed_date` | `observed_at` | DateTime | 관측 시점 매핑 |
| *(시스템 시간)* | `ingested_at` | DateTime | 실제 DB 인입 시스템 시간 (시간 누출 차단) |
| `target_listing_price_krw` | `price_krw` | Integer | 목표 등록가 스냅샷 |
| `mileage_km` | `mileage_km` | Integer | 주행거리 스냅샷 |
| `contract_closed_date` | `listing_status` | String | `ACTIVE` 또는 `SOLD` |
| *(고정값)* | `normalized_region_id`| String | `REG_SEOUL_JANGANPYEONG` |
| `outer_panel...` 외 | `raw_specs` | JSON | 사고부위, 침수, 누유 등 성능점검 전체 JSON 보존 |

### E. `SalesCandidate` (판매 및 마케팅 후보)
| 인입 템플릿 필드 | 기존 ORM 컬럼 | 타입 | 매핑 방식 / 비고 |
| :--- | :--- | :--- | :--- |
| *(자동생성)* | `candidate_id` | String | `CAND_{listing_id}` |
| `internal_listing_id` | `listing_id` | String | 외래키 매핑 |
| *(고정값)* | `target_region_id` | String | `REG_SEOUL_JANGANPYEONG` |
| `advertising_delegation_status` | `availability_status` | String | 서면 위임 검증 시 `AVAILABLE`, 미검증 시 `HOLD` |
| *(사후 승인)* | `partner_review_status`| String | `UNREVIEWED` -> 딜러 승인 시 `APPROVED` |

---

## 2. 연동 원칙 및 안전 게이트

1. **DRY RUN 기본 원칙:**  
   검증기(`PartnerListingIntakeValidator`)는 매핑 데이터 딕셔너리(`preview_orm_mappings`)만 생성하며, 명시적 승인 트랜잭션 전까지 실제 데이터베이스에 `commit`을 실행하지 않습니다.
2. **외래키 무결성 보장:**  
   `VehicleCatalog` -> `VehicleIdentity` -> `Listing` -> `ListingSnapshot` -> `SalesCandidate` 순서로 상위 의존성을 먼저 확보한 뒤 순차 인입합니다.
3. **외부 운영 DB 업로드 원천 차단:**  
   본 파일럿 인입은 로컬 SQLite 격리 세션에서만 실행되며, 어떠한 외부 클라우드나 프로덕션 데이터베이스로도 자동 발송되지 않습니다.
