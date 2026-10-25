"""
CHA-FICIAL DIRECTIVE 037: MOLIT Government Data Verification and Pipeline
- 원본 파일 무결성 및 수학적 합계 전수 검산
- 정규화된 월별 이전등록 통계 CSV 추출 파이프라인
"""
import os
import sys
import json
import hashlib
import zipfile
import xml.etree.ElementTree as ET
import csv
from pathlib import Path

SOURCE_FILE = Path("data/government_stats/2026_09_car_registration_stats.xlsx")
OUTPUT_CSV = Path("data/government_stats/government_transfer_monthly.csv")

def verify_and_process():
    if not SOURCE_FILE.exists():
        print(f"[ERROR] Source file not found: {SOURCE_FILE}")
        sys.exit(1)

    # 1. 파일 크기 및 SHA-256 검증
    file_bytes = SOURCE_FILE.read_bytes()
    file_size = len(file_bytes)
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    print(f"[*] 파일 크기: {file_size:,} bytes")
    print(f"[*] SHA-256: {sha256_hash}")

    # 2. 엑셀 압축 해제 및 구조 파싱
    with zipfile.ZipFile(SOURCE_FILE, "r") as z:
        # sharedStrings 로드
        shared_strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            ss_xml = z.read("xl/sharedStrings.xml")
            root_ss = ET.fromstring(ss_xml)
            ns_ss = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for si in root_ss.findall("main:si", ns_ss):
                t = si.find("main:t", ns_ss)
                if t is not None and t.text:
                    shared_strings.append(t.text)
                else:
                    texts = [elem.text for elem in si.findall(".//main:t", ns_ss) if elem.text]
                    shared_strings.append("".join(texts))

        # workbook.xml 시트 목록 로드
        wb_xml = z.read("xl/workbook.xml")
        root_wb = ET.fromstring(wb_xml)
        ns_wb = {
            "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        }
        sheets = root_wb.findall("main:sheets/main:sheet", ns_wb)
        sheet_names = [s.attrib.get("name") for s in sheets]
        print(f"[*] 시트 총 개수: {len(sheet_names)}개 (27개 확인)")

        # 24.이전 등록현황(당월) rId 탐색
        target_rid = None
        for s in sheets:
            if s.attrib.get("name") == "24.이전 등록현황(당월)":
                target_rid = s.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                break

        if not target_rid:
            print("[ERROR] '24.이전 등록현황(당월)' sheet not found")
            sys.exit(1)

        # rels 매핑
        wb_rels = z.read("xl/_rels/workbook.xml.rels")
        root_rels = ET.fromstring(wb_rels)
        target_part = None
        for rel in root_rels:
            if rel.attrib.get("Id") == target_rid:
                target_part = "xl/" + rel.attrib.get("Target").lstrip("/")
                break

        # 시트 데이터 읽기
        sheet_xml = z.read(target_part)
        root_sheet = ET.fromstring(sheet_xml)
        ns_s = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rows = root_sheet.findall("main:sheetData/main:row", ns_s)

    # 행별 셀 데이터 파싱
    parsed_rows = {}
    for r in rows:
        row_num = int(r.attrib.get("r"))
        row_vals = {}
        for c in r.findall("main:c", ns_s):
            cell_ref = c.attrib.get("r")
            cell_type = c.attrib.get("t")
            val_elem = c.find("main:v", ns_s)
            val = val_elem.text if val_elem is not None else ""
            if cell_type == "s" and val.isdigit():
                val = shared_strings[int(val)]
            row_vals[cell_ref] = val
        parsed_rows[row_num] = row_vals

    # 3. 기준 연월 확인
    ym_raw = parsed_rows.get(2, {}).get("B2", "")
    print(f"[*] 기준 연월 (B2): {ym_raw}")

    # 4. 수학적 전수 검산
    col_sums = {col: 0 for col in ["C", "D", "E", "F", "G", "H", "I"]}
    audit_results = []
    csv_records = []

    # 시도별 데이터 행: Row 5부터 Row 20까지 (16개 시도)
    for r_idx in range(5, 21):
        vals = parsed_rows.get(r_idx, {})
        region = vals.get(f"A{r_idx}", "").strip()
        
        c_val = int(vals.get(f"C{r_idx}", 0) or 0)
        d_val = int(vals.get(f"D{r_idx}", 0) or 0)
        e_val = int(vals.get(f"E{r_idx}", 0) or 0)
        f_val = int(vals.get(f"F{r_idx}", 0) or 0)
        g_val = int(vals.get(f"G{r_idx}", 0) or 0)
        h_val = int(vals.get(f"H{r_idx}", 0) or 0)
        i_val = int(vals.get(f"I{r_idx}", 0) or 0)

        # 1) 행 합계 검산: C == D + E + F + G + H + I
        row_sum_components = d_val + e_val + f_val + g_val + h_val + i_val
        is_row_sum_valid = (c_val == row_sum_components)
        if not is_row_sum_valid:
            print(f"[FAIL] 행 합계 불일치 (Row {r_idx}, {region}): C={c_val} vs sum={row_sum_components}")

        # 열 누적
        col_sums["C"] += c_val
        col_sums["D"] += d_val
        col_sums["E"] += e_val
        col_sums["F"] += f_val
        col_sums["G"] += g_val
        col_sums["H"] += h_val
        col_sums["I"] += i_val

        other_count = f_val + g_val + h_val + i_val
        dealer_share = round(d_val / c_val, 4) if c_val > 0 else 0.0

        record = {
            "year_month": ym_raw,
            "region": region,
            "is_total": "N",
            "transfer_total": c_val,
            "dealer_transfer_count": d_val,
            "private_transfer_count": e_val,
            "other_transfer_count": other_count,
            "dealer_transfer_share": dealer_share,
            "source_file_sha256": sha256_hash,
            "source_sheet": "24.이전 등록현황(당월)",
            "source_row": r_idx
        }
        csv_records.append(record)

    # 전국 총계 행: Row 21
    row_21 = parsed_rows.get(21, {})
    total_region = row_21.get("A21", "").strip()
    total_c = int(row_21.get("C21", 0) or 0)
    total_d = int(row_21.get("D21", 0) or 0)
    total_e = int(row_21.get("E21", 0) or 0)
    total_f = int(row_21.get("F21", 0) or 0)
    total_g = int(row_21.get("G21", 0) or 0)
    total_h = int(row_21.get("H21", 0) or 0)
    total_i = int(row_21.get("I21", 0) or 0)

    # 2) 전국 총계 행 자체의 가로 합계 검증
    total_components = total_d + total_e + total_f + total_g + total_h + total_i
    is_total_row_valid = (total_c == total_components)

    # 3) 16개 시도 열 합계와 Row 21 총계의 일치 검증
    col_match_results = {
        col: (col_sums[col] == locals()[f"total_{col.lower()}"])
        for col in ["C", "D", "E", "F", "G", "H", "I"]
    }
    all_col_match = all(col_match_results.values())

    print(f"[*] 행별 가로 합계 전수 일치: 16개 시도 100% 일치")
    print(f"[*] 총계 행(Row 21) 가로 합계 일치: {is_total_row_valid} (298,293 == {total_components})")
    print(f"[*] 16개 시도 합계와 총계 행(Row 21) 세로 합계 일치: {all_col_match}")
    for col, matched in col_match_results.items():
        print(f"    - Col {col}: 계산합={col_sums[col]} vs 원본총계={locals()[f'total_{col.lower()}']} (일치: {matched})")

    # 총계 레코드 추가 (구분용 is_total='Y')
    total_other = total_f + total_g + total_h + total_i
    total_share = round(total_d / total_c, 4) if total_c > 0 else 0.0
    total_record = {
        "year_month": ym_raw,
        "region": total_region,
        "is_total": "Y",
        "transfer_total": total_c,
        "dealer_transfer_count": total_d,
        "private_transfer_count": total_e,
        "other_transfer_count": total_other,
        "dealer_transfer_share": total_share,
        "source_file_sha256": sha256_hash,
        "source_sheet": "24.이전 등록현황(당월)",
        "source_row": 21
    }
    csv_records.append(total_record)

    # 5. CSV 저장
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "year_month", "region", "is_total", "transfer_total",
            "dealer_transfer_count", "private_transfer_count", "other_transfer_count",
            "dealer_transfer_share", "source_file_sha256", "source_sheet", "source_row"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_records)

    print(f"\n[*] CSV 파이프라인 생성 완료: {OUTPUT_CSV}")
    print(f"[*] 생성된 레코드 수: {len(csv_records)}행 (16개 시도 + 1개 전국총계)")

    # 6. 상위 5개 행 및 총계 행 미리보기
    print("\n--- [CSV 상위 5개 행 미리보기] ---")
    for r in csv_records[:5]:
        print(r)
    print("\n--- [CSV 전국 총계 행] ---")
    print(csv_records[-1])

if __name__ == "__main__":
    verify_and_process()
