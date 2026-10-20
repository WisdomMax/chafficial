"""데이터베이스 스키마 무손실 마이그레이션 모듈.

구버전 SQLite 데이터베이스의 기존 데이터와 스냅샷을 100% 보존하면서
최신 스키마(신규 컬럼, 신규 테이블, 불변성 트리거)로 안전하게 업그레이드합니다.
역사적 사실 왜곡을 방지하며 모든 마이그레이션 작업은 멱등성(Idempotent)을 보장합니다.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, text

from chaficial.models.candidate import ensure_candidate_history_triggers
from chaficial.models.snapshot import ensure_snapshot_immutability_triggers


def get_table_columns(connection: Any, table_name: str) -> set[str]:
    """SQLite 테이블의 컬럼 목록을 조회합니다."""
    result = connection.execute(text(f"PRAGMA table_info({table_name});")).fetchall()
    return {row[1] for row in result}


def table_exists(connection: Any, table_name: str) -> bool:
    """테이블 존재 여부를 확인합니다."""
    result = connection.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name;"),
        {"name": table_name},
    ).scalar()
    return result is not None


def inspect_foreign_keys(connection: Any, table_name: str) -> list[dict[str, Any]]:
    """테이블의 외래키 제약조건 목록을 조회합니다."""
    result = connection.execute(text(f"PRAGMA foreign_key_list({table_name});")).fetchall()
    return [
        {
            "id": row[0],
            "seq": row[1],
            "table": row[2],
            "from": row[3],
            "to": row[4],
            "on_update": row[5],
            "on_delete": row[6],
            "match": row[7],
        }
        for row in result
    ]


def migrate_database(
    engine_or_connection: Engine | Any, migration_time: datetime | None = None
) -> dict[str, Any]:
    """기존 데이터베이스를 데이터 무손실로 최신 스키마로 업그레이드합니다.
    
    작업 내역:
    1. listing_snapshots: normalized_region_id 컬럼 추가 (기존 데이터는 미확정 None으로 보존)
    2. sales_candidates: created_at 컬럼 추가 (기존 데이터는 보수적으로 migration_time 또는 selected_at 활용)
    3. candidate_status_histories 테이블 생성 (승인 상태 시계열 이력 테이블)
    4. 기존 후보 매물에 대해 초기 상태 이력 동기화
       - [역사적 정확성 보존]: 원래의 승인 시점이 입증되지 않는 기존 상태는 과거의 승인 사실로 날조하지 않고
         마이그레이션 실행 시점(migration_time)으로 등록하여 과거 시점 조회 시 미확정으로 안전하게 격리합니다.
    5. 스냅샷 및 후보 상태 이력 불변성/삭제 차단 최신 트리거 주입
    
    Returns:
        dict: 마이그레이션 적용 결과 리포트
    """
    is_engine = isinstance(engine_or_connection, Engine)
    conn = engine_or_connection.connect() if is_engine else engine_or_connection
    trans = conn.begin() if not conn.in_transaction() else None

    applied_changes: list[str] = []
    run_time = migration_time or datetime.now(UTC)
    run_time_str = run_time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        # 1. listing_snapshots 스키마 검사 및 보완
        if table_exists(conn, "listing_snapshots"):
            snap_cols = get_table_columns(conn, "listing_snapshots")
            if "normalized_region_id" not in snap_cols:
                conn.execute(
                    text("ALTER TABLE listing_snapshots ADD COLUMN normalized_region_id VARCHAR(50);")
                )
                applied_changes.append("listing_snapshots: added normalized_region_id column")

        # 2. sales_candidates 스키마 검사 및 보완
        # [역사적 정확성 보존]: 원본 시스템 적재 시점이 불명확한 구버전 후보의 created_at을
        # 과거 selected_at으로 임의 소급하지 않고, 보수적으로 마이그레이션 시점(run_time_str)으로 기록
        if table_exists(conn, "sales_candidates"):
            cand_cols = get_table_columns(conn, "sales_candidates")
            if "created_at" not in cand_cols:
                conn.execute(
                    text("ALTER TABLE sales_candidates ADD COLUMN created_at TIMESTAMP;")
                )
                conn.execute(
                    text(f"UPDATE sales_candidates SET created_at = '{run_time_str}' WHERE created_at IS NULL;")
                )
                applied_changes.append("sales_candidates: added created_at column (set to migration time for legacy data)")

        # 3. candidate_status_histories 테이블 생성
        if not table_exists(conn, "candidate_status_histories"):
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS candidate_status_histories (
                    history_id VARCHAR(36) PRIMARY KEY,
                    candidate_id VARCHAR(36) NOT NULL REFERENCES sales_candidates(candidate_id) ON DELETE RESTRICT,
                    partner_review_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
                    availability_status VARCHAR(30) NOT NULL DEFAULT 'UNCONFIRMED',
                    changed_at TIMESTAMP NOT NULL,
                    ingested_at TIMESTAMP NOT NULL,
                    review_note VARCHAR(500)
                );
            """))
            applied_changes.append("created table: candidate_status_histories")

            # 인덱스 생성
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_candidate_status_histories_candidate_id 
                ON candidate_status_histories(candidate_id);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_candidate_status_histories_changed_at 
                ON candidate_status_histories(changed_at);
            """))

        # 4. 기존 sales_candidates의 초기 상태 이력 동기화
        # [역사적 정확성 보존]: 기존 승인 상태를 과거 시점에 알고 있었다고 날조하지 않고,
        # 마이그레이션 실행 시각(run_time) 기준으로 최초 적재하여 과거 의사결정 재현 시 누출을 원천 차단
        if table_exists(conn, "sales_candidates") and table_exists(conn, "candidate_status_histories"):
            conn.execute(text(f"""
                INSERT INTO candidate_status_histories (
                    history_id, candidate_id, partner_review_status, availability_status, changed_at, ingested_at, review_note
                )
                SELECT 
                    'migrated-hist-' || candidate_id,
                    candidate_id,
                    partner_review_status,
                    availability_status,
                    '{run_time_str}',
                    '{run_time_str}',
                    '구버전 DB 마이그레이션 동기화 (역사적 승인 시점 미확정)'
                FROM sales_candidates
                WHERE candidate_id NOT IN (SELECT DISTINCT candidate_id FROM candidate_status_histories);
            """))

        # 5. 스냅샷 불변성 및 삭제 차단 최신 트리거 주입
        ensure_snapshot_immutability_triggers(conn)
        applied_changes.append("ensured immutable snapshot triggers")

        # 6. 후보 상태 이력 불변성 및 삭제 차단 최신 트리거 주입
        ensure_candidate_history_triggers(conn)
        applied_changes.append("ensured immutable candidate history triggers")

        if trans:
            trans.commit()

        return {
            "success": True,
            "applied_changes": applied_changes,
            "message": f"Successfully applied {len(applied_changes)} migration step(s).",
        }

    except Exception as e:  # noqa: BLE001
        if trans:
            trans.rollback()
        return {
            "success": False,
            "error": str(e),
            "applied_changes": applied_changes,
            "message": f"Migration failed: {e}",
        }
    finally:
        if is_engine:
            conn.close()
