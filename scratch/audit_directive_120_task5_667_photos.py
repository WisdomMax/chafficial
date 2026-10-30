"""
TASK 5: 병합 대상 74개 그룹의 사진 667건 전수 무손실 1:1 대조 감사 (ISSUE-65)
- 백업본(chamart_pre_consolidation_20261031_000308.db) vs 현재 운영 DB(chamart_platform_demo.db)
- 667건 전수 ID, URL, 이전된 vehicle_id, 공개/승인/영상사용 권한 1:1 대조
- 결과 증적 JSON: scratch/task5_667_photos_full_reconciliation.json
"""

import sqlite3
import json
from pathlib import Path

BACKUP_DB = "data/chamart/backups/chamart_pre_consolidation_20261031_000308.db"
CURRENT_DB = "data/chamart/chamart_platform_demo.db"
EVIDENCE_JSON = "scratch/task5_667_photos_full_reconciliation.json"

def audit_667_photos():
    print("=== [TASK 5] 사진 667건 전수 1:1 무손실 대조 감사 시작 ===")
    assert Path(BACKUP_DB).exists(), f"Backup DB {BACKUP_DB} not found!"
    assert Path(CURRENT_DB).exists(), f"Current DB {CURRENT_DB} not found!"

    # 1. 백업본에서 74개 중복 그룹 추출 및 duplicate_vehicle_id 식별
    conn_b = sqlite3.connect(BACKUP_DB)
    cb = conn_b.cursor()

    cb.execute("""
        SELECT listing_id, count(*) as cnt, group_concat(vehicle_id)
        FROM vehicle_listings
        WHERE platform = 'CARMANAGER'
        GROUP BY listing_id
        HAVING cnt > 1
    """)
    groups = cb.fetchall()
    print(f"[1] 백업본 74개 중복 그룹 확인: {len(groups)}개")
    assert len(groups) == 74

    duplicate_veh_ids = []
    canonical_veh_ids = {}

    for row in groups:
        v_ids = row[2].split(",")
        placeholders = ",".join(["?"] * len(v_ids))
        cb.execute(f"SELECT id, status, created_at FROM vehicles WHERE id IN ({placeholders})", v_ids)
        vehs = cb.fetchall()
        
        # 병합 로직과 동일하게 canonical 선정
        owned = next((v for v in vehs if v[1] in ('AVAILABLE', 'FOR_SALE')), None)
        draft = next((v for v in vehs if v[1] == 'DRAFT'), None)
        if owned and draft:
            canon = owned[0]
            dup = draft[0]
        else:
            sorted_v = sorted(vehs, key=lambda x: x[2])
            canon = sorted_v[0][0]
            dup = sorted_v[1][0]
        
        duplicate_veh_ids.append(dup)
        canonical_veh_ids[dup] = canon

    # 2. 백업본에서 duplicate_vehicle_id에 소속되어 있던 사진 667건 전수 조회
    dup_placeholders = ",".join(["?"] * len(duplicate_veh_ids))
    cb.execute(f"""
        SELECT id, vehicle_id, photo_url, category, allow_video_use, public_visibility, approval_status
        FROM vehicle_photos
        WHERE vehicle_id IN ({dup_placeholders})
        ORDER BY id
    """, duplicate_veh_ids)
    backup_photos = cb.fetchall()
    conn_b.close()

    print(f"[2] 백업본 중복 마스터에 연결되어 있던 사진 총수: {len(backup_photos)}장 (정확히 667장)")
    assert len(backup_photos) == 667, f"사진 수가 667장이 아님: {len(backup_photos)}"

    # 3. 현재 운영 DB에서 해당 사진 667장 전수 조회
    conn_c = sqlite3.connect(CURRENT_DB)
    cc = conn_c.cursor()

    photo_ids = [p[0] for p in backup_photos]
    p_placeholders = ",".join(["?"] * len(photo_ids))
    cc.execute(f"""
        SELECT id, vehicle_id, photo_url, category, allow_video_use, public_visibility, approval_status
        FROM vehicle_photos
        WHERE id IN ({p_placeholders})
        ORDER BY id
    """, photo_ids)
    current_photos = cc.fetchall()
    conn_c.close()

    print(f"[3] 현재 운영 DB에서 조회된 해당 사진 총수: {len(current_photos)}장")
    assert len(current_photos) == 667, f"운영 DB 사진 수가 667장이 아님: {len(current_photos)}"

    # 4. 667건 전수 1:1 대조
    curr_map = {row[0]: row for row in current_photos}
    reconciliation_details = []

    mismatches = 0
    migrated_correctly = 0

    for bp in backup_photos:
        p_id = bp[0]
        orig_veh = bp[1]
        orig_url = bp[2]
        orig_cat = bp[3]
        orig_video = bp[4]
        orig_vis = bp[5]
        orig_appr = bp[6]

        cp = curr_map.get(p_id)
        assert cp is not None, f"사진 ID {p_id} 유실!"

        curr_veh = cp[1]
        curr_url = cp[2]
        curr_cat = cp[3]
        curr_video = cp[4]
        curr_vis = cp[5]
        curr_appr = cp[6]

        expected_canon_veh = canonical_veh_ids[orig_veh]

        # 검증: vehicle_id가 대표 마스터로 안전 이전되었는지
        assert curr_veh == expected_canon_veh, f"Vehicle ID 불일치! 기대: {expected_canon_veh}, 실제: {curr_veh}"
        # 검증: 원본 URL 100% 동일
        assert curr_url == orig_url, "Photo URL 불일치!"
        # 검증: 권한 및 상태 보존
        assert curr_video == orig_video, "allow_video_use 불일치!"
        assert curr_vis == orig_vis, "public_visibility 불일치!"
        assert curr_appr == orig_appr, "approval_status 불일치!"

        migrated_correctly += 1
        reconciliation_details.append({
            "photo_id": p_id,
            "original_vehicle_id": orig_veh,
            "target_canonical_vehicle_id": curr_veh,
            "url_preserved": True,
            "category": curr_cat,
            "allow_video_use": curr_video,
            "public_visibility": curr_vis,
            "approval_status": curr_appr
        })

    evidence = {
        "directive": "CHA-FICIAL DIRECTIVE 120 TASK 5",
        "audit_timestamp": "2026-10-31T00:37:00+09:00",
        "total_audited_photos": len(backup_photos),
        "total_preserved_in_current_db": len(current_photos),
        "loss_count": 0,
        "perfect_match_count": migrated_correctly,
        "audit_verdict": "PERFECT_100_PERCENT_LOSSLESS_RECONCILIATION",
        "all_667_items": reconciliation_details
    }

    with open(EVIDENCE_JSON, "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)

    print(f"[+] 667건 전수 1:1 대조 완료: 무손실 667 / 667건 (100% 일치)")
    print(f"[+] 증적 파일 저장: {EVIDENCE_JSON}")

if __name__ == "__main__":
    audit_667_photos()
