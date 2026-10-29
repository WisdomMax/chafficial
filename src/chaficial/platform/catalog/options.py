"""표준 옵션 마스터 카탈로그 및 플랫폼별 코드 매핑 (DIRECTIVE 088 / DIRECTIVE 050).

엔카 및 차피셜 표준 4대 분류 체계:
1. EXTERIOR_INTERIOR (외관·내장)
2. SAFETY (안전)
3. CONVENIENCE_MULTIMEDIA (편의·멀티미디어)
4. SEAT (시트)
+ 10대 핵심 주요 옵션 (TOP 10)
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


class StandardOptionCatalog:
    """중고차 표준 옵션 사전 및 플랫폼 매핑."""

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
        # 1. 외관·내장 (EXTERIOR_INTERIOR)
        # ========================================================
        StandardOptionDef("OPT_SUNROOF", "선루프", "EXTERIOR_INTERIOR", "파노라마 또는 일반 전동 선루프", is_top10=True, icon="sun", is_common=True, encar_code="SUNROOF", kb_code="KB_EXT_01", carmanager_code="CM_SUNROOF"),
        StandardOptionDef("OPT_LED_HEADLAMP", "LED 헤드램프", "EXTERIOR_INTERIOR", "Full LED 헤드램프 및 주간주행등", is_top10=False, icon="zap", is_common=True, encar_code="LED_HEADLIGHT", kb_code="KB_EXT_02", carmanager_code="CM_LED_LAMP"),
        StandardOptionDef("OPT_POWER_FOLD_MIRROR", "전동접이 사이드미러", "EXTERIOR_INTERIOR", "전동 조절 및 락폴딩 아웃사이드 미러", is_top10=False, icon="move-horizontal", is_common=True, encar_code="POWER_MIRROR", kb_code="KB_EXT_04", carmanager_code="CM_MIRROR"),
        StandardOptionDef("OPT_ALUMINUM_WHEEL", "알루미늄 휠", "EXTERIOR_INTERIOR", "순정 17~21인치 알로이 휠", is_top10=False, icon="circle-dot", is_common=True, encar_code="AL_WHEEL", kb_code="KB_EXT_03", carmanager_code="CM_AL_WHEEL"),
        StandardOptionDef("OPT_HEATED_STEERING", "열선 스티어링 휠", "EXTERIOR_INTERIOR", "겨울철 핸들 온열 기능", is_top10=False, icon="flame", is_common=True, encar_code="HEAT_STEER", kb_code="KB_INT_01", carmanager_code="CM_HEAT_STR"),
        StandardOptionDef("OPT_PADDLE_SHIFT", "패들 시프트", "EXTERIOR_INTERIOR", "스티어링 휠 수동 변속 레버", is_top10=False, icon="sliders", is_common=False, encar_code="PADDLE_SHIFT", kb_code="KB_INT_02", carmanager_code="CM_PADDLE"),
        StandardOptionDef("OPT_POWER_TRUNK", "전동 트렁크", "EXTERIOR_INTERIOR", "스마트 파워 테일게이트", is_top10=False, icon="arrow-up-circle", is_common=True, encar_code="POWER_TRUNK", kb_code="KB_CONV_03", carmanager_code="CM_PWR_TRUNK"),
        StandardOptionDef("OPT_POWER_DOORLOCK", "파워 도어록", "EXTERIOR_INTERIOR", "전도어 중앙 집중식 도어 잠금장치", is_top10=False, icon="lock", is_common=True, encar_code="POWER_DOORLOCK", kb_code="KB_INT_03", carmanager_code="CM_DOORLOCK"),
        StandardOptionDef("OPT_POWER_WINDOW", "파워 윈도우", "EXTERIOR_INTERIOR", "전좌석 파워 윈도우 / 세이프티 윈도우", is_top10=False, icon="chevron-up", is_common=True, encar_code="POWER_WINDOW", kb_code="KB_INT_04", carmanager_code="CM_WINDOW"),
        StandardOptionDef("OPT_ROOF_RACK", "루프랙", "EXTERIOR_INTERIOR", "SUV/RV 차량 루프 캐리어 장착용 랙", is_top10=False, icon="grip-horizontal", is_common=False, encar_code="ROOF_RACK", kb_code="KB_EXT_05", carmanager_code="CM_ROOFRACK"),

        # ========================================================
        # 2. 안전 (SAFETY)
        # ========================================================
        StandardOptionDef("OPT_PARKING_SENSOR", "주차감지센서", "SAFETY", "전방/후방 장애물 감지 초음파 센서", is_top10=True, icon="radar", is_common=True, encar_code="PARKING_SENSOR", kb_code="KB_SAF_05", carmanager_code="CM_PARK_SENS"),
        StandardOptionDef("OPT_REAR_CAMERA", "후방카메라", "SAFETY", "후진 시 디스플레이 가이드라인 제공", is_top10=True, icon="camera", is_common=True, encar_code="REAR_CAM", kb_code="KB_SAF_06", carmanager_code="CM_REAR_CAM"),
        StandardOptionDef("OPT_SURROUND_VIEW", "360도 어라운드 뷰", "SAFETY", "서라운드 뷰 모니터 (SVM/AVM)", is_top10=False, icon="eye", is_common=True, encar_code="AROUND_VIEW", kb_code="KB_ADAS_04", carmanager_code="CM_AVM"),
        StandardOptionDef("OPT_AIRBAG_FRONT", "에어백 (운전석/동승석)", "SAFETY", "전면 충돌 보호 기본 에어백", is_top10=False, icon="shield", is_common=True, encar_code="AIRBAG_MAIN", kb_code="KB_SAF_01", carmanager_code="CM_AIRBAG_2"),
        StandardOptionDef("OPT_AIRBAG_SIDE", "사이드/커튼 에어백", "SAFETY", "측면 충돌 보호 에어백 시스템", is_top10=False, icon="shield-alert", is_common=True, encar_code="AIRBAG_SIDE", kb_code="KB_SAF_02", carmanager_code="CM_AIRBAG_CUR"),
        StandardOptionDef("OPT_ABS_ESC", "ABS / 차체자세제어(ESC)", "SAFETY", "급제동 미끄럼 방지 및 차체 자세 유지", is_top10=False, icon="activity", is_common=True, encar_code="ESC_SYS", kb_code="KB_SAF_03", carmanager_code="CM_ABS_ESC"),
        StandardOptionDef("OPT_TCS", "미끄럼 방지 (TCS)", "SAFETY", "구동력 제어 시스템", is_top10=False, icon="disc", is_common=True, encar_code="TCS_SYS", kb_code="KB_SAF_07", carmanager_code="CM_TCS"),
        StandardOptionDef("OPT_TPMS", "타이어 공기압 감지 (TPMS)", "SAFETY", "개별 타이어 공기압 이상 경보", is_top10=False, icon="alert-circle", is_common=True, encar_code="TPMS", kb_code="KB_SAF_04", carmanager_code="CM_TPMS"),
        StandardOptionDef("OPT_LANE_ASSIST", "차선이탈 경보 / 유지보조", "SAFETY", "차로 이탈 방지(LKA) 및 유지 보조(LFA)", is_top10=False, icon="git-commit", is_common=True, encar_code="LANE_KEEP", kb_code="KB_ADAS_02", carmanager_code="CM_LKA"),
        StandardOptionDef("OPT_BLIND_SPOT", "후측방 충돌방지 보조", "SAFETY", "사각지대 접근 차량 경고 및 능동 제동", is_top10=False, icon="alert-triangle", is_common=True, encar_code="BLIND_SPOT", kb_code="KB_ADAS_03", carmanager_code="CM_BSD"),

        # ========================================================
        # 3. 편의·멀티미디어 (CONVENIENCE_MULTIMEDIA)
        # ========================================================
        StandardOptionDef("OPT_HUD", "헤드업 디스플레이 (HUD)", "CONVENIENCE_MULTIMEDIA", "전면 앞유리 주행 정보 컬러 투영", is_top10=True, icon="tv", is_common=True, encar_code="HUD", kb_code="KB_ADAS_05", carmanager_code="CM_HUD"),
        StandardOptionDef("OPT_AUTO_AC", "자동 에어컨", "CONVENIENCE_MULTIMEDIA", "풀오토 에어컨 (좌우 독립 듀얼 제어)", is_top10=True, icon="fan", is_common=True, encar_code="AUTO_AC", kb_code="KB_CONV_01", carmanager_code="CM_FATC"),
        StandardOptionDef("OPT_SMART_KEY", "스마트키", "CONVENIENCE_MULTIMEDIA", "스마트키 / 버튼 시동 / 원격 시동", is_top10=True, icon="key", is_common=True, encar_code="SMART_KEY", kb_code="KB_CONV_02", carmanager_code="CM_SMART_KEY"),
        StandardOptionDef("OPT_GENUINE_NAVI", "내비게이션", "CONVENIENCE_MULTIMEDIA", "순정 와이드 디스플레이 내비게이션", is_top10=True, icon="navigation", is_common=True, encar_code="GENUINE_NAVI", kb_code="KB_MEDIA_01", carmanager_code="CM_ORIG_NAVI"),
        StandardOptionDef("OPT_SMART_CRUISE", "크루즈 컨트롤 (스마트 크루즈)", "CONVENIENCE_MULTIMEDIA", "스마트 크루즈 컨트롤 (정차 및 재출발)", is_top10=False, icon="compass", is_common=True, encar_code="SMART_CRUISE", kb_code="KB_ADAS_01", carmanager_code="CM_SCC"),
        StandardOptionDef("OPT_AUTO_HOLD", "전자식 파킹 브레이크 (오토홀드)", "CONVENIENCE_MULTIMEDIA", "EPB 및 신호대기 오토홀드 지원", is_top10=False, icon="pause-circle", is_common=True, encar_code="EPB_AUTOHOLD", kb_code="KB_CONV_05", carmanager_code="CM_EPB"),
        StandardOptionDef("OPT_AUTO_LIGHT", "오토 라이트 컨트롤", "CONVENIENCE_MULTIMEDIA", "조도 감지 자동 전조등 점등", is_top10=False, icon="sun-medium", is_common=True, encar_code="AUTO_LIGHT", kb_code="KB_CONV_06", carmanager_code="CM_AUTOLIGHT"),
        StandardOptionDef("OPT_BLUETOOTH", "블루투스 핸즈프리 / 오디오", "CONVENIENCE_MULTIMEDIA", "스마트폰 무선 오디오 스트리밍", is_top10=False, icon="bluetooth", is_common=True, encar_code="BLUETOOTH", kb_code="KB_MEDIA_04", carmanager_code="CM_BT"),
        StandardOptionDef("OPT_WIRELESS_CHARGER", "무선 충전 (스마트폰)", "CONVENIENCE_MULTIMEDIA", "고속 스마트폰 무선 충전 패드", is_top10=False, icon="battery-charging", is_common=False, encar_code="WIRELESS_CHG", kb_code="KB_CONV_04", carmanager_code="CM_WIRELESS"),
        StandardOptionDef("OPT_CARPLAY_AA", "애플 카플레이 / 안드로이드 오토", "CONVENIENCE_MULTIMEDIA", "스마트폰 폰 프로젝션 미러링", is_top10=False, icon="smartphone", is_common=True, encar_code="PHONE_PROJ", kb_code="KB_MEDIA_03", carmanager_code="CM_CARPLAY"),
        StandardOptionDef("OPT_HIPASS", "하이패스 내장 룸미러", "CONVENIENCE_MULTIMEDIA", "ECM 전자식 룸미러 및 하이패스 결제", is_top10=False, icon="credit-card", is_common=True, encar_code="HIPASS", kb_code="KB_CONV_07", carmanager_code="CM_HIPASS"),

        # ========================================================
        # 4. 시트 (SEAT)
        # ========================================================
        StandardOptionDef("OPT_LEATHER_SEATS", "가죽시트", "SEAT", "천연가죽 / 나파가죽 / 프리미엄 퀼팅 시트", is_top10=True, icon="armchair", is_common=True, encar_code="LEATHER_SEAT", kb_code="KB_SEAT_01", carmanager_code="CM_LEATHER"),
        StandardOptionDef("OPT_HEATED_SEAT", "열선시트", "SEAT", "앞좌석 및 뒷좌석 온열 시트", is_top10=True, icon="flame", is_common=True, encar_code="HEAT_SEAT", kb_code="KB_SEAT_04", carmanager_code="CM_HEAT_ST"),
        StandardOptionDef("OPT_VENTILATED_SEAT", "통풍시트", "SEAT", "앞좌석 시트 쿨링 바람 송풍 기능", is_top10=True, icon="wind", is_common=True, encar_code="COOL_SEAT", kb_code="KB_SEAT_03", carmanager_code="CM_VENT_ST"),
        StandardOptionDef("OPT_POWER_SEAT_DRV", "운전석 전동시트", "SEAT", "전동식 시트 및 전동 요추 받침대", is_top10=False, icon="user-check", is_common=True, encar_code="POWER_SEAT_DRV", kb_code="KB_SEAT_02", carmanager_code="CM_PWR_DRV"),
        StandardOptionDef("OPT_POWER_SEAT_PASS", "동승석 전동시트", "SEAT", "동승석 전동 조절 및 워크인 디바이스", is_top10=False, icon="users", is_common=True, encar_code="POWER_SEAT_PASS", kb_code="KB_SEAT_05", carmanager_code="CM_PWR_PASS"),
        StandardOptionDef("OPT_MEMORY_SEAT", "메모리 시트", "SEAT", "운전석 자세 메모리 시스템(IMS)", is_top10=False, icon="bookmark", is_common=True, encar_code="MEMORY_SEAT", kb_code="KB_SEAT_06", carmanager_code="CM_IMS"),
        StandardOptionDef("OPT_MASSAGE_SEAT", "마사지 시트 (에르고 모션)", "SEAT", "공기주머니 스트레칭 및 골반 피로완화", is_top10=False, icon="sparkles", is_common=False, encar_code="MASSAGE_SEAT", kb_code="KB_SEAT_07", carmanager_code="CM_MASSAGE"),
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
        ordered = []
        for code in cls.TOP_10_CODES:
            if code in top_map:
                item = top_map[code]
                item["category_label"] = cls.CATEGORY_LABELS.get(item["category"], item["category"])
                ordered.append(item)
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

