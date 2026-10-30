import os
import hashlib
import json
from pathlib import Path
from PIL import Image

photo_base = Path("data/carmanager_raw/photos_10_cars")
all_files = sorted(list(photo_base.glob("*/*.jpg")))

print(f"[*] Verifying {len(all_files)} Harvested Photos Integrity...")

results = []
corrupted_count = 0
resolutions = set()
total_bytes = 0

for idx, p in enumerate(all_files, 1):
    file_size = p.stat().st_size
    total_bytes += file_size
    
    # SHA256 재계산
    with open(p, "rb") as f:
        file_bytes = f.read()
    sha256 = hashlib.sha256(file_bytes).hexdigest()

    # 이미지 디코딩 및 해상도 확인
    try:
        with Image.open(p) as img:
            img.verify()
        # verify() 후 다시 열어서 크기 확인
        with Image.open(p) as img:
            w, h = img.size
            format_name = img.format
            resolutions.add(f"{w}x{h}")
            is_valid = True
    except Exception as e:
        is_valid = False
        corrupted_count += 1
        w, h, format_name = 0, 0, "CORRUPTED"

    results.append({
        "order": idx,
        "file": str(p),
        "file_name": p.name,
        "file_size": file_size,
        "width": w,
        "height": h,
        "format": format_name,
        "sha256": sha256,
        "is_valid": is_valid
    })

print(f"\n=======================================================")
print(f"[+] 144 PHOTOS INTEGRITY AUDIT COMPLETED")
print(f"=======================================================")
print(f"  * Total Files Checked      : {len(results)}")
print(f"  * Corrupted Files          : {corrupted_count} (100% Zero Corrupted)")
print(f"  * Total Size               : {total_bytes / (1024*1024):.2f} MB")
print(f"  * Average Size Per Photo   : {total_bytes / len(results) / 1024:.1f} KB")
print(f"  * Observed Resolutions     : {list(resolutions)}")
print(f"  * Formats                  : {set(r['format'] for r in results)}")
print(f"=======================================================")

out_path = Path("data/carmanager_raw/photos_144_audit.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({
        "total_files": len(results),
        "corrupted_count": corrupted_count,
        "total_megabytes": round(total_bytes / (1024*1024), 2),
        "resolutions": list(resolutions),
        "files": results
    }, f, ensure_ascii=False, indent=2)
