"""판매 후보 매물 및 파트너 승인/상태 이력 모델.

과거 시점 재현 시 미래의 파트너 승인 상태 유입을 방지하기 위해,
상태 변경 시점별 불변(Append-only) 이력을 보존하며, UPDATE 및 DELETE를 원천 차단합니다.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    DDL,
    CheckConstraint,
    DateTime,
    Engine,
    Float,
    ForeignKey,
    String,
    event,
    text,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from chaficial.database.base import Base


class ImmutableCandidateHistoryError(Exception):
    """후보 상태 이력 수정 또는 삭제 시도 시 발생하는 예외."""


class SalesCandidate(Base):
    """AI 알고리즘 또는 전문가가 선정한 실제 판매 후보 차량.
    
    저렴하다는 이유만으로 자동 추천되지 않으며, 파트너의 실제 재고·판매 가능 여부 검토를 거칩니다.
    - selected_at: 의사결정상 선정 시각
    - created_at: 시스템 데이터베이스에 적재된 시각
    """
    __tablename__ = "sales_candidates"

    candidate_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    listing_id: Mapped[str] = mapped_column(
        ForeignKey("listings.listing_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    target_region_id: Mapped[str] = mapped_column(
        ForeignKey("regions.region_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    selected_by: Mapped[str] = mapped_column(
        String(30), nullable=False, default="AI_AGENT"
    )  # AI_AGENT, PARTNER_MANUAL, RULE_BASED
    selection_reason: Mapped[str] = mapped_column(String(200), nullable=False)
    selection_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    availability_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNCONFIRMED"
    )  # AVAILABLE, RESERVED, SOLD_OUT, UNCONFIRMED
    partner_review_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING"
    )  # APPROVED, REJECTED, PENDING
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "selected_by IN ('AI_AGENT', 'PARTNER_MANUAL', 'RULE_BASED')",
            name="chk_candidate_selected_by",
        ),
        CheckConstraint(
            "availability_status IN ('AVAILABLE', 'RESERVED', 'SOLD_OUT', 'UNCONFIRMED')",
            name="chk_candidate_availability",
        ),
        CheckConstraint(
            "partner_review_status IN ('APPROVED', 'REJECTED', 'PENDING')",
            name="chk_candidate_partner_review",
        ),
    )

    listing = relationship("Listing", lazy="joined")
    target_region = relationship("Region", lazy="joined")
    # 부모 삭제 시 이력 연쇄 삭제 방지 (이력 보존)
    status_histories = relationship(
        "CandidateStatusHistory",
        back_populates="candidate",
        order_by="CandidateStatusHistory.changed_at",
        cascade="save-update, merge",
        passive_deletes=True,
    )


class CandidateStatusHistory(Base):
    """후보 차량의 파트너 승인 및 재고 상태 변경 이력 (Append-only).
    
    시간 경과에 따른 승인 상태 전이를 불변으로 기록하여 Time-Travel 시 미래 승인 누출을 차단합니다.
    ORM 리스너 및 DB 트리거를 통해 UPDATE/DELETE가 원천 차단됩니다.
    """
    __tablename__ = "candidate_status_histories"

    history_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("sales_candidates.candidate_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    partner_review_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING"
    )
    availability_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNCONFIRMED"
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "partner_review_status IN ('APPROVED', 'REJECTED', 'PENDING')",
            name="chk_history_partner_review",
        ),
        CheckConstraint(
            "availability_status IN ('AVAILABLE', 'RESERVED', 'SOLD_OUT', 'UNCONFIRMED')",
            name="chk_history_availability",
        ),
    )

    candidate = relationship("SalesCandidate", back_populates="status_histories")


# ==============================================================================
# 상태 이력 불변성(Append-only) 강제 장치
# ==============================================================================

@event.listens_for(CandidateStatusHistory, "before_update")
def _prevent_history_update(mapper, connection, target):
    raise ImmutableCandidateHistoryError("CandidateStatusHistory is append-only and cannot be updated.")


@event.listens_for(CandidateStatusHistory, "before_delete")
def _prevent_history_delete(mapper, connection, target):
    raise ImmutableCandidateHistoryError("CandidateStatusHistory is permanent audit data and cannot be deleted.")


SQLITE_TRIGGER_CANDIDATE_HIST_UPDATE = """
CREATE TRIGGER IF NOT EXISTS trg_prevent_candidate_hist_update
BEFORE UPDATE ON candidate_status_histories
BEGIN
    SELECT RAISE(ABORT, 'CandidateStatusHistory is append-only and cannot be updated.');
