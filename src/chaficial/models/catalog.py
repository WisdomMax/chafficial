"""한국형 차량 카탈로그 및 분류 모델."""


from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from chaficial.database.base import Base


class VehicleCatalog(Base):
    """한국 중고차 표준 분류 체계.
    
    제조사, 모델, 세대(Generation), 페이스리프트 여부, 세부 트림을 정규화하여 관리합니다.
    예: 현대 아반떼 AD vs 더 뉴 아반떼 CN7
    """
    __tablename__ = "vehicle_catalog"

    catalog_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    manufacturer: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    generation: Mapped[str] = mapped_column(String(50), nullable=False)  # 예: "AD", "CN7"
    is_facelift: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sub_model: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 예: "더 뉴 아반떼 CN7"
    trim: Mapped[str] = mapped_column(String(50), nullable=False)  # 예: "모던", "인스퍼레이션"
    model_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fuel_type: Mapped[str] = mapped_column(String(30), nullable=False)  # 가솔린, 디젤, LPG, 하이브리드, 전기 등
    transmission: Mapped[str] = mapped_column(String(30), nullable=False, default="오토")
    displacement_cc: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seating_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint("model_year >= 1970 AND model_year <= 2050", name="chk_catalog_year"),
        CheckConstraint("displacement_cc IS NULL OR displacement_cc >= 0", name="chk_catalog_displacement"),
        CheckConstraint("seating_capacity IS NULL OR seating_capacity > 0", name="chk_catalog_seating"),
    )

    def full_name(self) -> str:
        facelift_prefix = "더 뉴 " if self.is_facelift else ""
        return f"{self.manufacturer} {facelift_prefix}{self.model_name} {self.generation} {self.trim} ({self.model_year}년식)"
