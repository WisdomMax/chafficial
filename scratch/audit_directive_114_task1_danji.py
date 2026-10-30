import json
import hashlib
from pathlib import Path
from collections import Counter

def calculate_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=== [TASK 1] DIRECTIVE 114: 단지별 1,167 / 370 / 227건 원본 데이터 전수 감사 ===")
    
    json_path = "data/carmanager_raw/janghanpyeong_full_collection.json"
    html_path = "scratch/datapart_page1_live.html"
    
    json_hash = calculate_sha256(json_path)
    html_hash = calculate_sha256(html_path)
    
    print(f"1. 원본 파일 무결성 해시 (SHA256):")
    print(f"  - {json_path}: {json_hash}")
    print(f"  - {html_path}: {html_hash}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    cars = data.get("cars", [])
    total_cars = len(cars)
    print(f"\n2. 총 로드된 차량 레코드 수: {total_cars}건")
    
    # encarno 고유성 검사
    encarno_list = [c.get("encarno") for c in cars]
    unique_encarnos = set(encarno_list)
    print(f"  - 고유 encarno 수: {len(unique_encarnos)}개 (중복: {total_cars - len(unique_encarnos)}개)")
    
    # danji별 전수 집계
    danji_counter = Counter(c.get("danji") for c in cars)
    danji_encarno_counter = {}
    for c in cars:
        d = c.get("danji")
        danji_encarno_counter.setdefault(d, set()).add(c.get("encarno"))
        
    print(f"\n3. danji(단지)별 원시 문자열 및 고유 매물 ID 집계:")
    for d, cnt in danji_counter.most_common():
        uniq_cnt = len(danji_encarno_counter[d])
        pct = (cnt / total_cars) * 100
        print(f"  - [{d}]: 원시 {cnt}건, 고유 ID {uniq_cnt}건 ({pct:.1f}%)")
        
    unclassified = sum(1 for c in cars if not c.get("danji"))
    print(f"  - 단지 미분류 건수: {unclassified}건")
    
    # 검산
    c_motorplaza = danji_counter.get("성동구/장안모터프라", 0)
    c_seongdong_gen = danji_counter.get("성동구/성동구지역", 0)
    c_complex = danji_counter.get("성동구/장안평단지", 0)
    
    sum_verified = c_motorplaza + c_seongdong_gen + c_complex
    print(f"\n4. 검산 검증:")
    print(f"  - 장안모터프라자 ({c_motorplaza}) + 성동구지역 ({c_seongdong_gen}) + 장안평단지 ({c_complex}) = {sum_verified}대")
    assert sum_verified == total_cars == 1764, "검산 불일치!"
    print(f"  -> 검산 통과: 총 1,764대와 100% 일치!")
    
    # HTML 실서버 응답 확인
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    import re
    m_rowcount = re.search(r'#hdfCarRowCount.*val\([\'"](\d+)[\'"]\)', html_content)
    m_totalcount = re.search(r'#ui_totalcount.*html\(remakeNumber\([\'"](\d+)[\'"]\)\)', html_content)
    
    print(f"\n5. 카매니저 실서버 HTML 응답 증적 (DataPart Page 1):")
    if m_rowcount:
        print(f"  - #hdfCarRowCount: {m_rowcount.group(1)}대")
    if m_totalcount:
        print(f"  - #ui_totalcount: {m_totalcount.group(1)}대")
        
    # 결과 증적 저장
    audit_report = {
        "json_path": json_path,
        "json_sha256": json_hash,
        "html_path": html_path,
        "html_sha256": html_hash,
        "total_cars": total_cars,
        "unique_encarnos": len(unique_encarnos),
        "danji_breakdown": {
            "성동구/장안모터프라": c_motorplaza,
            "성동구/성동구지역": c_seongdong_gen,
            "성동구/장안평단지": c_complex,
            "unclassified": unclassified
        },
        "server_reported_total": m_rowcount.group(1) if m_rowcount else None,
        "verified_at": "2026-10-30T23:36:00+09:00"
    }
    with open("scratch/task1_danji_audit_result.json", "w", encoding="utf-8") as f:
        json.dump(audit_report, f, ensure_ascii=False, indent=2)
    print(f"\n[+] Audit report saved to scratch/task1_danji_audit_result.json")

if __name__ == "__main__":
    main()
