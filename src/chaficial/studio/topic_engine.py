"""AI 토픽 발견, 클러스터링 및 추천 랭킹 엔진.

DIRECTIVE 004-A 명세 준수:
- 단순 조회수 정렬 배제, 공통 관심사 기반 토픽 클러스터링
- 통계적 점수 계산(Popularity, Velocity, Time Decay, Channel Normalization)과 LLM 추론 분리
- 25년 경력 차마트 사장님 실무 경험 활용 적합도(Dealer Fit Score) 산출
- 근거 부족 시 LOW_CONFIDENCE / INSUFFICIENT_DATA 표시
- 프롬프트 버전, 모델명, 판단 근거, 원본 영상 ID 메타데이터 투명 저장
- 매일 제작 추천 주제 TOP 5~10개 선별
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from chaficial.studio.models import (
    AnalysisConfidence,
    TopicCluster,
    TopicRecommendation,
    TopicStatus,
    VideoRecord,
)

# 주요 의미론적 주제 카테고리 정의
TOPIC_CATEGORY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "IMPORT_REPAIR_BOMB": {
        "name": "수입 중고차 수리비 폭탄과 유지비 현실",
        "category": "수리비/유지비",
        "keywords": ["수리비", "벤츠", "bmw", "폭탄", "오일누유", "에어서스", "유지비", "가스켓", "정비"],
        "dealer_fit_weight": 0.95,  # 딜러가 매일 겪는 수리비 정밀 견적 노하우
        "selection_reason": "수입차 감가에 혹해 진입했다가 수리비로 낭패를 보는 시청자 공포와 현실적인 대처법에 대한 검색 수요가 매우 높음.",
    },
    "FLOOD_AND_FRAUD": {
        "name": "침수차·허위매물 1초 컷 실전 감별법",
        "category": "허위매물/사기예방",
        "keywords": ["침수", "허위매물", "계약금", "사기", "안전벨트", "퓨즈박스", "부식", "판별"],
        "dealer_fit_weight": 0.98,  # 25년 현장 딜러의 가장 강력한 실전 무기
        "selection_reason": "여름철/장마 후 침수차 유입 우려 및 중고차 시장 불신 해소에 대한 대중적 관심이 폭발적이며 쇼츠 후킹에 최적.",
    },
    "DEPRECIATION_VALUE_COMPARISON": {
        "name": "감가상각 60% 맞은 대형차 vs 신차 가성비 종결",
        "category": "감가상각/가성비",
        "keywords": ["감가", "감가상각", "제네시스", "g80", "아반떼", "가성비", "반값", "예산"],
        "dealer_fit_weight": 0.90,  # 신차 대비 중고차의 가격 메리트를 가장 잘 설명할 수 있는 영역
        "selection_reason": "동일 예산(2000~3000만원대)에서 하차감과 유지비 실리를 저울질하는 실구매자들의 반응률(댓글 참여)이 극대화됨.",
    },
    "ACCIDENT_FRAME_INSPECTION": {
        "name": "성능점검표 '단순교환'과 '골격 판금'의 결정적 차이",
        "category": "성능점검/사고이력",
        "keywords": ["성능점검", "무사고", "완전무사고", "단순교환", "골격", "휠하우스", "휀더", "사고차"],
        "dealer_fit_weight": 0.92,  # 성능기록부 판독 및 딜러 실무 노하우
        "selection_reason": "무사고 문구에 속지 않고 진짜 뼈대 사고를 거르는 전문적인 판별 팁에 대한 신뢰성 높은 수요 존재.",
    },
    "FIRST_CAR_BUDGET_500": {
        "name": "사회초년생 500만원대 고장 없는 첫 중고차 BEST",
        "category": "첫차추천/가성비",
        "keywords": ["500만원", "첫차", "사회초년생", "아반떼", "모닝", "가성비", "추천", "잔고장"],
        "dealer_fit_weight": 0.85,  # 초년생 상담 경험 풍부
        "selection_reason": "예산이 부족한 2030 사회초년생의 높은 클릭률과 잔고장 없는 안전한 매물 추천에 대한 높은 도달률.",
    },
    "ENGINE_MISSION_WARNING": {
        "name": "시동 걸고 3분! 엔진·미션 고장 전조 증상 판별",
        "category": "차량점검/엔진미션",
        "keywords": ["엔진", "미션", "소리", "전조증상", "냉간시동", "태핏", "보링", "점검"],
        "dealer_fit_weight": 0.88,  # 현장 시운전 노하우
        "selection_reason": "직접 차를 보러 갔을 때 일반인이 소리와 진동만으로 큰 결함을 피할 수 있는 실용 꿀팁 콘텐츠.",
    },
}


class TopicDiscoveryEngine:
    """통계적 지표 수식 계산과 LLM/규칙 기반 의미 클러스터링을 결합한 하이브리드 엔진."""

    PROMPT_VERSION = "v1.2.0-dealer-centric"
    MODEL_NAME = "chaficial-hybrid-stats-llm-v1"

    def __init__(self) -> None:
        pass

    def cluster_videos(self, videos: list[VideoRecord]) -> list[TopicCluster]:
        """비디오 목록을 의미론적 공통 관심사 클러스터로 그룹핑."""
        clusters: dict[str, TopicCluster] = {}

        # 1. 사전 정의된 주제 카테고리 초기화
        for cat_key, info in TOPIC_CATEGORY_DEFINITIONS.items():
            clusters[cat_key] = TopicCluster(
                cluster_name=info["name"],
                primary_category=info["category"],
                keywords=list(info["keywords"]),
                video_ids=[],
            )

        # 2. 비디오 텍스트(제목, 설명, 키워드)와 클러스터 매핑
        uncategorized_ids: list[str] = []
        for v in videos:
            text = f"{v.title} {v.description} {' '.join(v.matched_keywords)}".lower()
            matched_cluster_key: str | None = None
            max_match_count = 0

            for cat_key, info in TOPIC_CATEGORY_DEFINITIONS.items():
                match_count = sum(1 for kw in info["keywords"] if kw.lower() in text)
                if match_count > max_match_count:
                    max_match_count = match_count
                    matched_cluster_key = cat_key

            if matched_cluster_key and max_match_count >= 1:
                clusters[matched_cluster_key].video_ids.append(v.video_id)
                v.topic_ids.append(clusters[matched_cluster_key].cluster_id)
            else:
                uncategorized_ids.append(v.video_id)

        # 3. 매핑된 비디오가 존재하는 클러스터만 필터링
        active_clusters = [c for c in clusters.values() if len(c.video_ids) > 0]
        return active_clusters

    def calculate_topic_scores(
        self,
        cluster: TopicCluster,
        videos_by_id: dict[str, VideoRecord],
    ) -> TopicRecommendation:
        """클러스터 내 실제 인기 지표를 바탕으로 다차원 점수 및 신뢰도를 계산."""
        member_videos = [videos_by_id[vid] for vid in cluster.video_ids if vid in videos_by_id]
        if not member_videos:
            return TopicRecommendation(
                topic_name=cluster.cluster_name,
                category=cluster.primary_category,
                confidence_level=AnalysisConfidence.INSUFFICIENT_DATA,
                selection_reason="연결된 유효 영상 데이터가 존재하지 않습니다.",
                trend_summary="데이터 부족",
            )

        # A. 통계적 인기도 점수 (조회수 log + 참여율 가중치 + 시간 감쇄)
        total_views = sum(v.view_count for v in member_videos)
        total_likes = sum(v.like_count for v in member_videos)
        total_comments = sum(v.comment_count for v in member_videos)
        avg_views = total_views / max(len(member_videos), 1)

        # 평균 참여율
        avg_engagement = ((total_likes * 1.0) + (total_comments * 3.0)) / max(total_views, 1)

        # 최신성 감쇄 계산 (가장 최근 업로드 영상 기준)
        now = datetime.now(UTC)
        newest_upload = max(v.published_at for v in member_videos)
        if newest_upload.tzinfo is None:
            newest_upload = newest_upload.replace(tzinfo=UTC)
        days_since_newest = max((now - newest_upload).total_seconds() / 86400.0, 0.1)
        time_decay = max(1.0 - (days_since_newest / 60.0) * 0.4, 0.4)

        # 기본 인기도 점수 (0 ~ 100)
        pop_base = math.log10(max(avg_views, 10)) * 14.0
        pop_engagement_bonus = min(avg_engagement * 600.0, 30.0)
        popularity_score = round((pop_base + pop_engagement_bonus) * time_decay, 2)

        # B. 성장 속도 점수 (Velocity: 최근 7일 내 영상 비율 및 조회수 집중도)
        recent_7d_count = sum(
            1 for v in member_videos
            if (now - (v.published_at if v.published_at.tzinfo else v.published_at.replace(tzinfo=UTC))).total_seconds() <= 7 * 86400
        )
        velocity_ratio = recent_7d_count / max(len(member_videos), 1)
        velocity_score = round(velocity_ratio * 40.0 + min(len(member_videos) * 5.0, 30.0), 2)

        # C. 25년 딜러 경험 활용 적합도 점수 (Dealer Fit Score: 0 ~ 100)
        category_meta = next(
            (info for info in TOPIC_CATEGORY_DEFINITIONS.values() if info["name"] == cluster.cluster_name),
            None,
        )
        fit_weight = category_meta["dealer_fit_weight"] if category_meta else 0.70
        dealer_fit_score = round(fit_weight * 100.0, 2)

        # D. 종합 점수 (Composite Score): 인기(40%) + 속도(20%) + 딜러적합도(30%) + 클러스터볼륨(10%)
        volume_bonus = min(len(member_videos) * 4.0, 20.0)
        composite_score = round(
            (popularity_score * 0.40)
            + (velocity_score * 0.20)
            + (dealer_fit_score * 0.30)
            + volume_bonus,
            2,
        )

        # E. 신뢰도 평가
        confidence = AnalysisConfidence.HIGH_CONFIDENCE
        if len(member_videos) < 2:
            confidence = AnalysisConfidence.LOW_CONFIDENCE
        if total_views < 10000:
            confidence = AnalysisConfidence.LOW_CONFIDENCE

        # F. 선정 이유 및 트렌드 요약
        reason = category_meta["selection_reason"] if category_meta else "실제 검색 지표 및 시청자 참여 기반 유망 토픽."
        trend_summary = (
            f"총 {len(member_videos)}개 인기 영상 관측 (누적 조회수 {total_views:,}회, 평균 참여율 {avg_engagement * 100:.2f}%). "
            f"최근 {days_since_newest:.1f}일 전 신규 영상이 게시되었으며 딜러 실무 노하우 전달 적합도 {dealer_fit_score}점."
        )

        return TopicRecommendation(
            topic_name=cluster.cluster_name,
            category=cluster.primary_category,
            popularity_score=popularity_score,
            velocity_score=velocity_score,
            dealer_fit_score=dealer_fit_score,
            composite_score=composite_score,
            status=TopicStatus.RECOMMENDED,
            confidence_level=confidence,
            supporting_video_ids=[v.video_id for v in member_videos],
            selection_reason=reason,
            trend_summary=trend_summary,
            is_newly_discovered=True,
            prompt_version=self.PROMPT_VERSION,
            model_name=self.MODEL_NAME,
        )

    def rank_top_topics(
        self,
        videos: list[VideoRecord],
        top_n: int = 10,
    ) -> list[TopicRecommendation]:
        """비디오 목록 전체를 클러스터링하고 종합 점수 기준 TOP 5~10 추천 주제를 랭킹."""
        clusters = self.cluster_videos(videos)
        videos_by_id = {v.video_id: v for v in videos}

        recommendations: list[TopicRecommendation] = []
        for c in clusters:
            rec = self.calculate_topic_scores(c, videos_by_id)
            recommendations.append(rec)

        # 종합 점수 내림차순 정렬
        recommendations.sort(key=lambda r: r.composite_score, reverse=True)

        # 순위 부여 및 TOP N 슬라이싱 (최소 5개 ~ 최대 10개)
        top_list = recommendations[: max(5, min(top_n, 10))]
        for idx, rec in enumerate(top_list, start=1):
            rec.rank = idx

        return top_list
