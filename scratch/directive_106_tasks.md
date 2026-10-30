# DIRECTIVE 106 세부 업무 분장 (P0 긴급 감사 이행)

TASK 1. 가격변경 137건 감사 및 복구
- 직전 run_daily_sync.py에서 기록된 price_changed 137건 전수 조사.
- 실제 카매니저 가격 변경 vs 만원/원 단위 변환 버그로 인한 가짜 변경 분리.
- DB 가격 컬럼(target_price, purchase_price, advertised_price) 순수 만원 단위 완전 복구 및 timeline_json 감사.

TASK 2. carmanager_sync.py 수집/동기화 엔진 근본 수정
- 가격 단위: 순수 만원 단위(Integer Manwon)로 완전 고정.
- 주행거리 파서: '5.5만 km' -> 55000, '55,000km' -> 55000, 파싱 불가 시 0 대신 NULL 유지.
- 차량번호: 전체 번호판이 없는 경우 plate_number = NULL, plate_tail 별도 컬럼 또는 비고 관리.
- 판매완료: 수집률 95% 이상 정상 완료 검증된 스냅샷에서만 미출현 카운트 증가. 3회 누락 시 DELISTED(광고중지), 실제 SOLD API/상세 확인 전에는 임의 판매완료 처리 금지.

TASK 3. 우리 상사 74대 vs 87대 차이 정밀 규명
- 74대 vs 87대의 고유 차량 ID 전수 대조.
- (주)더쿨모터스 실제 등록 차량, 개인 딜러 담당, 직영, 파트너, 타 상사 오분류 내역 명시.

TASK 4. 사진 500대 고화질 원본 3,183장(272.52MB) 정밀 검증
- 500대 encarno 폴더별 1024x768 해상도, 디코딩 무결성, SHA256 해시, DB 연결 상태 보고서 산출.

TASK 5. 독립 테스트 DB에서 10대 통제 실험 수행
- 10개 핵심 시나리오(단위, 잠금, 5.5만km, 번호판 누락, 멱등성 등) SQL 검증 통과.

TASK 6. 실시간 수집 파이프라인 결합 및 동기화 재가동
- scripts/run_daily_sync.py가 과거 JSON 파일이 아닌 실시간 카매니저 수집 데이터로 안전하게 동기화하도록 구현.

TASK 7. Git 커밋/푸시 및 ChatGPT 단일 탭 전송 보고
