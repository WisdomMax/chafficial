"""콘텐츠 엔진 데이터 저장 및 조회 저장소 (Repository).

- TrendCandidate 중복 식별 및 등록 방지
- VehicleContentCandidate 관리
- ExpertReview 관리
- ProductionProject 상태 관리 및 영속화 인터페이스
"""

from __future__ import annotations

from pathlib import Path

from chaficial.content.models import (
    DuplicateTrendCandidateError,
    ExpertReview,
    ProductionProject,
    TrendCandidate,
    VehicleContentCandidate,
)


class ContentRepository:
    """메모리 기반 및 파일 기반 저장을 지원하는 콘텐츠 저장소."""

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        self.storage_dir = Path(storage_dir) if storage_dir else None
        if self.storage_dir:
            self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._trends_by_id: dict[str, TrendCandidate] = {}
        self._trends_by_hash: dict[str, str] = {}  # hash -> candidate_id

        self._vehicles_by_id: dict[str, VehicleContentCandidate] = {}
        self._reviews_by_id: dict[str, ExpertReview] = {}
        self._projects_by_id: dict[str, ProductionProject] = {}

    # -------------------------------------------------------------------------
    # TrendCandidate 관리
    # -------------------------------------------------------------------------

    def save_trend(self, candidate: TrendCandidate) -> TrendCandidate:
        """인기 영상 후보 등록. 중복 식별자가 이미 존재하는 경우 예외 발생."""
        content_hash = candidate.content_hash
        if content_hash in self._trends_by_hash:
            existing_id = self._trends_by_hash[content_hash]
            raise DuplicateTrendCandidateError(
                f"이미 등록된 영상 콘텐츠입니다. (기존 ID: {existing_id}, URL: {candidate.source_url})"
            )

        self._trends_by_id[candidate.candidate_id] = candidate
        self._trends_by_hash[content_hash] = candidate.candidate_id
        return candidate

    def get_trend(self, candidate_id: str) -> TrendCandidate | None:
        return self._trends_by_id.get(candidate_id)

    def list_trends(self) -> list[TrendCandidate]:
        return list(self._trends_by_id.values())

    # -------------------------------------------------------------------------
    # VehicleContentCandidate 관리
    # -------------------------------------------------------------------------

    def save_vehicle(self, candidate: VehicleContentCandidate) -> VehicleContentCandidate:
        self._vehicles_by_id[candidate.candidate_id] = candidate
        return candidate

    def get_vehicle(self, candidate_id: str) -> VehicleContentCandidate | None:
        return self._vehicles_by_id.get(candidate_id)

    def list_vehicles(self) -> list[VehicleContentCandidate]:
        return list(self._vehicles_by_id.values())

    # -------------------------------------------------------------------------
    # ExpertReview 관리
    # -------------------------------------------------------------------------

    def save_review(self, review: ExpertReview) -> ExpertReview:
        self._reviews_by_id[review.review_id] = review
        return review

    def get_review(self, review_id: str) -> ExpertReview | None:
        return self._reviews_by_id.get(review_id)

    def get_review_by_target(self, target_id: str) -> ExpertReview | None:
        for rev in self._reviews_by_id.values():
            if rev.target_id == target_id:
                return rev
        return None

    # -------------------------------------------------------------------------
    # ProductionProject 관리
    # -------------------------------------------------------------------------

    def save_project(self, project: ProductionProject) -> ProductionProject:
        self._projects_by_id[project.project_id] = project
        return project

    def get_project(self, project_id: str) -> ProductionProject | None:
        return self._projects_by_id.get(project_id)

    def list_projects(self) -> list[ProductionProject]:
        return list(self._projects_by_id.values())
