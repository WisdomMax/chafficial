"""표준 옵션 마스터 카탈로그 및 플랫폼별 코드 매핑 (DIRECTIVE 050)."""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class StandardOptionDef:
    code: str
    name: str
    category: str  # SAFETY, CONVENIENCE, SEAT, MULTIMEDIA, EXTERIOR, LIGHTING, DRIVING_ASSIST
    description: str
    is_common: bool  # 기본 추천 목록 표시 여부
    encar_code: str | None
    kb_code: str | None
    carmanager_code: str | None


class StandardOptionCatalog:
    """중고차 표준 옵션 사전 및 플랫폼 매핑."""

    OPTIONS: list[StandardOptionDef] = [
        # 안전
        StandardOptionDef("OPT_AIRBAG_FRONT", "운전석/동승석 에어백", "SAFETY", "전면 충돌 보호 기본 에어백", True, "AIRBAG_MAIN", "KB_SAF_01", "CM_AIRBAG_2"),
        StandardOptionDef("OPT_AIRBAG_SIDE", "사이드/커튼 에어백", "SAFETY", "측면 충돌 보호 에어백", True, "AIRBAG_SIDE", "KB_SAF_02", "CM_AIRBAG_CUR"),
        StandardOptionDef("OPT_ABS_ESC", "ABS/ESC 차체자세제어", "SAFETY", "급제동 및 미끄럼 방지 제어", True, "ESC_SYS", "KB_SAF_03", "CM_ABS_ESC"),
        StandardOptionDef("OPT_TPMS", "TPMS (타이어 공기압 감지)", "SAFETY", "공기압 이상 경고 장치", True, "TPMS", "KB_SAF_04", "CM_TPMS"),

        # 주행보조 (ADAS)
        StandardOptionDef("OPT_SMART_CRUISE", "스마트 크루즈 컨트롤 (SCC)", "DRIVING_ASSIST", "앞차 간격 유지 정속 주행", True, "SMART_CRUISE", "KB_ADAS_01", "CM_SCC"),
        StandardOptionDef("OPT_LANE_ASSIST", "차로 이탈 방지 / 차로 유지 보조", "DRIVING_ASSIST", "LKA/LFA 차로 중앙 유지", True, "LANE_KEEP", "KB_ADAS_02", "CM_LKA"),
        StandardOptionDef("OPT_BLIND_SPOT", "후측방 충돌방지 보조 (BCA)", "DRIVING_ASSIST", "사각지대 차량 경고 및 제동", True, "BLIND_SPOT", "KB_ADAS_03", "CM_BSD"),
        StandardOptionDef("OPT_SURROUND_VIEW", "서라운드 뷰 모니터 (SVM/AVM)", "DRIVING_ASSIST", "360도 전방위 어라운드뷰", True, "AROUND_VIEW", "KB_ADAS_04", "CM_AVM"),
        StandardOptionDef("OPT_HUD", "헤드업 디스플레이 (HUD)", "DRIVING_ASSIST", "전면 유리 주행 정보 투영", False, "HUD", "KB_ADAS_05", "CM_HUD"),

        # 시트 / 공조
        StandardOptionDef("OPT_LEATHER_SEATS", "가죽 시트", "SEAT", "천연가죽 또는 고급 인조가죽 시트", True, "LEATHER_SEAT", "KB_SEAT_01", "CM_LEATHER"),
        StandardOptionDef("OPT_POWER_SEAT", "전동 조절 시트 (운전석/동승석)", "SEAT", "전동식 시트 조절 및 요추 받침", True, "POWER_SEAT", "KB_SEAT_02", "CM_POWER_ST"),
        StandardOptionDef("OPT_VENTILATED_SEAT", "통풍 시트 (앞좌석)", "SEAT", "시트 쿨링 바람 송풍 기능", True, "COOL_SEAT", "KB_SEAT_03", "CM_VENT_ST"),
        StandardOptionDef("OPT_HEATED_SEAT", "열선 시트 (앞/뒤)", "SEAT", "겨울철 시트 온열 기능", True, "HEAT_SEAT", "KB_SEAT_04", "CM_HEAT_ST"),
        StandardOptionDef("OPT_AUTO_AC", "풀오토 에어컨 (듀얼 독립제어)", "CONVENIENCE", "좌우 독립 온도 자동 제어", True, "AUTO_AC", "KB_CONV_01", "CM_FATC"),

        # 편의
        StandardOptionDef("OPT_SMART_KEY", "스마트키 / 버튼 시동", "CONVENIENCE", "키 소지 상태 도어 오픈 및 시동", True, "SMART_KEY", "KB_CONV_02", "CM_SMART_KEY"),
        StandardOptionDef("OPT_POWER_TRUNK", "스마트 파워 테일게이트", "CONVENIENCE", "전동식 트렁크 개폐 기능", True, "POWER_TRUNK", "KB_CONV_03", "CM_PWR_TRUNK"),
        StandardOptionDef("OPT_WIRELESS_CHARGER", "스마트폰 무선 충전", "CONVENIENCE", "센터페시아 무선 충전 패드", False, "WIRELESS_CHG", "KB_CONV_04", "CM_WIRELESS"),
        StandardOptionDef("OPT_AUTO_HOLD", "전자식 파킹 브레이크 & 오토홀드", "CONVENIENCE", "정차 시 브레이크 자동 유지", True, "EPB_AUTOHOLD", "KB_CONV_05", "CM_EPB"),

        # 멀티미디어
        StandardOptionDef("OPT_GENUINE_NAVI", "순정 내비게이션 (대화면)", "MULTIMEDIA", "10.25인치/12.3인치 정품 내비", True, "GENUINE_NAVI", "KB_MEDIA_01", "CM_ORIG_NAVI"),
        StandardOptionDef("OPT_PREMIUM_AUDIO", "프리미엄 사운드 시스템", "MULTIMEDIA", "보스/크렐/하만카돈 외장 앰프", False, "PREMIUM_SOUND", "KB_MEDIA_02", "CM_EXT_AMP"),
        StandardOptionDef("OPT_CARPLAY_AA", "애플 카플레이 / 안드로이드 오토", "MULTIMEDIA", "스마트폰 폰 프로젝션 연동", True, "PHONE_PROJ", "KB_MEDIA_03", "CM_CARPLAY"),

        # 외관 / 등화
        StandardOptionDef("OPT_SUNROOF", "파노라마 선루프", "EXTERIOR", "개방감 높은 전면/와이드 루프", True, "SUNROOF_PANO", "KB_EXT_01", "CM_SUNROOF"),
        StandardOptionDef("OPT_LED_HEADLAMP", "Full LED 헤드램프", "LIGHTING", "프로젝션 LED 주간주행등/전조등", True, "LED_HEADLIGHT", "KB_EXT_02", "CM_LED_LAMP"),
        StandardOptionDef("OPT_ALUMINUM_WHEEL", "알루미늄 알로이 휠 (대구경)", "EXTERIOR", "순정 18~20인치 알로이 휠", True, "AL_WHEEL", "KB_EXT_03", "CM_AL_WHEEL"),
    ]

    @classmethod
    def list_options(cls, category: str | None = None) -> list[dict[str, Any]]:
        """전체 표준 옵션 목록 또는 카테고리별 필터 목록 반환."""
        res = []
        for opt in cls.OPTIONS:
            if category and opt.category != category:
                continue
            res.append(asdict(opt))
        return res

    @classmethod
    def get_by_code(cls, code: str) -> StandardOptionDef | None:
        """옵션 코드로 조회."""
        for opt in cls.OPTIONS:
            if opt.code == code:
                return opt
        return None

    @classmethod
    def get_categories(cls) -> list[str]:
        """옵션 카테고리 목록."""
        return ["SAFETY", "DRIVING_ASSIST", "SEAT", "CONVENIENCE", "MULTIMEDIA", "EXTERIOR", "LIGHTING"]
