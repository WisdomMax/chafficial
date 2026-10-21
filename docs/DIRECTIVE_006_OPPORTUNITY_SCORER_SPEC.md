# 🚘 CHA-FICIAL AI : 기회 매물 평가 점수 산정 공식 및 기술 명세서
## OPPORTUNITY SCORER V0.1 SPECIFICATION

**프로젝트:** 차피셜(CHA-FICIAL) AI  
**모듈:** `src/chaficial/scorer/opportunity.py`  
**버전:** V0.1 (규칙 기반 다차원 스코어러)  
**기준일:** 2026-10-21  

---

## 1. 개요 및 목적

차피셜 OPPORTUNITY SCORER V0.1은 전국 중고차 플랫폼(엔카, KB차차차, KCar 등)에서 관측된 매물 데이터를 분석하여, **"어떤 차량을 발굴하여 AI 영상으로 홍보했을 때 실질적인 판매 성사와 순수익 창출 가능성이 가장 높은가?"**를 0~100점의 점수로 정량화하는 규칙 기반 엔진입니다.

본 스코어러는 단순 등록가격 비교에 의존하지 않고, 동일군 벤치마크 통계, 주행거리 가치 편차, 사고/외판 상태 감가, 가격 인하 모멘텀, 데이터 신뢰도를 종합하여 **상태 조정 공정 가치(Adjusted Fair Value)**를 산출한 뒤 최종 기회 점수를 부여합니다.

---

## 2. 동일군(Cohort) 비교 및 표본 기준

### 1) 코호트 그룹핑 키
동일한 시장 가치를 비교하기 위해 매물을 다음 6대 제원 기준으로 그룹핑합니다:
$$\text{Cohort Key} = \text{제조사} + \text{모델} + \text{세대} + \text{연식} + \text{트림} + \text{연료}$$
- 예: `현대_아반떼_CN7_2021_모던_가솔린`

### 2) 최소 표본 수 제약 (Sample Adequacy)
- **최소 필요 표본 수 ($N_{\min}$): 3대**
- 동일군 내 표본 수가 3대 미만일 경우:
  - 억지 통계 왜곡을 방지하기 위해 점수를 산출하지 않음 (`opportunity_score = None`).
  - 평가 상태를 `INSUFFICIENT_DATA`로 설정.
  - 선정 사유: `"동일 비교군 표본 부족 (현재 N대 / 최소 3대 필요)"` 반환.

---

## 3. 상태 조정 공정 가치 (Adjusted Fair Value) 산출 공식

단순 호가 차이가 아닌, 차량의 실제 상태를 반영한 정당한 시장 가치를 도출합니다:

$$\text{Adjusted Fair Value} = \text{Median Price} + \Delta_{\text{mileage}} + \Delta_{\text{condition}}$$

### 1) 비교 표본 중앙 등록가격 ($\text{Median Price}$)
동일 코호트 내 활성 매물들의 등록가격 중앙값(원 단위).

### 2) 주행거리 가치 보정액 ($\Delta_{\text{mileage}}$)
동일군 표본의 중앙 주행거리($\text{Median Mileage}$) 대비 대상 차량의 주행거리 차이를 가치로 환산합니다. (신차급 준중형/중형 기준 10,000km당 약 400,000원 감가율 적용):

$$\Delta_{\text{mileage}} = \left( \frac{\text{Median Mileage} - \text{Target Mileage}}{10,000} \right) \times 400,000\text{원}$$
- 주행거리가 중앙값보다 20,000km 짧은 경우: 가치 $+800,000\text{원}$ 상승.
- 주행거리가 중앙값보다 30,000km 긴 경우: 가치 $-1,200,000\text{원}$ 하락.

### 3) 사고 및 성능 상태 보정액 ($\Delta_{\text{condition}}$)
- **완전 무사고 ($\text{NO\_ACCIDENT}$):** $0\text{원}$ (기준)
- **단순 외판 교환 ($\text{SIMPLE\_REPAIR}$):** $-600,000\text{원}$
- **주요 골격 유사고 ($\text{MAJOR\_ACCIDENT}$):** $-2,500,000\text{원}$
- **상태 미상 ($\text{UNKNOWN}$):** $-300,000\text{원}$

---

## 4. 실질 가격 경쟁력 및 기회 점수 (Opportunity Score) 공식

### 1) 실질 가격 경쟁력 이익률 ($\text{Advantage \%}$)
$$\text{Net Advantage (KRW)} = \text{Adjusted Fair Value} - \text{Target Price}$$
$$\text{Adjusted Advantage \%} = \left( \frac{\text{Net Advantage}}{\text{Adjusted Fair Value}} \right) \times 100$$

### 2) 점수 산정 다차원 구성 요소 (기본 50점 기준)
$$\text{Raw Score} = 50.0 + S_{\text{price}} + S_{\text{mileage}} + S_{\text{condition}} + S_{\text{momentum}}$$

1. **가격 경쟁력 점수 ($S_{\text{price}}$):** 상태 조정 이익률 1%당 2.0점 반영 (최대 $\pm 30$점 클램핑)
   $$S_{\text{price}} = \text{clamp}(-30.0, 30.0, \text{Adjusted Advantage \%} \times 2.0)$$
2. **주행거리 매력도 점수 ($S_{\text{mileage}}$):** 표본 중앙값 대비 우위 시 최대 $\pm 10$점
   $$S_{\text{mileage}} = \text{clamp}\left(-10.0, 10.0, \frac{\text{Median Mileage} - \text{Target Mileage}}{10,000} \times 5.0\right)$$
3. **성능점검 및 무사고 가점 ($S_{\text{condition}}$):**
   - 공인 성능점검기록부 교부 확인 시: $+5.0$점
   - 완전 무사고: $+5.0$점
   - 단순 교환: $-3.0$점
   - 주요 골격 손상: $-15.0$점
4. **가격 인하 모멘텀 ($S_{\text{momentum}}$):**
   - 최근 관측 스냅샷 대비 가격 인하 이력 관측 시: $+5.0$점

### 3) 데이터 신뢰도(Confidence) 가중치 보정
- **HIGH** (성능점검부 완비, 사고상태 명확, 전 제원 완비): 가중치 $1.0$ (감점 없음)
- **MEDIUM** (기본 제원 정상, 세부 트림/옵션 일부 누락): 가중치 $0.95$ ($5\%$ 감점)
- **LOW** (성능점검부 누락 또는 사고상태 미상): 가중치 $0.85$ ($15\%$ 감점)

$$\text{Final Opportunity Score} = \text{clamp}(0.0, 100.0, \text{Raw Score} \times \text{Confidence Weight})$$

---

## 5. 알고리즘의 한계점 및 주의사항 (Limitations)

1. **허위/미끼 매물 왜곡 위험:**
   - 온라인 플랫폼에 고의로 시세보다 현저히 낮게 등록된 미끼 매물의 경우 점수가 비정상적으로 높게 산출될 수 있습니다. (추후 파트너 딜러의 실차 전산 검증 필수)
2. **개별 추가 옵션 가치 미반영:**
   - 썬루프, 빌트인캠, 첨단 운전자 보조 패키지(ADAS) 등 수백만 원 상당의 유상 옵션 유무가 세부 트림명에 명시되지 않은 경우 가치 보정에서 누락될 수 있습니다.
3. **실차 미세 결함 및 성능 상태:**
   - 엔진 미세누유, 하부 부식, 실내 흡연 냄새, 타이어 마모도 등 성능점검표 외 물리적 컨디션은 알고리즘이 관측하지 못하므로 딜러 현장 점검이 병행되어야 합니다.
