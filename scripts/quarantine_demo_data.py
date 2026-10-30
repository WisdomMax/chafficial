"""
DIRECTIVE 130 TASK 1: 더미 데이터 안전 격리 스크립트
100대 데모 차량 및 2000장 가상 사진을 quarantined_* 테이블로 이동 격리.
실차량, 실제 사진, 상담, 거래 데이터 100% 보존.
"""

import subprocess
import json

def quarantine_d1():
    print("[*] Cloudflare D1 더미 격리 테이블 생성 및 이동 시작...")
    
    sql_commands = [
        # 1. 격리 테이블 생성
        "CREATE TABLE IF NOT EXISTS quarantined_demo_vehicles AS SELECT * FROM vehicles WHERE is_demo = 1;",
        "CREATE TABLE IF NOT EXISTS quarantined_demo_photos AS SELECT * FROM vehicle_photos WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 1);",
        # 2. 본 테이블에서 격리 (삭제)
        "DELETE FROM vehicle_photos WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 1);",
        "DELETE FROM vehicles WHERE is_demo = 1;"
    ]
    
    for sql in sql_commands:
        cmd = ["npx", "-y", "wrangler", "d1", "execute", "chamart-db", "--remote", f"--command={sql}"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"SQL 실행 실패: {sql}\n에러: {res.stderr}")
            return False
        else:
            print(f"[OK] {sql[:40]}...")
            
    print("[+] Cloudflare D1 더미 데이터 안전 격리 완료!")
    return True

if __name__ == "__main__":
    quarantine_d1()
