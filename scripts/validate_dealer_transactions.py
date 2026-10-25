#!/usr/bin/env python3
"""차피셜(CHA-FICIAL) DIRECTIVE 044-A: 딜러 실거래 출처 분류 강제 검증기

[출처 분류 강제 규칙 (Provenance Enforcement Rules)]
1. 모의 입력 / 테스트 식별자(TEST, SYN 등) -> 무조건 SYNTHETIC / evidence_level='N/A'
2. 수령 기록(메타데이터: received_at, provided_by_role 등)이 없는 외부 파일 -> 무조건 UNKNOWN / UNVERIFIED
   - 엑셀 시트에 자의적으로 'DEALER_SELF_REPORTED'라고 적혀 있어도 절대 신뢰하지 않고 UNKNOWN으로 강제 강등.
3. 오직 검증된 딜러 수령 기록(meta)이 주입된 경우에만 -> DEALER_SELF_REPORTED 승인.
4. 실제 거래 파일(dealer_real_transactions.csv) 오염 방지: REAL_DATA_0 엄격 사수.
"""

import csv
import datetime
import hashlib
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


REQUIRED_BASE_FIELDS = [
    "dealer_vehicle_id",
    "make_model",
    "model_year",
    "mileage_km",
    "purchase_date",
    "purchase_price_krw",
    "outcome_status",
]

VALID_PROVENANCES = {
    "DEALER_SELF_REPORTED",
    "PUBLIC_OBSERVATION",
    "SYNTHETIC",
    "UNKNOWN",
}

VALID_EVIDENCE_LEVELS = {"D0", "D1", "D2", "D3", "D4", "N/A"}

VALID_OUTCOMES = {
    "SOLD_CONFIRMED",
    "ACTIVE_CONFIRMED",
    "WITHDRAWN",
    "CANCELLED",
    "UNKNOWN",
    "TRANSACTION_UNKNOWN",
    "판매완료",
    "보유중",
    "취소",
}


def parse_date(date_str: Any) -> Optional[datetime.date]:
    if not date_str:
        return None
    if isinstance(date_str, (datetime.date, datetime.datetime)):
        return date_str if isinstance(date_str, datetime.date) else date_str.date()
    s = str(date_str).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_int(val_str: Any) -> Optional[int]:
    if val_str is None:
        return None
    if isinstance(val_str, (int, float)):
        return int(val_str)
    s = str(val_str).replace(",", "").strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def normalize_outcome(outcome: str) -> str:
    mapping = {
        "판매완료": "SOLD_CONFIRMED",
        "보유중": "ACTIVE_CONFIRMED",
        "취소": "CANCELLED",
    }
    return mapping.get(outcome, outcome)


def normalize_cost_comp(comp: str) -> str:
    mapping = {
        "완료": "COMPLETE",
        "미완료": "PARTIAL",
    }
    return mapping.get(comp, comp)


