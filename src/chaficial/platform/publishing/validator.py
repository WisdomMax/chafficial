"""다중 플랫폼 등록 준비도 통합 검증 및 상태 전이 엔진 (DIRECTIVE 050 4항 & 5항)."""

from __future__ import annotations
import datetime
import json
from typing import Any
from sqlalchemy.orm import Session
from chaficial.platform.publishing.encar import EncarPlatformMapper
from chaficial.platform.publishing.kb import KbPlatformMapper
from chaficial.platform.publishing.carmanager import CarManagerPlatformMapper
from chaficial.platform.publishing.base import ReadinessReport
from chaficial.platform.db import Vehicle, PlatformPublishingRecord


class PublishingReadinessValidator:
    """3대 중고차 플랫폼 다중 등록 준비도 검사 및 라이프사이클 관리자."""

    # 허용된 상태 라이프사이클
    ALLOWED_STATUSES = [
        "DRAFT",
        "DATA_VERIFIED",
        "READY_TO_PUBLISH",
        "APPROVED",
        "EXPORTED",
        "PUBLISHED",
        "UPDATED",
        "SOLD",
        "UNPUBLISHED",
    ]

    def __init__(self):
        self.mappers = {
            "ENCAR": EncarPlatformMapper(),
            "KB_CHACHACHA": KbPlatformMapper(),
            "CAR_MANAGER": CarManagerPlatformMapper(),
        }

    def evaluate_vehicle_readiness(
        self, db: Session, vehicle: Vehicle, sync_db: bool = True
    ) -> dict[str, Any]:
        """차량 1대에 대한 3대 플랫폼별 준비도 종합 검사 및 원장 동기화."""
        reports: dict[str, ReadinessReport] = {}
        for platform_name, mapper in self.mappers.items():
            rep = mapper.validate_readiness(vehicle)
            reports[platform_name] = rep

            if sync_db:
                # DB PlatformPublishingRecord 동기화 (UPSERT)
                rec = (
                    db.query(PlatformPublishingRecord)
                    .filter(
                        PlatformPublishingRecord.vehicle_id == vehicle.id,
                        PlatformPublishingRecord.platform == platform_name,
                    )
                    .first()
                )
                if not rec:
                    rec = PlatformPublishingRecord(
                        vehicle_id=vehicle.id,
                        platform=platform_name,
                        publishing_status="READY_TO_PUBLISH" if rep.is_ready else "DRAFT",
                        is_ready=rep.is_ready,
                        missing_fields_json=json.dumps(rep.missing_fields, ensure_ascii=False),
                        warnings_json=json.dumps(rep.warnings, ensure_ascii=False),
                        mapped_payload_json=json.dumps(rep.mapped_payload, ensure_ascii=False),
                        last_validated_at=datetime.datetime.utcnow(),
                    )
                    db.add(rec)
                else:
                    rec.is_ready = rep.is_ready
                    rec.missing_fields_json = json.dumps(rep.missing_fields, ensure_ascii=False)
                    rec.warnings_json = json.dumps(rep.warnings, ensure_ascii=False)
                    rec.mapped_payload_json = json.dumps(rep.mapped_payload, ensure_ascii=False)
                    rec.last_validated_at = datetime.datetime.utcnow()
                    if rep.is_ready and rec.publishing_status == "DRAFT":
                        rec.publishing_status = "READY_TO_PUBLISH"
                    elif not rep.is_ready and rec.publishing_status == "READY_TO_PUBLISH":
                        rec.publishing_status = "DRAFT"

        # 종합 상태 산출
        ready_count = sum(1 for r in reports.values() if r.is_ready)
        overall_ready = ready_count > 0

        summary = {
            "vehicle_id": vehicle.id,
            "plate_number": vehicle.plate_number,
            "model_name": vehicle.model_name,
            "current_publishing_status": getattr(vehicle, "publishing_status", "DRAFT"),
            "total_platforms": len(self.mappers),
            "ready_platform_count": ready_count,
            "overall_ready": overall_ready,
            "platforms": {k: v.to_dict() for k, v in reports.items()},
            "evaluated_at": datetime.datetime.utcnow().isoformat(),
        }

        if sync_db:
            vehicle.platform_readiness_json = json.dumps(summary, ensure_ascii=False)
            db.commit()

        return summary

    def transition_publishing_status(
        self, db: Session, vehicle: Vehicle, target_status: str, notes: str = ""
    ) -> dict[str, Any]:
        """차량의 플랫폼 게시 라이프사이클 상태 전이 및 가드 검증 (DIRECTIVE 050 5항)."""
        target_status = target_status.upper().strip()
        if target_status not in self.ALLOWED_STATUSES:
            raise ValueError(
                f"유효하지 않은 게시 상태입니다: '{target_status}'. 허용: {self.ALLOWED_STATUSES}"
            )

        current_status = getattr(vehicle, "publishing_status", "DRAFT")

        # 전이 가드 규칙
        if target_status == "READY_TO_PUBLISH":
            readiness = self.evaluate_vehicle_readiness(db, vehicle, sync_db=False)
            if not readiness["overall_ready"]:
                raise ValueError("등록 준비 상태 전이 차단: 최소 1개 이상 플랫폼의 등록 필수 요건을 통과해야 합니다.")

        elif target_status == "APPROVED":
            # 딜러 권한 확인
            ownership = getattr(vehicle, "ownership_type", "CHAMART_OWNED")
            if ownership in ["PARTNER_APPROVED", "PARTNER_CANDIDATE"]:
                rights = getattr(vehicle, "rights_ledgers", []) or []
                has_rights = any(not getattr(r, "is_revoked", False) for r in rights)
                if not has_rights:
                    raise ValueError("승인 전이 차단: 제휴 딜러의 유효한 광고 권한 승인이 필요합니다.")
            elif ownership == "MARKET_OBSERVED":
                raise ValueError("승인 전이 차단: 시장 관측 매물은 다중 플랫폼 게시 승인이 불가합니다.")

        elif target_status == "PUBLISHED":
            # 실제 승인된 외부 공식 연동 플랫폼이 없는 상태에서 임의 PUBLISHED 설정 방지
            raise ValueError(
                "실제 게시 차단: 현재 외부 플랫폼 공식 API 제휴 연동 계약이 활성화되지 않았습니다. "
                "'EXPORTED' (내보내기 완료) 또는 'APPROVED' (승인 완료) 상태로 관리하십시오 (가짜 게시 보고 금지 원칙)."
            )

        # 상태 갱신
        vehicle.publishing_status = target_status
        vehicle.updated_at = datetime.datetime.utcnow()

        # 이력 타임라인 기록
        try:
            tl = json.loads(getattr(vehicle, "timeline_json", "[]") or "[]")
        except Exception:
            tl = []
        tl.append({
            "event": "PUBLISHING_STATUS_CHANGED",
            "from": current_status,
            "to": target_status,
            "notes": notes,
            "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        })
        vehicle.timeline_json = json.dumps(tl, ensure_ascii=False)

        db.commit()

        return {
            "vehicle_id": vehicle.id,
            "plate_number": vehicle.plate_number,
            "previous_status": current_status,
            "current_status": target_status,
            "notes": notes,
            "updated_at": vehicle.updated_at.isoformat(),
        }
