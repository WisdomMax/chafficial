"""
D1 안전 청크 실행 스크립트 (페이로드 초과 방지)
"""

import subprocess
import os

with open("cloudflare/d1/0003_demo_vehicles_100.sql", "r", encoding="utf-8") as f:
    lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("--")]

print(f"전체 SQL 문장 수: {len(lines)}")

# 150줄씩 청크 분할
CHUNK_SIZE = 150
chunks = [lines[i:i + CHUNK_SIZE] for i in range(0, len(lines), CHUNK_SIZE)]
print(f"총 {len(chunks)}개 청크 생성")

os.makedirs("cloudflare/d1/chunks", exist_ok=True)

for idx, chunk in enumerate(chunks):
    chunk_file = f"cloudflare/d1/chunks/chunk_{idx:02d}.sql"
    with open(chunk_file, "w", encoding="utf-8") as f:
        f.write("\n".join(chunk))

    print(f"[{idx+1}/{len(chunks)}] D1 원격 실행 중: {chunk_file} ({len(chunk)}문장)...")
    cmd = ["npx", "-y", "wrangler", "d1", "execute", "chamart-db", "--remote", f"--file={chunk_file}", "-y"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"오류 발생 (청크 {idx}):", res.stderr)
        # retry once
        print("재시도 중...")
        res2 = subprocess.run(cmd, capture_output=True, text=True)
        if res2.returncode != 0:
            print("재시도 실패:", res2.stderr)
            break
    else:
        print(f"[{idx+1}/{len(chunks)}] 청크 성공!")

print("전체 청크 D1 실행 완료!")
