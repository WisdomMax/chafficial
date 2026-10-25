#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 048 P0-1 무사고 의심 레코드 감사 및 격리 스크립트.

공인 성능점검기록부나 카히스토리 공식 증빙 없이 단순 고지 또는 임의 주입으로
CLEAN 상태가 부여된 차량을 감사하고, UNCHECKED(검증 대기) 상태로 격리하며 수정 이력을 보존합니다.
"""

import json
import os
import sys
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from chaficial.platform.db import SessionLocal, Vehicle

def audit_and_quarantine():
    db = SessionLocal()
    try:
        vehicles = db.query(Vehicle).all()
        quarantine_list = []
        updated_count = 0

        for v in vehicles:
            acc = json.loads(v.accident_history_json or "{}")
            current_state = acc.get("accident_state", "UNCHECKED")
            verified_source = acc.get("verified_source", "")
            verified_at = acc.get("verified_at")

            # 공식 검증 증빙이 없는데 CLEAN 또는 NO_ACCIDENT로 표기된 경우 격리 대상
            is_suspicious = False
            if current_state in ["CLEAN", "NO_ACCIDENT"]:
                if not verified_at or "딜러 고지" in verified_source or "미조회" in verified_source or not verified_source:
                    is_suspicious = True

            if is_suspicious:
                original_history = dict(acc)
                # 감사 로그 생성
                log_entry = {
                    "vehicle_id": v.id,
                    "plate_number": v.plate_number,
                    "model_name": v.model_name,
                    "original_state": current_state,
                    "original_source": verified_source,
                    "quarantined_at": datetime.utcnow().isoformat(),
                    "reason": "공인 증빙 문서 부재 상태에서 CLEAN 표기된 출처 불명 레코드 격리 (DIRECTIVE 048 P0-1)",
                }
                quarantine_list.append(log_entry)

                # UNCHECKED 상태로 안전 격리 및 수정 이력 보존
                acc["accident_state"] = "UNCHECKED"
                acc["frame_damage"] = "미확인 (성능점검 대기)"
                acc["outer_panel_exchange"] = "미확인 (성능점검 대기)"
                acc["verified_source"] = f"검증 대기 격리 (이전 고지: {verified_source or '출처없음'})"
                acc["audit_history"] = {
                    "quarantined": True,
                    "quarantined_at": datetime.utcnow().isoformat(),
                    "previous_unverified_record": original_history,
                }
                v.accident_history_json = json.dumps(acc, ensure_ascii=False)
                updated_count += 1

        db.commit()

        # 감사 보고서 저장
        report_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "audit_unverified_accidents.json",
        )
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "audit_timestamp": datetime.utcnow().isoformat(),
                "total_vehicles_audited": len(vehicles),
                "quarantined_count": updated_count,
                "quarantined_records": quarantine_list,
            }, f, ensure_ascii=False, indent=2)

        print(f"[*] 감사 완료: 총 {len(vehicles)}대 차량 점검, {updated_count}대 의심 차량 UNCHECKED 격리 완료.")
        print(f"[*] 감사 보고서 저장됨: {report_path}")

    finally:
        db.close()

if __name__ == "__main__":
    audit_and_quarantine()
