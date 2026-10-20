"""데이터베이스 연결 및 베이스 클래스 정의.

SQLAlchemy 2.x 표준 Base 및 엔진 팩토리를 제공합니다.
"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """모든 데이터 모델의 공통 베이스 클래스."""


def get_engine(db_url: str = "sqlite:///:memory:", echo: bool = False):
    """지정된 URL에 대한 SQLAlchemy 엔진을 생성합니다.
    
    SQLite 사용 시 외래 키(Foreign Key) 제약조건 활성화를 강제합니다.
    """
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(db_url, echo=echo, connect_args=connect_args)

    if db_url.startswith("sqlite"):
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_session_factory(engine) -> sessionmaker[Session]:
    """엔진에 연결된 Session 팩토리를 반환합니다."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """트랜잭션 컨텍스트 매니저."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
