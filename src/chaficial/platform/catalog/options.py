"""표준 옵션 마스터 카탈로그 및 플랫폼별 코드 매핑 (DIRECTIVE 088 / 현대화 각색 반영).

엔카 및 차피셜 표준 4대 분류 체계:
1. EXTERIOR_INTERIOR (외관·내장)
2. SAFETY (안전)
3. CONVENIENCE_MULTIMEDIA (편의·멀티미디어)
4. SEAT (시트)
+ 10대 핵심 주요 옵션 (TOP 10)

※ 2026년 기준 사장된 구시대 옵션(CD플레이어, AUX단자, 파워윈도우, 파워도어록 등)은 제거하고,
  소비자가 실제로 중고차 선택 시 필수 확인하는 현대적 사양(무선충전, 카플레이/안드로이드오토,
  스마트크루즈, 서라운드뷰, C타입 USB, 앰비언트 등)으로 각색 구축.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class StandardOptionDef:
    code: str
    name: str
    category: str  # EXTERIOR_INTERIOR, SAFETY, CONVENIENCE_MULTIMEDIA, SEAT
    description: str
    is_top10: bool = False  # 고객 상세 10대 핵심 요약 아이콘 표시 여부
    icon: str = "check"     # Lucide / SVG 아이콘 식별자
    is_common: bool = True  # 관리자 우선 노출 여부
    encar_code: str | None = None
    kb_code: str | None = None
    carmanager_code: str | None = None
    keywords: list[str] = None  # 자동 판정 키워드

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = [self.name]


class StandardOptionCatalog:
    """차마트 현대형 표준 옵션 사전 및 플랫폼 매핑."""

    # 고객 상세 페이지 상단 10대 주요 옵션 공식 코드 순서
    TOP_10_CODES = [
        "OPT_SUNROOF",          # 1. 선루프
        "OPT_HUD",              # 2. 헤드업 디스플레이 (HUD)
        "OPT_PARKING_SENSOR",   # 3. 주차감지센서 (전/후방)
        "OPT_REAR_CAMERA",      # 4. 후방카메라
        "OPT_AUTO_AC",          # 5. 자동 에어컨
        "OPT_SMART_KEY",        # 6. 스마트키
        "OPT_GENUINE_NAVI",     # 7. 내비게이션
        "OPT_HEATED_SEAT",      # 8. 열선시트
        "OPT_VENTILATED_SEAT",  # 9. 통풍시트
        "OPT_LEATHER_SEATS",    # 10. 가죽시트
    ]

    OPTIONS: list[StandardOptionDef] = [
        # ========================================================
        # 1. 외관·내장 (EXTERIOR_INTERIOR) - 13개 항목
        # ========================================================
        StandardOptionDef(
            "OPT_SUNROOF", "선루프 (파노라마/일반)", "EXTERIOR_INTERIOR",
            "개방감을 주는 파노라마 또는 전동 선루프", is_top10=True, icon="sun",
            encar_code="SUNROOF", kb_code="KB_EXT_01", carmanager_code="CM_SUNROOF",
            keywords=["선루프", "파노라마", "루프탑"]
        ),
        StandardOptionDef(
            "OPT_LED_HEADLAMP", "LED 헤드램프 & 주간주행등", "EXTERIOR_INTERIOR",
            "Full LED 헤드램프 및 LED 주간주행등(DRL)", is_top10=False, icon="zap",
            encar_code="LED_HEADLIGHT", kb_code="KB_EXT_02", carmanager_code="CM_LED_LAMP",
            keywords=["LED", "HID", "프로젝션", "헤드램프", "데이라이트"]
        ),
        StandardOptionDef(
            "OPT_POWER_TRUNK", "스마트 파워 전동 트렁크", "EXTERIOR_INTERIOR",
            "버튼/스마트키/센서로 자동 개폐되는 전동 트렁크", is_top10=False, icon="arrow-up-circle",
            encar_code="POWER_TRUNK", kb_code="KB_CONV_03", carmanager_code="CM_PWR_TRUNK",
            keywords=["전동트렁크", "파워트렁크", "스마트테일게이트", "테일게이트"]
        ),
        StandardOptionDef(
            "OPT_POWER_FOLD_MIRROR", "전동접이 사이드미러 (락폴딩)", "EXTERIOR_INTERIOR",
            "도어 잠금 시 자동 접힘 및 전동 각도 조절", is_top10=False, icon="move-horizontal",
            encar_code="POWER_MIRROR", kb_code="KB_EXT_04", carmanager_code="CM_MIRROR",
            keywords=["사이드미러", "전동접이", "락폴딩", "미러"]
        ),
        StandardOptionDef(
            "OPT_ALUMINUM_WHEEL", "알루미늄 휠 (17~21인치)", "EXTERIOR_INTERIOR",
            "순정 대구경 프리미엄 알로이 휠", is_top10=False, icon="circle-dot",
            encar_code="AL_WHEEL", kb_code="KB_EXT_03", carmanager_code="CM_AL_WHEEL",
            keywords=["알루미늄", "알로이", "휠", "18인치", "19인치", "20인치", "21인치"]
        ),
        StandardOptionDef(
            "OPT_ROOF_RACK", "루프랙", "EXTERIOR_INTERIOR",
            "SUV/RV 차체 루프 캐리어 장착용 레일", is_top10=False, icon="grip-horizontal",
            encar_code="ROOF_RACK", kb_code="KB_EXT_05", carmanager_code="CM_ROOFRACK",
            keywords=["루프랙", "루프레일", "캐리어"]
        ),
        StandardOptionDef(
            "OPT_HEATED_STEERING", "열선 스티어링 휠", "EXTERIOR_INTERIOR",
            "겨울철 스티어링 휠 핸들 온열 기능", is_top10=False, icon="flame",
            encar_code="HEAT_STEER", kb_code="KB_INT_01", carmanager_code="CM_HEAT_STR",
            keywords=["열선핸들", "열선 스티어링", "핸들열선"]
        ),
        StandardOptionDef(
            "OPT_TILT_STEERING", "전동 조절 스티어링 휠", "EXTERIOR_INTERIOR",
            "전동식 틸트 및 텔레스코픽 핸들 조절", is_top10=False, icon="move",
            encar_code="ELEC_STEER", kb_code="KB_INT_05", carmanager_code="CM_PWR_STR",
            keywords=["전동조절핸들", "전동 스티어링", "틸트", "텔레스코픽"]
        ),
        StandardOptionDef(
            "OPT_PADDLE_SHIFT", "패들 시프트", "EXTERIOR_INTERIOR",
            "스티어링 휠 수동 기어 변속 패들 레버", is_top10=False, icon="sliders",
            encar_code="PADDLE_SHIFT", kb_code="KB_INT_02", carmanager_code="CM_PADDLE",
            keywords=["패들시프트", "패들", "시프트패들"]
        ),
        StandardOptionDef(
            "OPT_STEERING_REMOTE", "스티어링 휠 리모컨", "EXTERIOR_INTERIOR",
            "오디오/통화/주행제어 핸들 통합 버튼", is_top10=False, icon="disc",
            encar_code="STEER_REMOTE", kb_code="KB_INT_06", carmanager_code="CM_STR_REM",
            keywords=["핸들리모컨", "스티어링리모컨"]
        ),
        StandardOptionDef(
            "OPT_AMBIENT_LIGHT", "앰비언트 라이트 (실내 무드램프)", "EXTERIOR_INTERIOR",
            "64색 인터랙티브 실내 감성 무드 조명", is_top10=False, icon="sparkles",
            encar_code="AMBIENT", kb_code="KB_INT_07", carmanager_code="CM_AMBIENT",
            keywords=["앰비언트", "무드램프", "무드등"]
        ),
        StandardOptionDef(
            "OPT_ECM_ROOM_MIRROR", "ECM 전자식 룸미러", "EXTERIOR_INTERIOR",
            "야간 후방 차량 전조등 눈부심 자동 방지", is_top10=False, icon="eye",
            encar_code="ECM_MIRROR", kb_code="KB_INT_08", carmanager_code="CM_ECM",
            keywords=["ECM", "눈부심방지"]
        ),
        StandardOptionDef(
            "OPT_GHOST_DOOR", "고스트 도어 클로징 (소프트 클로징)", "EXTERIOR_INTERIOR",
            "덜 닫힌 도어를 모터가 부드럽게 자동 압축 흡착", is_top10=False, icon="shield-check",
            encar_code="GHOST_DOOR", kb_code="KB_EXT_06", carmanager_code="CM_GHOST_DR",
            keywords=["고스트도어", "소프트클로징", "압축도어"]
        ),

        # ========================================================
        # 2. 안전 (SAFETY) - 12개 항목
        # ========================================================
        StandardOptionDef(
            "OPT_PARKING_SENSOR", "주차감지센서 (전방/후방)", "SAFETY",
            "전방 및 후방 초음파 장애물 감지 경보", is_top10=True, icon="radar",
            encar_code="PARKING_SENSOR", kb_code="KB_SAF_05", carmanager_code="CM_PARK_SENS",
            keywords=["주차감지", "센서", "전방감지", "후방감지", "전후방센서"]
        ),
        StandardOptionDef(
            "OPT_REAR_CAMERA", "후방카메라 (조향 연동 가이드)", "SAFETY",
            "후진 시 스티어링 궤적 연동 디스플레이 표시", is_top10=True, icon="camera",
            encar_code="REAR_CAM", kb_code="KB_SAF_06", carmanager_code="CM_REAR_CAM",
            keywords=["후방카메라", "후방 캠", "조향가이드"]
        ),
        StandardOptionDef(
            "OPT_SURROUND_VIEW", "360도 어라운드 뷰 (서라운드 뷰)", "SAFETY",
            "차량 주변을 하늘에서 내려다보듯 360도 표시", is_top10=False, icon="eye",
            encar_code="AVM_360", kb_code="KB_SAF_07", carmanager_code="CM_AVM",
            keywords=["어라운드뷰", "서라운드뷰", "360", "서라운드", "어라운드"]
        ),
        StandardOptionDef(
            "OPT_AIRBAG_FRONT", "에어백 (운전석, 동승석)", "SAFETY",
            "충돌 시 전방 승객 보호 듀얼 에어백", is_top10=False, icon="shield",
            encar_code="AIRBAG_FRONT", kb_code="KB_SAF_01", carmanager_code="CM_AIRBAG_FR",
            keywords=["에어백", "운전석에어백", "동승석에어백"]
        ),
        StandardOptionDef(
            "OPT_AIRBAG_SIDE_CURTAIN", "사이드 & 커튼 에어백", "SAFETY",
            "측면 충돌 및 전복 시 승객 머리/상체 보호", is_top10=False, icon="shield-alert",
            encar_code="AIRBAG_SIDE", kb_code="KB_SAF_02", carmanager_code="CM_AIRBAG_SC",
            keywords=["사이드에어백", "커튼에어백", "사이드"]
        ),
        StandardOptionDef(
            "OPT_ABS_ESC_TCS", "ABS / ESC (차체자세제어장치) / TCS", "SAFETY",
            "급제동 미끄럼 방지 및 능동적 자세 제어 안전장치", is_top10=False, icon="activity",
            encar_code="ESC_SYSTEM", kb_code="KB_SAF_03", carmanager_code="CM_ESC",
            keywords=["ABS", "ESC", "TCS", "차체자세", "미끄럼방지"]
        ),
        StandardOptionDef(
            "OPT_TPMS", "타이어 공기압 경보 (TPMS)", "SAFETY",
            "각 타이어의 실시간 공기압 모니터링", is_top10=False, icon="gauge",
            encar_code="TPMS", kb_code="KB_SAF_04", carmanager_code="CM_TPMS",
            keywords=["TPMS", "공기압", "타이어공기압"]
        ),
        StandardOptionDef(
            "OPT_LANE_ASSIST", "차로 이탈방지 / 차로 유지 보조 (LKA/LFA)", "SAFETY",
            "주행 차선을 인식하여 스티어링 능동 제어", is_top10=False, icon="git-commit",
            encar_code="LDWS", kb_code="KB_ADAS_01", carmanager_code="CM_LANE_AST",
            keywords=["차선이탈", "차로유지", "LKA", "LFA", "차선"]
        ),
        StandardOptionDef(
            "OPT_FORWARD_COLLISION", "전방 충돌방지 보조 (FCA)", "SAFETY",
            "차량·보행자 감지 후 긴급 자동 제동", is_top10=False, icon="alert-triangle",
            encar_code="FCA_SYSTEM", kb_code="KB_ADAS_02", carmanager_code="CM_FCA",
            keywords=["전방충돌", "긴급제동", "FCA", "충돌방지"]
        ),
        StandardOptionDef(
            "OPT_BLIND_SPOT", "후측방 충돌방지 보조 / 경보 (BCA/BSD)", "SAFETY",
            "사각지대 접근 차량 감지 및 경고·회피 보조", is_top10=False, icon="scan",
            encar_code="BSD_SYSTEM", kb_code="KB_ADAS_03", carmanager_code="CM_BSD",
            keywords=["후측방", "사각지대", "BSD", "BCA", "측후방"]
        ),
        StandardOptionDef(
            "OPT_ELEC_SUSPENSION", "전자제어 서스펜션 (ECS)", "SAFETY",
            "노면 상태에 따라 감쇠력을 실시간 전자 제어", is_top10=False, icon="layers",
            encar_code="ECS_SUSP", kb_code="KB_SAF_08", carmanager_code="CM_ECS",
            keywords=["전자제어서스펜션", "에어서스", "서스펜션", "ECS"]
        ),
        StandardOptionDef(
            "OPT_REMOTE_PARKING", "원격 스마트 주차 보조 (RSPA)", "SAFETY",
            "차량 외부에서 스마트키 버튼으로 원격 주차/출차", is_top10=False, icon="smartphone",
            encar_code="RSPA_PARK", kb_code="KB_ADAS_04", carmanager_code="CM_RSPA",
            keywords=["원격주차", "RSPA", "원격스마트주차"]
        ),

        # ========================================================
        # 3. 편의·멀티미디어 (CONVENIENCE_MULTIMEDIA) - 15개 항목
        # ========================================================
        StandardOptionDef(
            "OPT_HUD", "헤드업 디스플레이 (HUD)", "CONVENIENCE_MULTIMEDIA",
            "전면 앞유리 컬러 그래픽 주행 정보 투영", is_top10=True, icon="tv",
            encar_code="HUD", kb_code="KB_ADAS_05", carmanager_code="CM_HUD",
            keywords=["HUD", "헤드업", "헤드업디스플레이"]
        ),
        StandardOptionDef(
            "OPT_AUTO_AC", "자동 에어컨 (풀오토 듀얼 에어컨)", "CONVENIENCE_MULTIMEDIA",
            "좌우 독립 온도 제어 및 오토 디포그", is_top10=True, icon="fan",
            encar_code="AUTO_AC", kb_code="KB_CONV_01", carmanager_code="CM_FATC",
            keywords=["에어컨", "풀오토", "오토에어컨", "듀얼에어컨", "자동에어컨"]
        ),
        StandardOptionDef(
            "OPT_SMART_KEY", "스마트키 & 버튼 시동 / 원격 시동", "CONVENIENCE_MULTIMEDIA",
            "키 소지만으로 도어 오픈 및 버튼/원격 시동", is_top10=True, icon="key",
            encar_code="SMART_KEY", kb_code="KB_CONV_02", carmanager_code="CM_SMART_KEY",
            keywords=["스마트키", "버튼시동", "원격시동"]
        ),
        StandardOptionDef(
            "OPT_GENUINE_NAVI", "와이드 디스플레이 내비게이션", "CONVENIENCE_MULTIMEDIA",
            "10.25~14.5인치 순정 고화질 와이드 내비게이션", is_top10=True, icon="navigation",
            encar_code="GENUINE_NAVI", kb_code="KB_MEDIA_01", carmanager_code="CM_ORIG_NAVI",
            keywords=["내비게이션", "네비", "내비", "순정내비"]
        ),
        StandardOptionDef(
            "OPT_SMART_CRUISE", "스마트 크루즈 컨트롤 (어댑티브 / 정차&재출발)", "CONVENIENCE_MULTIMEDIA",
            "앞차와의 거리를 계산하여 가감속 및 정차 지원", is_top10=False, icon="compass",
            encar_code="SMART_CRUISE", kb_code="KB_ADAS_06", carmanager_code="CM_SCC",
            keywords=["스마트크루즈", "어댑티브", "크루즈", "SCC", "ASCC"]
        ),
        StandardOptionDef(
            "OPT_HDA", "고속도로 주행 보조 (HDA / HDA2)", "CONVENIENCE_MULTIMEDIA",
            "내비게이션 연동 고속도로 반자율 곡선·속도 감속", is_top10=False, icon="navigation-2",
            encar_code="HDA_SYSTEM", kb_code="KB_ADAS_07", carmanager_code="CM_HDA",
            keywords=["HDA", "고속도로주행보조", "HDA2"]
        ),
        StandardOptionDef(
            "OPT_AUTO_HOLD", "전자식 주차브레이크 (EPB & 오토홀드)", "CONVENIENCE_MULTIMEDIA",
            "신호 대기 시 브레이크 페달을 떼어도 정지 유지", is_top10=False, icon="pause-circle",
            encar_code="EPB_AUTOHOLD", kb_code="KB_CONV_05", carmanager_code="CM_EPB",
            keywords=["EPB", "전자식파킹", "오토홀드", "파킹브레이크"]
        ),
        StandardOptionDef(
            "OPT_CARPLAY_AA", "애플 카플레이 / 안드로이드 오토 (폰 프로젝션)", "CONVENIENCE_MULTIMEDIA",
            "티맵, 카카오내비, 유튜브뮤직 스마트폰 미러링 연동", is_top10=False, icon="smartphone",
            encar_code="PHONE_PROJ", kb_code="KB_MEDIA_03", carmanager_code="CM_CARPLAY",
            keywords=["카플레이", "안드로이드오토", "폰프로젝션", "티맵"]
        ),
        StandardOptionDef(
            "OPT_WIRELESS_CHARGER", "스마트폰 무선 충전 패드", "CONVENIENCE_MULTIMEDIA",
            "콘솔 거치 시 고속 무선 충전 기능", is_top10=False, icon="battery-charging",
            encar_code="WIRELESS_CHG", kb_code="KB_CONV_04", carmanager_code="CM_WIRELESS",
            keywords=["무선충전", "무선 충전", "스마트폰무선충전"]
        ),
        StandardOptionDef(
            "OPT_DIGITAL_KEY", "디지털 키 (스마트폰 키)", "CONVENIENCE_MULTIMEDIA",
            "스마트폰 또는 NFC 카드키로 문 열림 및 시동", is_top10=False, icon="credit-card",
            encar_code="DIGITAL_KEY", kb_code="KB_CONV_08", carmanager_code="CM_DIGITAL_KEY",
            keywords=["디지털키", "카드키", "NFC"]
        ),
        StandardOptionDef(
            "OPT_HIPASS", "하이패스 시스템 (내장형/룸미러)", "CONVENIENCE_MULTIMEDIA",
            "고속도로 톨게이트 자동 결제 하이패스 단말기", is_top10=False, icon="tag",
            encar_code="HIPASS", kb_code="KB_CONV_07", carmanager_code="CM_HIPASS",
            keywords=["하이패스", "통행료"]
        ),
        StandardOptionDef(
            "OPT_RAIN_SENSOR", "레인센서 (우적감지 와이퍼)", "CONVENIENCE_MULTIMEDIA",
            "비의 양을 스스로 감지하여 와이퍼 속도 자동 조절", is_top10=False, icon="cloud-rain",
            encar_code="RAIN_SENSOR", kb_code="KB_CONV_06", carmanager_code="CM_RAIN_SENS",
            keywords=["레인센서", "우적감지", "와이퍼"]
        ),
        StandardOptionDef(
            "OPT_AUTO_LIGHT", "오토 라이트 컨트롤", "CONVENIENCE_MULTIMEDIA",
            "주변 조도를 감지해 터널 및 야간 시 자동 전조등 점등", is_top10=False, icon="sun-medium",
            encar_code="AUTO_LIGHT", kb_code="KB_CONV_09", carmanager_code="CM_AUTO_LIGHT",
            keywords=["오토라이트", "오토 헤드램프"]
        ),
        StandardOptionDef(
            "OPT_PREMIUM_AUDIO", "프리미엄 사운드 시스템 (크렐/보스/하만카돈/B&O)", "CONVENIENCE_MULTIMEDIA",
            "서브우퍼 및 고음질 프리미엄 앰프 사운드 시스템", is_top10=False, icon="volume-2",
            encar_code="PREMIUM_SOUND", kb_code="KB_MEDIA_02", carmanager_code="CM_SOUND",
            keywords=["크렐", "보스", "하만카돈", "뱅앤올룹슨", "사운드", "스피커", "JBL", "렉시콘", "메리디안"]
        ),
        StandardOptionDef(
            "OPT_SUN_CURTAIN", "뒷좌석 / 후방 선커튼 (수동/전동)", "CONVENIENCE_MULTIMEDIA",
            "2열 승객 프라이버시 보호 및 자외선 차단 블라인드", is_top10=False, icon="columns",
            encar_code="SUN_CURTAIN", kb_code="KB_CONV_10", carmanager_code="CM_CURTAIN",
            keywords=["커튼", "선커튼", "블라인드", "선블라인드"]
        ),

        # ========================================================
        # 4. 시트 (SEAT) - 10개 항목
        # ========================================================
        StandardOptionDef(
            "OPT_LEATHER_SEATS", "가죽시트 (천연 / 나파 / 퀼팅)", "SEAT",
            "최고급 천연가죽 또는 나파가죽 프리미엄 시트", is_top10=True, icon="armchair",
            encar_code="LEATHER_SEAT", kb_code="KB_SEAT_01", carmanager_code="CM_LEATHER",
            keywords=["가죽시트", "가죽", "나파", "천연가죽"]
        ),
        StandardOptionDef(
            "OPT_HEATED_SEAT_FRONT", "열선시트 (앞좌석)", "SEAT",
            "운전석 및 동승석 1열 온열 시트", is_top10=True, icon="flame",
            encar_code="HEAT_SEAT", kb_code="KB_SEAT_04", carmanager_code="CM_HEAT_ST",
            keywords=["열선시트", "열선", "앞좌석열선"]
        ),
        StandardOptionDef(
            "OPT_HEATED_SEAT_REAR", "열선시트 (뒷좌석)", "SEAT",
            "2열 뒷좌석 승객용 온열 시트", is_top10=False, icon="flame",
            encar_code="HEAT_SEAT_REAR", kb_code="KB_SEAT_08", carmanager_code="CM_HEAT_RR",
            keywords=["뒷좌석열선", "2열열선", "후석열선"]
        ),
        StandardOptionDef(
            "OPT_VENTILATED_SEAT_FRONT", "통풍시트 (앞좌석)", "SEAT",
            "운전석 및 동승석 1열 시원한 바람 송풍 시트", is_top10=True, icon="wind",
            encar_code="COOL_SEAT", kb_code="KB_SEAT_03", carmanager_code="CM_VENT_ST",
            keywords=["통풍시트", "통풍", "앞좌석통풍"]
        ),
        StandardOptionDef(
            "OPT_VENTILATED_SEAT_REAR", "통풍시트 (뒷좌석)", "SEAT",
            "2열 뒷좌석 승객용 쿨링 송풍 시트", is_top10=False, icon="wind",
            encar_code="COOL_SEAT_REAR", kb_code="KB_SEAT_09", carmanager_code="CM_VENT_RR",
            keywords=["뒷좌석통풍", "2열통풍", "후석통풍"]
        ),
        StandardOptionDef(
            "OPT_POWER_SEAT_DRV", "운전석 전동시트 & 럼버서포트", "SEAT",
            "운전석 파워 시트 및 전동 요추 받침대", is_top10=False, icon="user-check",
            encar_code="POWER_SEAT_DRV", kb_code="KB_SEAT_02", carmanager_code="CM_PWR_DRV",
            keywords=["운전석전동시트", "전동시트", "요추받침"]
        ),
        StandardOptionDef(
            "OPT_POWER_SEAT_PASS", "동승석 전동시트 & 워크인 디바이스", "SEAT",
            "동승석 전동 조절 및 운전석/뒷좌석 조작 워크인 스위치", is_top10=False, icon="users",
            encar_code="POWER_SEAT_PASS", kb_code="KB_SEAT_05", carmanager_code="CM_PWR_PASS",
            keywords=["동승석전동시트", "동승석전동", "워크인", "릴렉션"]
        ),
        StandardOptionDef(
            "OPT_MEMORY_SEAT", "운전석 자세 메모리 시스템 (IMS)", "SEAT",
            "시트, 사이드미러, 스티어링 휠 위치 원터치 기억 복원", is_top10=False, icon="bookmark",
            encar_code="MEMORY_SEAT", kb_code="KB_SEAT_06", carmanager_code="CM_IMS",
            keywords=["메모리시트", "메모리", "IMS"]
        ),
        StandardOptionDef(
            "OPT_POWER_SEAT_REAR", "뒷좌석 전동 리클라이닝 시트", "SEAT",
            "2열 VIP 전동 각도 조절 시트", is_top10=False, icon="user-plus",
            encar_code="POWER_SEAT_REAR", kb_code="KB_SEAT_10", carmanager_code="CM_PWR_RR",
            keywords=["뒷좌석전동시트", "후석전동", "2열전동", "리클라이닝"]
        ),
        StandardOptionDef(
            "OPT_MASSAGE_SEAT", "마사지 시트 (에르고 모션 스트레칭)", "SEAT",
            "공기주머니를 통한 운전자 골반/허리 피로 완화 스트레칭", is_top10=False, icon="sparkles",
            encar_code="MASSAGE_SEAT", kb_code="KB_SEAT_07", carmanager_code="CM_MASSAGE",
            keywords=["마사지시트", "에르고모션", "마사지"]
        ),
    ]

    CATEGORY_LABELS = {
        "EXTERIOR_INTERIOR": "외관·내장",
        "SAFETY": "안전",
        "CONVENIENCE_MULTIMEDIA": "편의·멀티미디어",
        "SEAT": "시트",
    }

    @classmethod
    def list_options(cls, category: str | None = None) -> list[dict[str, Any]]:
        """전체 표준 옵션 목록 또는 카테고리별 필터 목록 반환."""
        res = []
        for opt in cls.OPTIONS:
            if category and opt.category != category:
                continue
            item = asdict(opt)
            item["category_label"] = cls.CATEGORY_LABELS.get(opt.category, opt.category)
            res.append(item)
        return res

    @classmethod
    def get_by_code(cls, code: str) -> StandardOptionDef | None:
        """옵션 코드로 조회."""
        for opt in cls.OPTIONS:
            if opt.code == code:
                return opt
        return None

    @classmethod
    def get_top10_options(cls) -> list[dict[str, Any]]:
        """고객 상세 페이지용 10대 핵심 주요 옵션 정의 목록."""
        top_map = {opt.code: asdict(opt) for opt in cls.OPTIONS if opt.code in cls.TOP_10_CODES}
        # TOP_10_CODES 중 SEAT 쪽에서 OPT_HEATED_SEAT_FRONT, OPT_VENTILATED_SEAT_FRONT 매핑 호환
        code_alias = {
            "OPT_HEATED_SEAT": "OPT_HEATED_SEAT_FRONT",
            "OPT_VENTILATED_SEAT": "OPT_VENTILATED_SEAT_FRONT"
        }
        ordered = []
        for code in cls.TOP_10_CODES:
            real_code = code_alias.get(code, code)
            target = top_map.get(code) or {asdict(o)["code"]: asdict(o) for o in cls.OPTIONS}.get(real_code)
            if target:
                target["category_label"] = cls.CATEGORY_LABELS.get(target["category"], target["category"])
                ordered.append(target)
        return ordered

    @classmethod
    def get_categories(cls) -> list[dict[str, str]]:
        """옵션 4대 카테고리 키 및 한글 라벨."""
        return [
            {"key": "EXTERIOR_INTERIOR", "label": "외관·내장"},
            {"key": "SAFETY", "label": "안전"},
            {"key": "CONVENIENCE_MULTIMEDIA", "label": "편의·멀티미디어"},
            {"key": "SEAT", "label": "시트"},
        ]
