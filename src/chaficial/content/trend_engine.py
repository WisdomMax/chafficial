"""트렌드 기반 인기 콘텐츠 발굴 및 분석 엔진.

DIRECTIVE 003-A 명세 준수:
- 유튜브 쇼츠, 인스타그램 릴스, 틱톡 인기 소재 발굴
- 조회수, 반응률, 업로드 시점 기반 인기도 점수 계산
- 인기 영상의 주제, 후킹 패턴, 구성 요소 추출
- 중복 등록 방지 (DuplicateTrendCandidateError)
- 검색과 심층 분석의 분리 및 탐색 예산/지표 관리
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from chaficial.content.models import (
    DuplicateTrendCandidateError,
    TrendCandidate,
)
from chaficial.content.repository import ContentRepository


class TrendIntelligenceEngine:
    """인기 영상 발굴, 중복 방지, 반응률 분석 및 구조 추출 엔진."""

    def __init__(self, repository: ContentRepository) -> None:
        self.repository = repository
        self.total_search_calls = 0
        self.discovered_count = 0
        self.duplicate_count = 0

    def calculate_popularity_score(
        self,
        view_count: int,
        like_count: int,
        comment_count: int,
        uploaded_at: datetime | None = None,
    ) -> float:
        """조회수와 참여율(Engagement), 시간 감쇄를 반영한 바이럴 인기도 점수 산출."""
        if view_count <= 0:
            return 0.0

        # 참여율 (좋아요 가중치 1.0, 댓글 가중치 3.0)
        engagement_rate = ((like_count * 1.0) + (comment_count * 3.0)) / max(view_count, 1)

        # 로그 스케일 조회수 기본 점수
        base_score = math.log10(max(view_count, 1)) * 15.0

        # 참여 보너스 (최대 30점)
        engagement_bonus = min(engagement_rate * 500.0, 30.0)

        # 시간 감쇄 (최신 영상일수록 트렌드 가산점)
        time_factor = 1.0
        if uploaded_at:
            now = datetime.now(UTC)
            if uploaded_at.tzinfo is None:
                uploaded_at = uploaded_at.replace(tzinfo=UTC)
            days_old = max((now - uploaded_at).total_seconds() / 86400.0, 0.1)
            time_factor = max(1.0 - (days_old / 90.0) * 0.3, 0.5)

        total_score = (base_score + engagement_bonus) * time_factor
        return round(total_score, 2)

    def analyze_content_structure(self, title: str, raw_text: str = "") -> dict[str, Any]:
        """인기 영상의 제목 및 설명으로부터 후킹 패턴, 주제, 편집 구조 추출."""
        text = f"{title} {raw_text}".strip()

        # 주요 후킹 패턴 식별
        hook_type = "CURIOSITY"  # 호기심 유발 기본형
        if any(w in text for w in ["절대", "사지 마세요", "호구", "망합니다", "속지"]):
            hook_type = "WARNING_FEAR"  # 손실 회피 및 경고형
        elif any(w in text for w in ["천만원", "가성비", "반값", "감가", "싸게"]):
            hook_type = "VALUE_BARGAIN"  # 가성비/가격 충격형
        elif any(w in text for w in ["비밀", "딜러만 아는", "진실", "고백", "폭로"]):
            hook_type = "INSIDER_SECRET"  # 내부자 고백/썰형
        elif any(w in text for w in ["침수", "사고", "전손", "구별법", "확인법"]):
            hook_type = "PRACTICAL_TIP"  # 실전 꿀팁/검증형

        # 핵심 주제 추출
        topic = "중고차 구매 꿀팁 및 주의사항"
        if "침수" in text:
            topic = "침수차 판별 및 장마철 매물 구별법"
        elif "감가" in text or "수입차" in text:
            topic = "감가 폭탄 맞은 가성비 수입차 분석"
        elif "허위" in text or "미끼" in text:
            topic = "허위매물 및 중고차 사기 수법 파헤치기"
        elif "엔진" in text or "누유" in text:
            topic = "중고차 하체 및 누유 1분 점검 썰"

        return {
            "hook_type": hook_type,
            "topic": topic,
            "recommended_duration_sec": 30,
            "target_emotions": ["호기심", "신뢰", "안도감"],
            "structure": {
                "hook_phase": "0~3초: 강력한 질문 또는 경고로 이탈 방지",
                "body_phase": "3~20초: 25년 현장 딜러 경험담 및 구체적 식별법",
                "twist_phase": "20~25초: 사람들이 잘못 알고 있는 상식 뒤집기",
                "cta_phase": "25~30초: 문의 및 안심 구매 유도",
            },
        }

    def register_trend_candidate(
        self,
        platform: str,
        source_url: str,
        title: str,
        account_name: str,
        view_count: int = 0,
        like_count: int = 0,
        comment_count: int = 0,
        uploaded_at: datetime | None = None,
        search_keyword: str = "",
        raw_description: str = "",
    ) -> TrendCandidate:
        """인기 영상 후보를 등록하고 분석 결과를 기록. 중복 등록 시 예외 발생."""
        self.total_search_calls += 1

        pop_score = self.calculate_popularity_score(
            view_count, like_count, comment_count, uploaded_at
        )
        struct = self.analyze_content_structure(title, raw_description)

        candidate = TrendCandidate(
            platform=platform,
            source_url=source_url,
            title=title,
            account_name=account_name,
            view_count=view_count,
            like_count=like_count,
            comment_count=comment_count,
            uploaded_at=uploaded_at,
            search_keyword=search_keyword,
            popularity_score=pop_score,
            topic=struct["topic"],
            structure_analysis=struct,
        )

        try:
            saved = self.repository.save_trend(candidate)
            self.discovered_count += 1
            return saved
        except DuplicateTrendCandidateError:
            self.duplicate_count += 1
            raise

    def get_discovery_metrics(self) -> dict[str, Any]:
        """신규 발견율, 중복률, 탐색 지표 반환."""
        dup_rate = (
            (self.duplicate_count / self.total_search_calls)
            if self.total_search_calls > 0
            else 0.0
        )
        return {
            "total_search_calls": self.total_search_calls,
            "discovered_count": self.discovered_count,
            "duplicate_count": self.duplicate_count,
            "duplicate_rate": round(dup_rate, 4),
        }
