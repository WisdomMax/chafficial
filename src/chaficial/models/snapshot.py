"""매물 상태 및 가격의 시계열 스냅샷 모델.

시계열 불변성(Append-only)을 보장하며, DB 트리거 및 ORM 리스너를 통해
UPDATE 및 DELETE를 영구적으로 차단합니다.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    DDL,
    JSON,
    CheckConstraint,
    DateTime,
    Engine,
    ForeignKey,
    Integer,
    String,
    event,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class ImmutableSnapshotError(Exception):
    """스냅샷 수정 또는 삭제 시도 시 발생하는 예외."""


class ListingSnapshot(Base):
    """매물 관측 시점별 불변(Immutable) 스냅샷.
    
    가격 변경이나 상태 변경, 지역 정정 시 이전 기록을 절대 덮어쓰지 않고 새로 추가합니다.
    - observed_at: 실제 시장에서 관측된 시점
    - ingested_at: 차피셜 시스템 데이터베이스에 적재된 시점
    - normalized_region_id: 해당 관측 시점에 확인된 지역 ID (사후 정정 이력 추적)
    - DB 트리거를 통해 SQL UPDATE 및 DELETE를 원천 차단합니다.
    """
    __tablename__ = "listing_snapshots"

    snapshot_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    listing_id: Mapped[str] = mapped_column(
        ForeignKey("listings.listing_id", ondelete="CASCADE"), nullable=False, index=True
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    price_krw: Mapped[int] = mapped_column(Integer, nullable=False)
    mileage_km: Mapped[int] = mapped_column(Integer, nullable=False)
    listing_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ACTIVE"
    )  # ACTIVE, PRICE_CHANGED, DELISTED, UNKNOWN
    normalized_region_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )
    raw_specs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source_record_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        CheckConstraint("price_krw >= 0", name="chk_snapshot_price_non_negative"),
        CheckConstraint("mileage_km >= 0", name="chk_snapshot_mileage_non_negative"),
        CheckConstraint(
            "listing_status IN ('ACTIVE', 'PRICE_CHANGED', 'DELISTED', 'UNKNOWN')",
            name="chk_snapshot_status",
        ),
    )

    listing = relationship("Listing", back_populates="snapshots")


# ==============================================================================
# 시계열 데이터 불변성(Append-only) 강제 장치
# ==============================================================================

# 1. ORM 레벨 UPDATE/DELETE 차단
@event.listens_for(ListingSnapshot, "before_update")
def _prevent_orm_update(mapper, connection, target):
    raise ImmutableSnapshotError("ListingSnapshot is immutable and cannot be updated.")


@event.listens_for(ListingSnapshot, "before_delete")
def _prevent_orm_delete(mapper, connection, target):
    # 부모 매물이 DB에 여전히 존재하는 상태에서 스냅샷만 직접 삭제하려는 경우 차단
    res = connection.execute(
        text("SELECT 1 FROM listings WHERE listing_id = :lid"),
        {"lid": target.listing_id},
    ).scalar()
    if res is not None:
        raise ImmutableSnapshotError("ListingSnapshot is immutable and cannot be deleted directly.")


# 2. SQLite DB 트리거 정의 (DDL)
SQLITE_TRIGGER_UPDATE = """
CREATE TRIGGER IF NOT EXISTS trg_prevent_snapshot_update
BEFORE UPDATE ON listing_snapshots
BEGIN
    SELECT RAISE(ABORT, 'ListingSnapshot is immutable and cannot be updated.');
END;
"""

SQLITE_TRIGGER_DELETE = """
CREATE TRIGGER IF NOT EXISTS trg_prevent_snapshot_delete
BEFORE DELETE ON listing_snapshots
WHEN EXISTS (SELECT 1 FROM listings WHERE listing_id = OLD.listing_id)
BEGIN
    SELECT RAISE(ABORT, 'ListingSnapshot is immutable and direct deletion is prohibited.');
END;
"""

_trg_prevent_update_sqlite = DDL(SQLITE_TRIGGER_UPDATE)
_trg_prevent_delete_sqlite = DDL(SQLITE_TRIGGER_DELETE)

event.listen(
    ListingSnapshot.__table__,
    "after_create",
    _trg_prevent_update_sqlite.execute_if(dialect="sqlite"),
)
event.listen(
    ListingSnapshot.__table__,
    "after_create",
    _trg_prevent_delete_sqlite.execute_if(dialect="sqlite"),
)


def ensure_snapshot_immutability_triggers(engine_or_connection: Engine | Any) -> None:
    """기존 데이터베이스에 누락된 스냅샷 불변성 트리거를 무손실로 주입합니다.
    
    여러 번 호출해도 안전(멱등성)하며, 기존 데이터를 손상시키지 않습니다.
    """
    is_engine = isinstance(engine_or_connection, Engine)
    conn = engine_or_connection.connect() if is_engine else engine_or_connection
    try:
        if conn.dialect.name == "sqlite":
            conn.execute(text(SQLITE_TRIGGER_UPDATE))
            conn.execute(text(SQLITE_TRIGGER_DELETE))
            if is_engine:
                conn.commit()
    finally:
        if is_engine:
            conn.close()
