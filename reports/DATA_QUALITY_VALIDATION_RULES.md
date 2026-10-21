# 🚘 CHA-FICIAL AI PROJECT
## 데이터 품질 검증 규칙 명세서 (DATA QUALITY VALIDATION RULES)

**문서 목적:** 차피셜 시스템에 인입되는 모든 중고차 매물 및 실거래 데이터의 무결성을 검증하기 위한 10대 불변 규칙 정의  
**작성일자:** 2026-10-21  

---

### [규칙 1] 차량 및 매물 식별자 유일성 (ID Uniqueness)
- `internal_listing_id`는 시스템 내에서 유일(Primary Key)해야 하며, 동일 매물에 대한 중복 인입을 차단합니다.
- `anonymous_vehicle_code`는 실물 차량 단위로 고유하게 매핑되며, 다중 플랫폼 등록 매물은 별도의 listing_id를 유지하되 동일한 vehicle_code에 링크됩니다.

### [규칙 2] 가격 및 주행거리 비음수성 (Non-negative Constraints)
- `cost_price_krw`, `target_listing_price_krw`, `min_acceptable_price_krw`, `actual_contract_price_krw` >= 0
- `mileage_km` >= 0
- 0원 이하의 가격 또는 음수 주행거리 레코드는 파이프라인 인입 단계에서 즉각 거절(Reject)됩니다.

### [규칙 3] 연식 및 날짜 유효성 (Date & Temporal Validity)
- `model_year`는 1990년 이상, 현재 연도 + 1년 이하의 정수여야 합니다.
- `inspection_date` <= `first_observed_date` <= `contract_closed_date` 순서를 엄격히 준수해야 하며, 미래 시점 날짜는 차단됩니다.

### [규칙 4] 등록 호가와 확정 계약가 분리 (Listing vs Contract Price)
- 플랫폼에 등록된 희망 가격(`target_listing_price_krw`)과 실제 계약 체결 가격(`actual_contract_price_krw`)은 절대 단일 필드로 혼용되지 않으며, 계약 체결 전까지 `actual_contract_price_krw`는 반드시 NULL이어야 합니다.

### [규칙 5] 무사고와 미확정 상태 구분 (Accident Status Clarity)
- 성능점검이 아직 이루어지지 않은 상태는 결코 '무사고'로 간주되지 않으며, `UNCONFIRMED`(미확정)로 분리 관리됩니다.
- 성능점검표 원본이 입증된 경우에만 '무사고(외판 단순교환)' 또는 '완전무사고(교환 없음)' 상태가 부여됩니다.

### [규칙 6] 외판(1랭크) vs 골격(2랭크) 손상 분리 (Damage Severity Hierarchy)
- 외판 패널(휀더, 도어, 후드 등 단순 볼트 체결 부위)의 교환/판금과 차체 골격(휠하우스, 사이드멤버, 필러 등 용접 구조 부위)의 손상은 명확히 분리 기록되며, 골격 손상 차량은 자동 마케팅 추천 대상에서 최하위 우선순위로 격하됩니다.

### [규칙 7] 판매 종료(DELISTED)와 판매 완료(SOLD_OUT) 분리
- 플랫폼에서 매물이 내려간 사유가 실제 판매 계약 체결인지(`SOLD_CONFIRMED`), 딜러 변심/타 상사 이동/단순 광고 중단인지(`DELISTED_UNCONFIRMED`)를 엄격히 구분하여 학습에 반영합니다.

### [규칙 8] 광고 권한 미확인 차량의 홍보 차단 (Ad Delegation Gate)
- `advertising_delegation_status`가 명시적으로 `DELEGATED`로 서면 확인되지 않은 매물은, 아무리 가성비와 수익 기대값이 높더라도 AI 영상 제작 및 SNS 광고 집행 대상에서 100% 원천 배제됩니다.

### [규칙 9] 순수익 산식의 수학적 일관성 (Net Profit Determinism)
- 확정 순수익 공식:
  $$\text{net\_profit\_krw} = \text{gross\_commission\_revenue\_krw} - (\text{video\_production\_cost\_krw} + \text{ad\_spend\_krw} + \text{other\_operational\_costs\_krw})$$
- 어떠한 경우에도 계산 불일치가 허용되지 않으며, 계약 전 정산 상태는 `UNSETTLED`로 격리됩니다.

### [규칙 10] 관측 시점과 시스템 적재 시점 분리 (Time-Travel Integrity)
- 실제 시장 관측 시각(`observed_at`)과 차피셜 데이터베이스 인입 시각(`ingested_at`)을 분리하여, 뒤늦게 입력된 과거 데이터가 과거 의사결정 시점에 사전 유출되는 Data Leakage를 차단합니다.
