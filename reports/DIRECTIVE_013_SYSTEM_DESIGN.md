# DIRECTIVE 013: 차피셜(CHA-FICIAL) 주기적 LIVE 시장 관측 운영체계 설계서

## 1. 개요 및 목적
- **목적**: 단발성 수집 실험을 넘어, 실시간 중고차 시장의 가격 변동과 매물 라이프사이클을 장기간 안정적으로 축적하는 자율 운영 관측 엔진 구축.
- **적용 대상 차종**: 현대 아반떼 CN7 전 트림 (이후 전 차종 확장 가능한 파이프라인 구조)
- **핵심 성공 기준**:
  1. 기존 348대 실매물 및 382건 스냅샷의 100% 영구 보존.
  2. 스케줄러 중복 실행 및 동일 배치 중복 기동 100% 원천 차단.
  3. 네트워크 장애 시 지수 백오프 기반 안전 재시도 및 무한 루프 방지.
  4. 매 수집 전 SQLite 온라인 백업 및 PRAGMA integrity_check 자동화.
  5. 일별 시장 요약 리포트(`reports/daily_summaries/`) 및 장애 격리 보고서(`reports/failures/`) 자동 발행.
  6. **안전 모드(Safety Guard)**: 총괄 감독의 별도 활성화 승인 전까지 무단 LIVE 스케줄링 방지 (`STANDBY`/`DRY_RUN` 기본 적용).

---

## 2. 시스템 아키텍처 및 핵심 모듈

```mermaid
flowchart TD
    Scheduler[ScheduledMarketWatcher<br/>주기적 관측 감시자] -->|1. fcntl 배타적 락| LockCheck{Scheduler Lock 획득?}
    LockCheck -->|실패| LockExit[중복 실행 즉시 차단 및 종료]
    LockCheck -->|성공| SafetyCheck{LIVE 플래그 활성화?}
    
    SafetyCheck -->|비활성 STANDBY| DryRunLog[대기 모드 기록 및 시뮬레이션]
    SafetyCheck -->|활성화| PreBackup[SQLite Online Backup API<br/>+ integrity_check]
    
    PreBackup --> CollectAttempt[엔카 모바일 웹 실시간 관측 시도]
    CollectAttempt -->|네트워크 실패| BackoffRetry{재시도 횟수 < 3?}
    BackoffRetry -->|Yes| WaitBackoff[지수 백오프 대기 후 재시도]
    WaitBackoff --> CollectAttempt
    BackoffRetry -->|No (최대 초과)| FailureReport[장애 보고서 생성 및 알림 로깅]
    
    CollectAttempt -->|성공| ParseValidation[아반떼 CN7 정밀 파싱<br/>비CN7 안전 격리]
    ParseValidation --> PipelineIngest[시계열 파이프라인 적재<br/>FIRST_SEEN / RE_OBSERVED / PRICE_DROP]
    
    PipelineIngest --> PostAudit[DB 해시 재계산 및 불변성 검증]
    PostAudit --> DailyReport[일별 시장 요약 리포트 자동 생성]
    DailyReport --> VoiceAlert[음성 알림 / 로컬 로깅]
```

---

## 3. 상세 컴포넌트 설계

### 3.1 주기적 수집 감시자 (`src/chaficial/tracker/scheduler.py`)
- **클래스명**: `MarketObservationScheduler`
- **설정 옵션 (`SchedulerConfig`)**:
  - `interval_seconds`: 관측 주기 (기본: 86400초 / 24시간, 테스트: 임의 초)
  - `scheduled_time_kst`: 지정 시각 실행 (예: "09:00 KST")
  - `max_retries`: 최대 재시도 횟수 (기본: 3회)
  - `backoff_factor`: 지수 백오프 배수 (기본: 2.0, 시작 5초 -> 10초 -> 20초)
  - `enable_live_execution`: 실제 LIVE 실행 허용 여부 (기본: False, 감독 승인 시만 True)
  - `lock_file_path`: 스케줄러 전용 락 파일 (`data/.scheduler.lock`)
  - `backup_dir`: 백업 디렉터리 (`data/backups/`)
  - `report_dir`: 일별 리포트 디렉터리 (`reports/daily_summaries/`)
  - `failure_dir`: 장애 리포트 디렉터리 (`reports/failures/`)

### 3.2 안전 재시도 및 실패 격리 정책
- 장애 유형:
  - `NetworkTimeout / HTTPError`: 네트워크 연결 실패
  - `ParseFailure`: 엔카 페이지 구조 변경 등
  - `OperationalLockError`: 다른 프로세스가 이미 관측 중
- 재시도 알고리즘:
  - 1회 실패: 5초 대기 후 2회 시도
  - 2회 실패: 10초 대기 후 3회 시도
  - 3회 실패: 최종 실패 처리 -> `FailureBatchReport` 자동 발행 (`reports/failures/failure_batch_...md`) -> 프로세스 안전 종료 (무한 루프 원천 차단)

### 3.3 일별 시장 리포터 (`src/chaficial/tracker/daily_reporter.py`)
- 일별 집계 지표:
  - 총 관측 배치 수
  - 총 수집 원천 카드 수 및 아반떼 CN7 정밀 파싱률
  - 시스템 최초 발견(`FIRST_SEEN` / `NEW_LISTING`) 건수
  - 재관측(`RE_OBSERVED`) 건수
  - 실제 가격 변동(`PRICE_DROP` / `PRICE_INCREASE`) 건수 및 금액 합계
  - 원본 JSON 해시 및 운영 DB 논리 SHA-256 해시 기록

---

## 4. 운영 원칙 및 제약 준수
1. **CPU 70% 미만 점유 (5% 수준 유지)**: 모든 대기 루프에 `time.sleep()`을 적용하여 CPU 낭비 방지.
2. **시계열 데이터 영구 보존**: 기존 348대 매물 및 382건 스냅샷의 물리적 수정·삭제 절대 금지.
3. **독립 테스트 스위트 구비**: 모의 웹 응답 및 장애 주입 테스트를 통해 LIVE 오염 없이 100% 안전하게 동작 검증.