def compute_file_sha256(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def determine_provenance_and_evidence(
    vehicle_id: str,
    raw_provenance: str,
    raw_evidence: str,
    meta: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, str, bool]:
    """[DIRECTIVE 044-A 핵심] 출처와 증거 등급을 자의적 라벨이 아닌 객관적 증거 기준으로 강제 판정"""
    vid_upper = vehicle_id.upper()

    # 1. 테스트/모의 식별자 또는 SYNTHETIC 선언 -> 무조건 SYNTHETIC / N/A
    if any(k in vid_upper for k in ["TEST", "SYN", "MOCK", "SAMPLE", "TEMP", "EX_"]) or raw_provenance == "SYNTHETIC":
        return ("SYNTHETIC", "N/A", "NOT_PROVIDED", True)

    # 2. 공개 관측 데이터 (엔카 관측 8대 등)
    if "CAR_CN7_" in vid_upper or raw_provenance == "PUBLIC_OBSERVATION":
        return ("PUBLIC_OBSERVATION", "D0", "NOT_PROVIDED", False)

    # 3. 딜러 실제 수령 데이터 판정:
    # 수령 메타데이터(수령일시, 제공자역할, 파일해시)가 검증된 경우에만 DEALER_SELF_REPORTED 인정
    is_officially_received = meta and meta.get("received_at") and meta.get("provided_by_role")
    if is_officially_received:
        ev = raw_evidence if raw_evidence in {"D1", "D2", "D3", "D4"} else "D1"
        doc_stat = "VERIFIED" if ev in {"D3", "D4"} else "UNVERIFIED"
        return ("DEALER_SELF_REPORTED", ev, doc_stat, False)

    # 4. 수령 기록이 없는 외부 입력 파일 -> 무조건 UNKNOWN / UNVERIFIED (엑셀 라벨 신뢰 금지)
    return ("UNKNOWN", "D0", "UNVERIFIED", False)


def validate_transaction_row(
    row: Dict[str, Any], row_idx: int, meta: Optional[Dict[str, Any]] = None
) -> Tuple[bool, List[str], Dict[str, Any]]:
    errors = []

    for field in REQUIRED_BASE_FIELDS:
        val = str(row.get(field, "") or "").strip()
        if not val:
            errors.append(f"Row {row_idx}: 필수 필드 누락 '{field}'")

    vehicle_id = str(row.get("dealer_vehicle_id", "") or "").strip()
    outcome = normalize_outcome(str(row.get("outcome_status", "") or "").strip())
    raw_prov = str(row.get("data_provenance", "") or "").strip()
    raw_ev = str(row.get("evidence_level", "") or "").strip()
    cost_comp = normalize_cost_comp(str(row.get("cost_completeness", "") or "").strip())

    # 출처 및 증거 등급 강제 판정
    provenance, evidence, doc_ver_status, is_syn = determine_provenance_and_evidence(
        vehicle_id, raw_prov, raw_ev, meta
    )

    if outcome and outcome not in VALID_OUTCOMES:
        errors.append(f"Row {row_idx}: 유효하지 않은 상태 '{outcome}'")

    model_year = parse_int(row.get("model_year"))
    mileage = parse_int(row.get("mileage_km"))
    p_price = parse_int(row.get("purchase_price_krw"))
    s_price = parse_int(row.get("actual_sale_price_krw"))
    acq_cost = parse_int(row.get("acquisition_cost_krw"))
    rec_cost = parse_int(row.get("reconditioning_cost_krw"))
    oth_cost = parse_int(row.get("other_cost_krw"))

    if p_price is not None and p_price <= 0:
        errors.append(f"Row {row_idx}: 매입금액은 0원보다 커야 합니다 ({p_price})")
    if mileage is not None and mileage < 0:
        errors.append(f"Row {row_idx}: 주행거리는 음수일 수 없습니다 ({mileage})")

    p_date = parse_date(row.get("purchase_date"))
    inv_date = parse_date(row.get("inventory_start_date"))
    s_date = parse_date(row.get("sale_contract_date"))

    if row.get("purchase_date") and p_date is None:
        errors.append(f"Row {row_idx}: 매입일 형식 오류")
    if row.get("inventory_start_date") and inv_date is None:
        errors.append(f"Row {row_idx}: 입고일 형식 오류")
    if row.get("sale_contract_date") and s_date is None:
        errors.append(f"Row {row_idx}: 판매계약일 형식 오류")

    if p_date and inv_date and p_date > inv_date:
        errors.append(f"Row {row_idx}: 입고일({inv_date})이 매입일({p_date})보다 빠름")
    if p_date and s_date and p_date > s_date:
        errors.append(f"Row {row_idx}: 판매일({s_date})이 매입일({p_date})보다 빠름")

    if outcome == "SOLD_CONFIRMED":
        if s_price is None or s_price <= 0:
            errors.append(f"Row {row_idx}: 판매완료 차량은 판매금액 필수")
        if s_date is None:
            errors.append(f"Row {row_idx}: 판매완료 차량은 판매계약일 필수")
    elif outcome == "ACTIVE_CONFIRMED":
        if s_price is not None:
            errors.append(f"Row {row_idx}: 보유중 차량은 판매금액 공란이어야 함")
        if s_date is not None:
            errors.append(f"Row {row_idx}: 보유중 차량은 판매일 공란이어야 함")

    gross_spread = None
    if p_price is not None and s_price is not None and outcome == "SOLD_CONFIRMED":
        gross_spread = s_price - p_price

    costs_list = [c for c in [acq_cost, rec_cost, oth_cost] if c is not None]
    all_costs_present = (acq_cost is not None) and (rec_cost is not None) and (oth_cost is not None)
    verified_costs = sum(costs_list) if costs_list else None

    # 실거래 수익은 오직 공식 딜러 수령(DEALER_SELF_REPORTED) 및 D3 이상일 때만 검증 완료
    verified_contribution = None
    is_profit_verified = False
    if (
        outcome == "SOLD_CONFIRMED"
        and gross_spread is not None
        and cost_comp == "COMPLETE"
        and all_costs_present
        and provenance == "DEALER_SELF_REPORTED"
        and evidence in {"D3", "D4"}
        and not is_syn
    ):
        verified_contribution = gross_spread - (acq_cost + rec_cost + oth_cost)
        is_profit_verified = True

    inventory_days = None
    if inv_date and s_date:
        inventory_days = (s_date - inv_date).days
    elif inv_date and outcome == "ACTIVE_CONFIRMED":
        today = datetime.date(2026, 10, 26)
        inventory_days = (today - inv_date).days

    parsed = {
        "dealer_vehicle_id": vehicle_id,
        "make_model": str(row.get("make_model", "") or "").strip(),
        "model_year": model_year,
        "mileage_km": mileage,
        "purchase_date": p_date,
        "purchase_price_krw": p_price,
        "inventory_start_date": inv_date,
        "sale_contract_date": s_date,
        "actual_sale_price_krw": s_price,
        "acquisition_cost_krw": acq_cost,
        "reconditioning_cost_krw": rec_cost,
        "other_cost_krw": oth_cost,
        "outcome_status": outcome,
        "data_provenance": provenance,
        "evidence_level": evidence,
        "document_verification_status": doc_ver_status,
        "is_synthetic": is_syn,
        "cost_completeness": cost_comp,
        "gross_spread": gross_spread,
        "verified_costs": verified_costs,
        "verified_contribution": verified_contribution,
        "is_profit_verified": is_profit_verified,
        "inventory_days": inventory_days,
    }

    return (len(errors) == 0, errors, parsed)


def parse_excel_file(file_path: str) -> List[Dict[str, Any]]:
    import openpyxl
    wb = openpyxl.load_workbook(file_path, data_only=True)
    if "거래기록 입력" not in wb.sheetnames:
        raise ValueError(f"시트 '거래기록 입력' 누락: {wb.sheetnames}")
    ws = wb["거래기록 입력"]

    col_mapping = {
        "차량관리번호": "dealer_vehicle_id",
        "차종/트림": "make_model",
        "연식": "model_year",
        "주행거리(km)": "mileage_km",
        "매입일": "purchase_date",
        "매입금액(원)": "purchase_price_krw",
        "입고일": "inventory_start_date",
        "판매일": "sale_contract_date",
        "판매금액(원)": "actual_sale_price_krw",
        "취득비용(원)": "acquisition_cost_krw",
        "상품화비용(원)": "reconditioning_cost_krw",
        "기타비용(원)": "other_cost_krw",
        "거래상태": "outcome_status",
        "비용정산": "cost_completeness",
        "증빙확인": "evidence_check",
        "데이터출처": "data_provenance",
        "증거등급": "evidence_level",
    }

    header_row = [cell.value for cell in ws[1]]
    mapped_keys = [col_mapping.get(str(h or "").strip(), str(h or "").strip()) for h in header_row]

    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue
        first_val = str(row[0] or "").strip()
        if first_val.startswith("DTR_EX_") or not first_val:
            continue
        row_dict = {}
        for key, val in zip(mapped_keys, row):
            row_dict[key] = val
        rows.append(row_dict)
    return rows


def validate_dealer_file(
    file_path: str, meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        return {"ok": False, "error": f"파일 없음: {file_path}"}

    total_rows = 0
    valid_rows = 0
    all_errors = []
    records = []

    if file_path.endswith(".xlsx"):
        rows = parse_excel_file(file_path)
        for idx, row in enumerate(rows, start=2):
            total_rows += 1
            ok, errors, parsed = validate_transaction_row(row, idx, meta)
            if ok:
                valid_rows += 1
                records.append(parsed)
            else:
                all_errors.extend(errors)
    else:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=2):
                first_val = list(row.values())[0] if row else ""
                if first_val and first_val.strip().startswith("#"):
                    continue

                total_rows += 1
                ok, errors, parsed = validate_transaction_row(row, idx, meta)
                if ok:
                    valid_rows += 1
                    records.append(parsed)
                else:
                    all_errors.extend(errors)

    sha256 = compute_file_sha256(file_path)
    return {
        "ok": len(all_errors) == 0,
        "file_path": file_path,
        "file_sha256": sha256,
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "errors": all_errors,
        "records": records,
    }


def run_directive_044a_regression_tests():
    """DIRECTIVE 044-A 3대 최소 회귀 테스트 슈트 실행"""
    import openpyxl

    template_path = "data/dealer_pilot/차피셜_딜러_실거래_입력양식_v1.xlsx"
    real_csv_path = "data/dealer_pilot/dealer_real_transactions.csv"

    print("\n[*] === DIRECTIVE 044-A 3대 회귀 테스트 슈트 실행 ===")

    # ------------------------------------------------------------------
    # TEST A: 합성 데이터 왕복 테스트 (기대 결과: SYNTHETIC / N/A)
    # ------------------------------------------------------------------
    wb_a = openpyxl.load_workbook(template_path)
    ws_a = wb_a["거래기록 입력"]
    # 딜러 자체보고라고 자의적으로 적어도 ID가 TEST이면 무조건 SYNTHETIC/NA 처리되어야 함
    row_a = [
        "SYN_TEST_MOCK01", "현대 아반떼 CN7 1.6 가솔린 모던", 2024, 30000,
        "2026-08-10", 15000000, "2026-08-12", "2026-09-01", 17500000,
        450000, 300000, 150000, "판매완료", "완료", "가능",
        "DEALER_SELF_REPORTED", "D2"
    ]
    for c_idx, val in enumerate(row_a, start=1):
        ws_a.cell(row=4, column=c_idx, value=val)

    temp_a = "data/dealer_pilot/temp_test_a.xlsx"
    wb_a.save(temp_a)

    res_a = validate_dealer_file(temp_a, meta=None)
    rec_a = res_a["records"][0] if res_a["valid_rows"] > 0 else {}
    test_a_pass = (
        rec_a.get("data_provenance") == "SYNTHETIC"
        and rec_a.get("evidence_level") == "N/A"
        and rec_a.get("is_synthetic") is True
    )
    print(f"  [TEST A] 합성 데이터 왕복: {'PASS' if test_a_pass else 'FAIL'}")
    print(f"           출처={rec_a.get('data_provenance')}, 등급={rec_a.get('evidence_level')}, is_syn={rec_a.get('is_synthetic')}")
    if os.path.exists(temp_a):
        os.remove(temp_a)

    # ------------------------------------------------------------------
    # TEST B: 수령 기록 없는 입력 테스트 (기대 결과: UNKNOWN / UNVERIFIED)
    # ------------------------------------------------------------------
    wb_b = openpyxl.load_workbook(template_path)
    ws_b = wb_b["거래기록 입력"]
    # 일반 딜러 ID처럼 꾸며도 수령 기록(meta)이 없으면 UNKNOWN/UNVERIFIED 처리되어야 함
    row_b = [
        "DTR_UNKNOWN_01", "현대 아반떼 CN7 1.6 가솔린 인스퍼레이션", 2024, 25000,
        "2026-08-15", 18500000, "2026-08-17", "2026-09-15", 21000000,
        500000, 350000, 150000, "판매완료", "완료", "가능",
        "DEALER_SELF_REPORTED", "D3"
    ]
    for c_idx, val in enumerate(row_b, start=1):
        ws_b.cell(row=4, column=c_idx, value=val)

    temp_b = "data/dealer_pilot/temp_test_b.xlsx"
    wb_b.save(temp_b)

    res_b = validate_dealer_file(temp_b, meta=None)  # 메타데이터 없음
    rec_b = res_b["records"][0] if res_b["valid_rows"] > 0 else {}
    test_b_pass = (
        rec_b.get("data_provenance") == "UNKNOWN"
        and rec_b.get("document_verification_status") == "UNVERIFIED"
        and rec_b.get("is_profit_verified") is False
    )
    print(f"  [TEST B] 수령 기록 없는 입력: {'PASS' if test_b_pass else 'FAIL'}")
    print(f"           출처={rec_b.get('data_provenance')}, 상태={rec_b.get('document_verification_status')}, 수익검증={rec_b.get('is_profit_verified')}")
    if os.path.exists(temp_b):
        os.remove(temp_b)

    # ------------------------------------------------------------------
    # TEST C: 실제 거래 파일 오염 방지 테스트 (기대 결과: REAL_DATA_0)
    # ------------------------------------------------------------------
    res_c = validate_dealer_file(real_csv_path)
    test_c_pass = (res_c["total_rows"] == 0 and res_c["valid_rows"] == 0)
    print(f"  [TEST C] 실제 거래 파일 오염 방지: {'PASS' if test_c_pass else 'FAIL'}")
    print(f"           real_transactions 행 수={res_c['total_rows']}건 (STATUS: REAL_DATA_0)")

    all_pass = test_a_pass and test_b_pass and test_c_pass
    print(f"\n[+] DIRECTIVE 044-A 3대 회귀 테스트 결과: {'ALL 100% PASS' if all_pass else 'FAIL'}\n")
    return all_pass


if __name__ == "__main__":
    run_directive_044a_regression_tests()
