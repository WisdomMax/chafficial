"""차마트(CHAMART) 장한평 소재지 식별 및 지역 분류 엔진 (DIRECTIVE 049).

- JANGANPYEONG_CONFIRMED: 장한평·장안평 매매단지/용답동/장안동 확정 매물
- JANGANPYEONG_CANDIDATE: 동대문구/성동구 인접 지역 또는 장한평 추정 매물
- SEOUL_OTHER: 서울 타 자치구(강서, 강남, 양천 등) 소재 확인 매물
- SEOUL_UNSPECIFIED: 서울 등록 매물이나 세부 상사/단지 미기재 매물
- LOCATION_UNKNOWN: 지역 정보 부재 매물
"""

from __future__ import annotations

import re
from typing import Optional, Tuple


class JanganpyeongClassifier:
    """장한평 및 서울 지역 실매물 정밀 분류기."""

    # 1. 장한평 확정 키워드 (매매단지명, 행정동, 랜드마크)
    CONFIRMED_KEYWORDS = [
        "장한평", "장안평", "장안동", "용답동", "답십리동",
        "장안모터프라자", "장안오토랜드", "장안매매단지", "용답매매단지",
        "동대문구 천호대로", "성동구 천호대로", "장한평역",
    ]

    # 2. 장한평 후보 키워드 (인접 자치구 및 상사)
    CANDIDATE_KEYWORDS = [
        "동대문구", "성동구", "군자동", "중곡동", "면목동",
    ]

    # 3. 서울 타 자치구 키워드
    OTHER_SEOUL_DISTRICTS = [
        "강서구", "양천구", "구로구", "금천구", "영등포구", "마포구",
        "서대문구", "은평구", "종로구", "중구", "용산구", "동작구",
        "관악구", "서초구", "강남구", "송파구", "강동구", "광진구",
        "중랑구", "노원구", "도봉구", "강북구", "성북구",
    ]

    @classmethod
    def classify(
        cls,
        raw_region: Optional[str] = None,
        seller_location: Optional[str] = None,
        dealership_name: Optional[str] = None,
    ) -> Tuple[str, str]:
        """소재지 및 판매자 정보를 종합 분석하여 (분류상태, 판정사유) 튜플 반환.
        
        Returns:
            (location_category, identification_reason)
        """
        combined_text = f"{raw_region or ''} {seller_location or ''} {dealership_name or ''}".strip()
        if not combined_text:
            return "LOCATION_UNKNOWN", "소재지 및 판매자 정보가 전혀 제공되지 않음"

        # 텍스트 정규화: 특수문자 및 다중 공백 정리
        normalized = re.sub(r"[\s\-_,/\(\)\[\]]+", " ", combined_text).strip()

        # 1. 장한평 확정 검사 (JANGANPYEONG_CONFIRMED)
        for kw in cls.CONFIRMED_KEYWORDS:
            if kw in normalized:
                matched_source = "단지/상사명" if dealership_name and kw in dealership_name else "전시장 주소"
                return (
                    "JANGANPYEONG_CONFIRMED",
                    f"장한평 핵심 단지/소재지 키워드 '{kw}' 검출 ({matched_source} 근거 확정)",
                )

        # 2. 장한평 후보 검사 (JANGANPYEONG_CANDIDATE)
        for kw in cls.CANDIDATE_KEYWORDS:
            if kw in normalized:
                return (
                    "JANGANPYEONG_CANDIDATE",
                    f"장한평 인접 관할 자치구 '{kw}' 소재 확인 (추정 후보)",
                )

        # 3. 서울 타 구 검사 (SEOUL_OTHER)
        for dist in cls.OTHER_SEOUL_DISTRICTS:
            if dist in normalized:
                return (
                    "SEOUL_OTHER",
                    f"서울 타 자치구 '{dist}' 매매단지/상사 소재 확인",
                )

        # 4. 서울 미지정 검사 (SEOUL_UNSPECIFIED)
        if "서울" in normalized:
            return (
                "SEOUL_UNSPECIFIED",
                "서울 등록 매물이나 세부 구·단지 주소 미지정 (서울 일반 매물)",
            )

        # 5. 불명
        return (
            "LOCATION_UNKNOWN",
            f"서울 외 또는 상세 위치 판별 불가: '{normalized[:30]}'",
        )
