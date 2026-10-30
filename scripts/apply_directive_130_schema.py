"""
DIRECTIVE 130 TASK 4: AI 차량등록 확장 스키마 마이그레이션 (안전 추가)
DROP TABLE 등 파괴적 쿼리 절대 금지. 기존 데이터 100% 보존.
"""

import sqlite3
import subprocess
import json

def apply_local():
    conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
    c = conn.cursor()
    
    # 1. vehicles 테이블 컬럼 추가
    c.execute("PRAGMA table_info(vehicles);")
    existing_cols = [r[1] for r in c.fetchall()]
    
    ai_cols = [
        ("ai_vision_analysis_json", "TEXT DEFAULT '{}'"),
        ("ai_recommended_primary_photo", "TEXT"),
        ("ai_confidence_score", "REAL DEFAULT 0.0"),
        ("ai_review_status", "VARCHAR(30) DEFAULT 'MANUAL'")
    ]
    
    for col_name, col_type in ai_cols:
        if col_name not in existing_cols:
            print(f"[Local] Adding column {col_name} to vehicles...")
            c.execute(f"ALTER TABLE vehicles ADD COLUMN {col_name} {col_type};")
            
    # 2. vehicle_photos 테이블 컬럼 추가
    c.execute("PRAGMA table_info(vehicle_photos);")
    p_cols = [r[1] for r in c.fetchall()]
    
    ai_p_cols = [
        ("ai_classification", "VARCHAR(50)"),
        ("ai_confidence", "REAL DEFAULT 0.0")
    ]
    
    for col_name, col_type in ai_p_cols:
        if col_name not in p_cols:
            print(f"[Local] Adding column {col_name} to vehicle_photos...")
            c.execute(f"ALTER TABLE vehicle_photos ADD COLUMN {col_name} {col_type};")
            
    conn.commit()
    conn.close()
    print("[+] Local DB AI 확장 스키마 적용 완료!")

def apply_d1():
    # D1 컬럼 확인
    cmd = ["npx", "-y", "wrangler", "d1", "execute", "chamart-db", "--remote", "--json", "--command=PRAGMA table_info(vehicles);"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(res.stdout)
        existing_cols = [r["name"] for r in data[0]["results"]]
    except Exception:
        existing_cols = []
        
    ai_cols = [
        ("ai_vision_analysis_json", "TEXT DEFAULT '{}'"),
        ("ai_recommended_primary_photo", "TEXT"),
        ("ai_confidence_score", "REAL DEFAULT 0.0"),
        ("ai_review_status", "VARCHAR(30) DEFAULT 'MANUAL'")
    ]
    
    for col_name, col_type in ai_cols:
        if col_name not in existing_cols:
            print(f"[D1] Adding column {col_name} to vehicles...")
            sql = f"ALTER TABLE vehicles ADD COLUMN {col_name} {col_type};"
            cmd = ["npx", "-y", "wrangler", "d1", "execute", "chamart-db", "--remote", f"--command={sql}"]
            subprocess.run(cmd, check=True)
            
    # vehicle_photos
    cmd = ["npx", "-y", "wrangler", "d1", "execute", "chamart-db", "--remote", "--json", "--command=PRAGMA table_info(vehicle_photos);"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(res.stdout)
        p_cols = [r["name"] for r in data[0]["results"]]
    except Exception:
        p_cols = []
        
    ai_p_cols = [
        ("ai_classification", "VARCHAR(50)"),
        ("ai_confidence", "REAL DEFAULT 0.0")
    ]
    
    for col_name, col_type in ai_p_cols:
        if col_name not in p_cols:
            print(f"[D1] Adding column {col_name} to vehicle_photos...")
            sql = f"ALTER TABLE vehicle_photos ADD COLUMN {col_name} {col_type};"
            cmd = ["npx", "-y", "wrangler", "d1", "execute", "chamart-db", "--remote", f"--command={sql}"]
            subprocess.run(cmd, check=True)
            
    print("[+] D1 DB AI 확장 스키마 적용 완료!")

if __name__ == "__main__":
    apply_local()
    apply_d1()
