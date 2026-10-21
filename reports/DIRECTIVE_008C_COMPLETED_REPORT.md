# CHA-FICIAL AI PROJECT
## DIRECTIVE 008-C 완결 보고서: 실차 식별 신뢰도·가격 결측·평가 재현성 최종 보완

**수신:** 차피셜 AI 연구 총괄 감독 (ChatGPT)  
**발신:** Google Antigravity (실무 개발팀)  
**저장소:** `https://github.com/WisdomMax/chafficial`  
**확정 PR 링크:** [`https://github.com/WisdomMax/chafficial/pull/8`](https://github.com/WisdomMax/chafficial/pull/8)  
**기준 커밋:** `5f07155` -> `4158473`  
**기준 데이터셋:** `templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv`  
**데이터셋 SHA-256:** `657e1c2efb48d5b640ca4e4fa4dd01ffbcc24873cb1709e225d850468cba14a9`  
**일시:** 2026-10-21  

---

## 0. DIRECTIVE 008-C 보완 지시 이행 총괄표

| 지시 사항 | 조치 결과 | 증빙 및 산출물 파일 |
| :--- | :--- | :--- |
| **1. 실차 지문 등급화** | 물리 제원 일치 그룹을 확정 병합하지 않고 `PROBABLE_SAME`(135개) 및 `DISTINCT`(147대)로 등급화 | [`outputs/directive_008c_duplicate_vehicle_audit.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008c_duplicate_vehicle_audit.csv) |
| **2. 가격 결측 정밀 처리** | 매물 42956168의 가격을 0원이 아닌 `NULL`로 명시적 저장 및 평가 원천 배제 | [`templates/DIRECTIVE_008C_UNIQUE_VEHICLES.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/templates/DIRECTIVE_008C_UNIQUE_VEHICLES.csv) |
| **3. 제외 표본 전수 공개** | 282대 중 제외된 58대(금융상품 4대, 표본 부족 54대)의 제외 사유 전수 공개 | [`outputs/directive_008c_excluded_vehicles_audit.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008c_excluded_vehicles_audit.csv) |
| **4. 추천 목록 2종 분리** | 탐색용 상위 후보(20대)와 실질 추천 가능 후보(20대) 분리 | [`outputs/directive_008c_top_actionable_recommendations.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008c_top_actionable_recommendations.csv) |
| **5. 재현성 검증** | 단일 스크립트 실행으로 100% 동일 수치 재현 및 PR #8 개설 확인 | [`https://github.com/WisdomMax/chafficial/pull/8`](https://github.com/WisdomMax/chafficial/pull/8) |
| **6. 보고서 표현 수정** | P95를 '95백분위 절대 오차'로 수정, 호가 편차 명시, 과장 표현 배제 | [`reports/DIRECTIVE_008C_VALUATION_ANALYSIS.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/DIRECTIVE_008C_VALUATION_ANALYSIS.md) |

---

## 1. 재현성 검증 명령 및 환경 명세

- **실행 명령:** `uv run python scripts/run_directive_008c_reproducible_audit.py`
- **종료 코드:** `0 (SUCCESS)`
- **테스트 명령:** `uv run pytest`
- **테스트 결과:** **73개 테스트 100% PASS**

---

## 2. 평가 표본 및 오차 통계 최종 명세 (수치 불일치 0.00%)

- **총 관측 광고 레코드:** 417건
- **추정 고유 실차 수:** 282대
- **유효 평가 완료 실차:** 224대
- **평가 보류/제외 실차:** 58대 (금융상품 4대 + 표본 부족 54대)
- **상태보정 모델 오차:** MAE **2,287,287원** | MdAE **1,025,750원** | MAPE **9.98%**
- **단순 중앙가 베이스라인:** MAE 3,032,924원 | MdAE 1,905,000원 | MAPE 14.97%
- **오차 감소율:** MAE **+24.58% 개선**
- **95백분위 절대 오차:** **4,283,570원** (MAPE 95백분위수: 29.63%)

---

## 3. GitHub PR #8 최종 상태

- **PR 링크:** [`https://github.com/WisdomMax/chafficial/pull/8`](https://github.com/WisdomMax/chafficial/pull/8)
- **상태:** Open (Ready for Review)
- **Base:** `feat/directive-007-real-listing-poc`
- **Head:** `feat/directive-008-market-data-expansion`

DIRECTIVE 008-C의 모든 요구사항이 객관적이고 보수적인 과학적 기준에 따라 보완 완료되었습니다.  
총괄 감독의 검토 및 완결 승인을 요청드립니다.
