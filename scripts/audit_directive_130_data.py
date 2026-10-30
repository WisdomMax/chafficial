"""
DIRECTIVE 130 TASK 1: 전수 데이터 감사 스크립트
로컬 SQLite vs Cloudflare D1
"""

import sqlite3
import subprocess
import json

def get_local_stats():
    conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
    c = conn.cursor()
    
    stats = {}
    
    # 1. Tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    stats["tables"] = [r[0] for r in c.fetchall()]
    
    # 2. Vehicles
    c.execute("SELECT count(*) FROM vehicles;")
    stats["vehicles_total"] = c.fetchone()[0]
    
    c.execute("SELECT count(*) FROM vehicles WHERE is_demo = 1;")
    stats["vehicles_demo"] = c.fetchone()[0]
    
    c.execute("SELECT count(*) FROM vehicles WHERE is_demo = 0 OR is_demo IS NULL;")
    stats["vehicles_real_or_market"] = c.fetchone()[0]
    
    c.execute("SELECT listing_ownership_type, count(*) FROM vehicles GROUP BY listing_ownership_type;")
    stats["vehicles_by_ownership"] = dict(c.fetchall())
    
    c.execute("SELECT status, count(*) FROM vehicles GROUP BY status;")
    stats["vehicles_by_status"] = dict(c.fetchall())
    
    c.execute("SELECT is_public, count(*) FROM vehicles GROUP BY is_public;")
    stats["vehicles_by_is_public"] = dict(c.fetchall())
    
    # 3. Photos
    c.execute("SELECT count(*) FROM vehicle_photos;")
    stats["photos_total"] = c.fetchone()[0]
    
    # 4. Business data
    for tbl in ["consultations", "transactions", "dealer_rights_ledgers", "customers", "users"]:
        if tbl in stats["tables"]:
            c.execute(f"SELECT count(*) FROM {tbl};")
            stats[f"{tbl}_count"] = c.fetchone()[0]
        else:
            stats[f"{tbl}_count"] = 0
            
    conn.close()
    return stats

def get_d1_stats():
    stats = {}
    
    # Run queries via wrangler
    queries = {
        "vehicles_total": "SELECT count(*) FROM vehicles;",
        "vehicles_demo": "SELECT count(*) FROM vehicles WHERE is_demo = 1;",
        "vehicles_real": "SELECT count(*) FROM vehicles WHERE is_demo = 0 OR is_demo IS NULL;",
        "vehicles_ownership": "SELECT listing_ownership_type, count(*) FROM vehicles GROUP BY listing_ownership_type;",
        "vehicles_status": "SELECT status, count(*) FROM vehicles GROUP BY status;",
        "vehicles_is_public": "SELECT is_public, count(*) FROM vehicles GROUP BY is_public;",
        "photos_total": "SELECT count(*) FROM vehicle_photos;",
        "photos_demo": "SELECT count(*) FROM vehicle_photos WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 1);",
        "photos_real": "SELECT count(*) FROM vehicle_photos WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 0 OR is_demo IS NULL);",
        "consultations_count": "SELECT count(*) FROM consultations;",
        "transactions_count": "SELECT count(*) FROM transactions;",
        "dealer_rights_ledgers_count": "SELECT count(*) FROM dealer_rights_ledgers;",
        "customers_count": "SELECT count(*) FROM customers;",
        "users_count": "SELECT count(*) FROM users;"
    }
    
    combined_sql = ";\n".join([f"{v.rstrip(';')}" for v in queries.values()]) + ";"
    cmd = ["npx", "-y", "wrangler", "d1", "execute", "chamart-db", "--remote", "--json", f"--command={combined_sql}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    try:
        data = json.loads(res.stdout)
        keys = list(queries.keys())
        for i, k in enumerate(keys):
            if i < len(data):
                stats[k] = data[i].get("results", [])
    except Exception as e:
        print("D1 query parse error:", e, res.stdout[:300])
        
    return stats

if __name__ == "__main__":
    print("[*] Local DB 감사 중...")
    local = get_local_stats()
    print("[*] D1 DB 감사 중...")
    d1 = get_d1_stats()
    
    report = {
        "local": local,
        "d1": d1
    }
    
    with open("reports/DIRECTIVE_130_DATA_AUDIT.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    print("[+] 감사 완료: reports/DIRECTIVE_130_DATA_AUDIT.json 저장 완료")
    print("\n--- LOCAL DB 요약 ---")
    print(f"차량 총: {local['vehicles_total']} (데모: {local['vehicles_demo']}, 실차/시장: {local['vehicles_real_or_market']})")
    print(f"소유 구분: {local['vehicles_by_ownership']}")
    print(f"공개 여부: {local['vehicles_by_is_public']}")
    print(f"상담: {local.get('consultations_count')}, 거래: {local.get('transactions_count')}")
    
    print("\n--- D1 REMOTE DB 요약 ---")
    print(f"차량 총: {d1.get('vehicles_total')}")
    print(f"데모 차량: {d1.get('vehicles_demo')}")
    print(f"실차 차량: {d1.get('vehicles_real')}")
    print(f"소유 구분: {d1.get('vehicles_ownership')}")
    print(f"공개 여부: {d1.get('vehicles_is_public')}")
    print(f"사진 총: {d1.get('photos_total')} (데모: {d1.get('photos_demo')}, 실차: {d1.get('photos_real')})")
    print(f"상담: {d1.get('consultations_count')}, 거래: {d1.get('transactions_count')}")
