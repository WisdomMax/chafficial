"""pytest 공통 fixtures."""

import pytest
from sqlalchemy.orm import Session

from chaficial.database.base import Base, get_engine, get_session_factory
from chaficial.synthetic.generator import SyntheticDataGenerator


@pytest.fixture
def db_session() -> Session:
    """테스트용 격리된 SQLite In-Memory 세션을 제공합니다."""
    engine = get_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session_factory = get_session_factory(engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def seeded_db(db_session: Session) -> Session:
    """120건 이상의 다양한 한국형 합성 데이터가 적재된 DB 세션을 제공합니다."""
    gen = SyntheticDataGenerator(session=db_session, seed=123)
    gen.generate_all(target_count=120)
    return db_session
