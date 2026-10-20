# 🚘 CHA-FICIAL (차피셜) AI
## 한국형 중고차 시장 데이터 엔진 V0.1
### Korean Used Car Market Intelligence Foundation (PHASE 1)

차피셜(CHA-FICIAL)은 대한민국 전국 중고차 시장의 매물 및 가격 데이터를 분석하여 판매 가능성이 높은 꿀매물을 발굴하고, 광고 의사결정과 실제 영업 성과(문의, 계약, 정산 순수익)를 추적·학습하여 장기적인 사업 수익을 극대화하는 중고차 전문 AI 시스템입니다.

---

### 1. 핵심 아키텍처 및 원칙

- **전국 시장 분석과 판매 대상 지역 분리**:
  - `MARKET_ANALYSIS_REGION`: 전국(NATIONWIDE) 매물, 시세, 가격 인하 및 공급 흐름 분석
  - `SALES_TARGET_REGION`: 서울 장안평 중고차 시장(초기 기본) 등 실무 파트너 영업 가능 매물 선별 (수원, 인천, 부천 확장 지원)
  - `CUSTOMER_TARGET_REGION`: 캠페인별 고객 타겟 권역
- **실무 전문 파트너 중심 설계**:
  - 서울 장안평 25년 경력 중고차 전문 딜러 파트너십 기반
  - 업계의 공동 매물 알선 영업 관행을 반영하되, 사진/영상 재사용 등 법적 광고 권한을 독립 검증
- **시계열 정보 보존 및 데이터 누출(Data Leakage) 차단**:
  - 과거 시점 조회 시 `observed_at <= T` AND `ingested_at <= T` 엄격 적용
  - 가격 변경 시 과거 스냅샷 불변 보존(Append-only)
- **실제 판매와 매물 삭제 구분**:
  - `DELISTED_UNKNOWN`(단순 매물 삭제)와 `SOLD_CONFIRMED`(계약 확인 완료)의 엄격한 분리
- **공급 조건과 확정 순수익 분리**:
  - 이론적 마진이 아닌, 확인된 계약 정산액에서 마케팅비·제작비 등을 차감한 `Net Profit` 보상 모델

---

### 2. 기술 스택

- **언어 및 패키지 관리**: Python 3.12, `uv`
- **데이터베이스 & ORM**: SQLite (In-Memory / File), SQLAlchemy 2.x
- **테스트 & 린팅**: `pytest`, `ruff`

---

### 3. 설치 및 실행 방법

#### 1) 의존성 설치
```bash
uv sync
```

#### 2) 단위 및 통합 테스트 실행 (20대 핵심 테스트 + 무결성 제약)
```bash
uv run pytest -v
```

#### 3) 코드 품질 검사 (Ruff)
```bash
uv run ruff check .
```

#### 4) 가상 데이터 생성 데모 실행
```bash
uv run python -m chaficial.synthetic.generator
```

---

### 4. 디렉터리 구조

```text
cha-ficial/
├── pyproject.toml              # 프로젝트 명세 및 의존성 설정
├── README.md                   # 프로젝트 개요 및 실행 매뉴얼
├── configs/
│   └── regions.yaml            # 전국 분석 및 판매 대상 시장권역 설정
├── src/
│   └── chaficial/
│       ├── database/           # DB 엔진 및 세션 팩토리
│       ├── models/             # 카탈로그, 매물, 스냅샷, 파트너, 의사결정 등 14종 엔티티
│       ├── regions/            # 지역 정규화 및 장안평 필터 매니저
│       ├── time_travel/        # 미래 정보 누출 방지 시계열 쿼리 엔진
│       └── synthetic/          # 100건 이상 한국형 가상 매물 데이터 생성기
└── tests/
    ├── conftest.py             # 테스트 fixture (DB 세션, 시드 데이터)
    └── test_directive_002_all.py # DIRECTIVE 002 필수 테스트 20선 및 무결성 검증
```
