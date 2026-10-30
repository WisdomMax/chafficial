import sqlite3
import json

def audit_restoration_exact_match():
    print("=== [TASK 1] DIRECTIVE 117: 백업본 대조 정상 매물 5건 복원 정밀 무결성 검증 ===")
    
    backup_db = "data/chamart/backups/chamart_online_backup_directive115_20261030_234504.db"
    prod_db = "data/chamart/chamart_platform_demo.db"

    b_conn = sqlite3.connect(backup_db)
    b_c = b_conn.cursor()

    p_conn = sqlite3.connect(prod_db)
    p_c = p_conn.cursor()

    restore_ids = [
        "KB5+r92iDSPMPoF29e/9mA==",
        "kBYAJHA7MyKZsNQYunZImQ==",
        "kBLkL1Hq/p3sxNUvcVR+GA==",
        "kBG+SmFwDEEas0uMhdq/sw==",
        "encar_sw_102938"
    ]

    verified_records = []
    for lid in restore_ids:
        b_c.execute("SELECT * FROM vehicle_listings WHERE listing_id = ?", (lid,))
        b_row = b_c.fetchone()
        col_names = [d[0] for d in b_c.description]
        b_dict = dict(zip(col_names, b_row))

        p_c.execute("SELECT * FROM vehicle_listings WHERE listing_id = ?", (lid,))
        p_row = p_c.fetchone()
        p_dict = dict(zip(col_names, p_row))

        # 컬럼별 100% 일치 확인
        mismatches = []
        for k in col_names:
            if b_dict[k] != p_dict[k]:
                mismatches.append(f"{k}: backup='{b_dict[k]}' vs prod='{p_dict[k]}'")

        assert len(mismatches) == 0, f"불일치 발생: {mismatches}"
        
        # vehicles 테이블과의 FK 연결 유효성 검증
        p_c.execute("SELECT id, plate_number, model_name FROM vehicles WHERE id = ?", (p_dict["vehicle_id"],))
        veh_row = p_c.fetchone()
        assert veh_row is not None, f"외래키 연결 실패! vehicle_id: {p_dict['vehicle_id']}"

        print(f"[+] 100% 일치 확인: {p_dict['platform']} | ID: {lid} | Vehicle: {veh_row[0]} ({veh_row[2]})")
        verified_records.append({
            "listing_id": lid,
            "platform": p_dict["platform"],
            "vehicle_id": p_dict["vehicle_id"],
            "model_name": veh_row[2],
            "all_columns_matched": True
        })

    # PRAGMA 점검
    p_c.execute("PRAGMA integrity_check;")
    assert p_c.fetchall() == [("ok",)]
    p_c.execute("PRAGMA foreign_key_check;")
    assert len(p_c.fetchall()) == 0

    # 고객, 상담, 거래 데이터 보존 확인
    p_c.execute("SELECT count(*) FROM customers;")
    cust_cnt = p_c.fetchone()[0]
    p_c.execute("SELECT count(*) FROM consultations;")
    cons_cnt = p_c.fetchone()[0]
    p_c.execute("SELECT count(*) FROM transactions;")
    tx_cnt = p_c.fetchone()[0]

    assert cust_cnt == 28, f"고객 데이터 손실: {cust_cnt} != 28"
    assert cons_cnt == 29, f"상담 데이터 손실: {cons_cnt} != 29"
    assert tx_cnt == 37, f"거래 데이터 손실: {tx_cnt} != 37"
    print(f"\n[+] 핵심 영업 데이터 100% 무손실 보존: Customers={cust_cnt}, Consultations={cons_cnt}, Transactions={tx_cnt}")

    evidence = {
        "verified_at": "2026-10-31T00:03:00+09:00",
        "verified_count": len(verified_records),
        "records": verified_records,
        "integrity_check": "ok",
        "foreign_key_violations": 0,
        "core_entities": {
            "customers": cust_cnt,
            "consultations": cons_cnt,
            "transactions": tx_cnt
        }
    }
    with open("scratch/task1_restoration_final_evidence.json", "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)

    print("[+] TASK 1 증적 scratch/task1_restoration_final_evidence.json 저장 완료!")
    b_conn.close()
    p_conn.close()

if __name__ == "__main__":
    audit_restoration_exact_match()