END;
"""

SQLITE_TRIGGER_CANDIDATE_HIST_DELETE = """
CREATE TRIGGER IF NOT EXISTS trg_prevent_candidate_hist_delete
BEFORE DELETE ON candidate_status_histories
BEGIN
    SELECT RAISE(ABORT, 'CandidateStatusHistory is permanent audit data and deletion is prohibited.');
END;
"""

_trg_hist_update_sqlite = DDL(SQLITE_TRIGGER_CANDIDATE_HIST_UPDATE)
_trg_hist_delete_sqlite = DDL(SQLITE_TRIGGER_CANDIDATE_HIST_DELETE)

event.listen(
    CandidateStatusHistory.__table__,
    "after_create",
    _trg_hist_update_sqlite.execute_if(dialect="sqlite"),
)
event.listen(
    CandidateStatusHistory.__table__,
    "after_create",
    _trg_hist_delete_sqlite.execute_if(dialect="sqlite"),
)


def ensure_candidate_history_triggers(engine_or_connection: Engine | Any) -> None:
    """기존 데이터베이스에 후보 상태 이력 불변성 트리거를 멱등하게 주입/갱신합니다."""
    is_engine = isinstance(engine_or_connection, Engine)
    conn = engine_or_connection.connect() if is_engine else engine_or_connection
    try:
        if conn.dialect.name == "sqlite":
            conn.execute(text("DROP TRIGGER IF EXISTS trg_prevent_candidate_hist_update;"))
            conn.execute(text("DROP TRIGGER IF EXISTS trg_prevent_candidate_hist_delete;"))
            conn.execute(text(SQLITE_TRIGGER_CANDIDATE_HIST_UPDATE))
            conn.execute(text(SQLITE_TRIGGER_CANDIDATE_HIST_DELETE))
            if is_engine:
                conn.commit()
    finally:
        if is_engine:
            conn.close()


def update_candidate_status(
    session: Session,
    candidate_id: str,
    new_partner_status: str | None = None,
    new_availability_status: str | None = None,
    changed_at: datetime | None = None,
    ingested_at: datetime | None = None,
    note: str | None = None,
) -> CandidateStatusHistory:
    """후보 매물의 파트너 승인/재고 상태를 원자적으로 갱신하고 불변 이력을 동시 생성합니다.
    
    이 함수는 SalesCandidate의 현재 상태를 동기화하면서 반드시 새로운 CandidateStatusHistory
    레코드를 추가하여 시간순 정합성을 보장합니다.
    """
    candidate = session.get(SalesCandidate, candidate_id)
    if not candidate:
        raise ValueError(f"SalesCandidate '{candidate_id}' not found.")

    partner_status = new_partner_status or candidate.partner_review_status
    avail_status = new_availability_status or candidate.availability_status
    event_time = changed_at or datetime.now(UTC)
    ingest_time = ingested_at or datetime.now(UTC)

    # 1. SalesCandidate 현재 상태 업데이트
    candidate.partner_review_status = partner_status
    candidate.availability_status = avail_status
    if note:
        candidate.review_note = note

    # 2. 불변 이력 생성 (Append-only)
    history = CandidateStatusHistory(
        candidate_id=candidate.candidate_id,
        partner_review_status=partner_status,
        availability_status=avail_status,
        changed_at=event_time,
        ingested_at=ingest_time,
        review_note=note,
    )
    session.add(history)
    session.flush()
    return history
