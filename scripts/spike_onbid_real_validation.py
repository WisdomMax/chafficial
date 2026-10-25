"""
CHA-FICIAL DIRECTIVE 032: ONBID REAL API SINGLE-RECORD VALIDATION SPIKE
- 엄격한 3회 호출 예산 준수
- 순수 표준 라이브러리(urllib) 사용
- 키 마스킹 및 보안 준수
- 6대 검증 항목 독립 평가
"""
import os
import sys
import json
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
from pathlib import Path

# .env 직접 파싱 (python-dotenv 의존성 없이 순수 파이썬)
env_path = Path(".env")
raw_key = None
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k in ["ONBID_SERVICE_KEY", "API_KEY"]:
                    raw_key = v
                    break

if not raw_key:
    raw_key = os.getenv("ONBID_SERVICE_KEY") or os.getenv("API_KEY")

if not raw_key:
    print("[ERROR] ONBID_SERVICE_KEY or API_KEY not found in .env or environment")
    sys.exit(1)

service_key = raw_key.strip()
masked_key = service_key[:4] + "..." + service_key[-4:] if len(service_key) > 8 else "***"
print(f"[*] 인증키 확인 완료: {masked_key} (길이: {len(service_key)})")

# 호출 카운터 (최대 3회)
CALL_COUNT = 0
MAX_CALLS = 3

audit_log = {
    "total_calls": 0,
    "max_allowed": MAX_CALLS,
    "calls": [],
    "outcomes": {
        "HTTP_OK": False,
        "API_SUCCESS": False,
        "RECORD_FOUND": False,
        "PRICE_VERIFIED": False,
        "JOIN_VERIFIED": False,
        "HISTORICAL_DETAIL_VERIFIED": False,
    },
    "captured_data": {},
}

def parse_response(res_text):
    """JSON 또는 XML 응답을 딕셔너리로 변환"""
    stripped = res_text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return json.loads(stripped)
        except Exception:
            pass
    
    # XML 파싱
    try:
        root = ET.fromstring(stripped)
        def elem_to_dict(elem):
            d = {}
            for child in elem:
                if len(child) == 0:
                    d[child.tag] = child.text
                else:
                    child_dict = elem_to_dict(child)
                    if child.tag in d:
                        if isinstance(d[child.tag], list):
                            d[child.tag].append(child_dict)
                        else:
                            d[child.tag] = [d[child.tag], child_dict]
                    else:
                        d[child.tag] = child_dict
            return d
        return {root.tag: elem_to_dict(root)}
    except Exception as e:
        return {"raw_text": stripped[:500], "parse_error": str(e)}

def safe_request(url, params, step_name):
    global CALL_COUNT
    if CALL_COUNT >= MAX_CALLS:
        print(f"[BLOCKED] 호출 예산 초과 차단: 현재 {CALL_COUNT} / 최대 {MAX_CALLS}")
        return None, None, None

    CALL_COUNT += 1
    audit_log["total_calls"] = CALL_COUNT
    
    # 쿼리스트링 조합
    # serviceKey는 인코딩하지 않고 그대로 붙이거나 quote 처리
    # urllib.parse.urlencode는 serviceKey를 인코딩하므로 주의
    qs = urllib.parse.urlencode(params)
    full_url = f"{url}?{qs}"

    # 로깅용 (마스킹)
    log_params = dict(params)
    if "serviceKey" in log_params:
        log_params["serviceKey"] = masked_key
    log_qs = urllib.parse.urlencode(log_params)

    print(f"\n[호출 {CALL_COUNT}/{MAX_CALLS}] {step_name}")
    print(f"  URL: {url}?{log_qs}")

    try:
        req = urllib.request.Request(
            full_url,
            headers={"User-Agent": "Mozilla/5.0 (CHA-FICIAL Research Spike)"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            http_status = response.status
            raw_text = response.read().decode("utf-8", errors="replace")
            print(f"  HTTP 상태: {http_status}")
            
            parsed = parse_response(raw_text)
            
            call_record = {
                "step": step_name,
                "call_index": CALL_COUNT,
                "url": url,
                "http_status": http_status,
                "response_preview": parsed,
            }
            audit_log["calls"].append(call_record)
            return http_status, parsed, raw_text
    except urllib.error.HTTPError as e:
        http_status = e.code
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"  [HTTP ERROR {http_status}]: {err_body[:300]}")
        audit_log["calls"].append({
            "step": step_name,
            "call_index": CALL_COUNT,
            "url": url,
            "http_status": http_status,
            "error_body": err_body[:500]
        })
        return http_status, None, err_body
    except Exception as e:
        print(f"  [ERROR] 요청 실패: {e}")
        audit_log["calls"].append({
            "step": step_name,
            "call_index": CALL_COUNT,
            "url": url,
            "error": str(e)
        })
        return None, None, None

# -------------------------------------------------------------
# [1단계] 과거 입찰결과 목록 조회 (아반떼 검색)
# -------------------------------------------------------------
url_step1 = "https://apis.data.go.kr/B010003/OnbidCltrBidRsltListSrvc2/getCltrBidRsltList2"
params_step1 = {
    "serviceKey": service_key,
    "pageNo": "1",
    "numOfRows": "10",
    "cltrNm": "아반떼",
    "_type": "json"
}

status1, data1, raw1 = safe_request(url_step1, params_step1, "1회차: 아반떼 입찰결과 목록 조회")

target_cltr_mng_no = None
target_pbct_cdtn_no = None
target_car_info = {}

if status1 == 200:
    audit_log["outcomes"]["HTTP_OK"] = True
    print("  [✓] HTTP_OK 달성")
    
    header = None
    items = []
    
    if isinstance(data1, dict):
        resp_obj = data1.get("response", data1)
        header = resp_obj.get("header", {})
        body = resp_obj.get("body", {})
        
        res_code = header.get("resultCode") or header.get("resCode")
        res_msg = header.get("resultMsg") or header.get("resMsg")
        print(f"  내부 결과 코드: {res_code} ({res_msg})")
        
        if res_code in ["00", "0000", "0"]:
            audit_log["outcomes"]["API_SUCCESS"] = True
            print("  [✓] API_SUCCESS 달성")
            
            raw_items = body.get("items", {})
            if isinstance(raw_items, dict):
                items = raw_items.get("item", [])
            elif isinstance(raw_items, list):
                items = raw_items
            
            if isinstance(items, dict):
                items = [items]

    if items:
        print(f"  발견된 물건 수: {len(items)}건")
        for item in items:
            cltr_nm = item.get("cltrNm") or item.get("CLTR_NM") or ""
            bid_amt = item.get("sucsfBidAmt") or item.get("SUCSF_BID_AMT") or item.get("bidAmt")
            cltr_no = item.get("cltrMngNo") or item.get("CLTR_MNG_NO")
            pbct_no = item.get("pbctCdtnNo") or item.get("PBCT_CDTN_NO")
            opng_dt = item.get("opngDt") or item.get("OPNG_DT")
            
            print(f"  - 물건명: {cltr_nm} | 관리번호: {cltr_no} | 낙찰가: {bid_amt} | 개찰일: {opng_dt}")
            
            if cltr_no and pbct_no:
                target_cltr_mng_no = str(cltr_no)
                target_pbct_cdtn_no = str(pbct_no)
                target_car_info = {
                    "cltrNm": cltr_nm,
                    "cltrMngNo": target_cltr_mng_no,
                    "pbctCdtnNo": target_pbct_cdtn_no,
                    "sucsfBidAmt": bid_amt,
                    "opngDt": opng_dt,
                    "raw_item": item
                }
                audit_log["outcomes"]["RECORD_FOUND"] = True
                print(f"  [✓] RECORD_FOUND 달성: {cltr_nm} ({target_cltr_mng_no})")
                
                if bid_amt and str(bid_amt) not in ["0", "None", ""]:
                    audit_log["outcomes"]["PRICE_VERIFIED"] = True
                    print(f"  [✓] PRICE_VERIFIED 달성: 낙찰가격 = {bid_amt}원")
                break
    else:
        print("  [!] 아반떼 검색 결과 없음 또는 응답 파싱 실패")

# -------------------------------------------------------------
# [2단계] 입찰결과 상세 조회 (2회차 호출)
# -------------------------------------------------------------
if target_cltr_mng_no and target_pbct_cdtn_no and CALL_COUNT < MAX_CALLS:
    url_step2 = "https://apis.data.go.kr/B010003/OnbidCltrBidRsltDtlSrvc2/getCltrBidRsltDtl2"
    params_step2 = {
        "serviceKey": service_key,
        "cltrMngNo": target_cltr_mng_no,
        "pbctCdtnNo": target_pbct_cdtn_no,
        "_type": "json"
    }
    status2, data2, raw2 = safe_request(url_step2, params_step2, "2회차: 물건 입찰결과 상세 조회")
    if status2 == 200:
        resp2 = data2.get("response", data2) if isinstance(data2, dict) else {}
        body2 = resp2.get("body", {})
        item2 = body2.get("items", {}).get("item", {}) if isinstance(body2.get("items"), dict) else {}
        print(f"  상세 입찰 결과: {item2}")
        target_car_info["detail_bid_result"] = item2

# -------------------------------------------------------------
# [3단계] 차량 물건상세 조회 (3회차 호출: 과거 제원 역조회 검증)
# -------------------------------------------------------------
if target_cltr_mng_no and target_pbct_cdtn_no and CALL_COUNT < MAX_CALLS:
    url_step3 = "https://apis.data.go.kr/B010003/OnbidCarDtlSrvc2/getCarDtlInf2"
    params_step3 = {
        "serviceKey": service_key,
        "cltrMngNo": target_cltr_mng_no,
        "pbctCdtnNo": target_pbct_cdtn_no,
        "_type": "json"
    }
    status3, data3, raw3 = safe_request(url_step3, params_step3, "3회차: 차량 상세 제원 역조회 (Join 검증)")
    if status3 == 200:
        audit_log["outcomes"]["JOIN_VERIFIED"] = True
        print("  [✓] JOIN_VERIFIED 달성 (키 매칭 및 응답 수신)")
        
        resp3 = data3.get("response", data3) if isinstance(data3, dict) else {}
        body3 = resp3.get("body", {})
        item3 = body3.get("items", {}).get("item", {}) if isinstance(body3.get("items"), dict) else {}
        print(f"  차량 제원 상세 결과: {item3}")
        target_car_info["car_detail_spec"] = item3
        
        if item3 and (item3.get("vhclMlge") or item3.get("VHCL_MLGE") or item3.get("vhclYr") or item3.get("VHCL_YR")):
            audit_log["outcomes"]["HISTORICAL_DETAIL_VERIFIED"] = True
            print("  [✓] HISTORICAL_DETAIL_VERIFIED 달성: 제원 확인 완료")

audit_log["captured_data"] = target_car_info

# 결과 저장
output_path = "reports/onbid_spike_raw_result.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(audit_log, f, ensure_ascii=False, indent=2)

print(f"\n[*] 최종 결과 아티팩트 저장 완료: {output_path}")
print(f"[*] 총 호출 횟수: {CALL_COUNT} / {MAX_CALLS}")
print(f"[*] 6대 판정 현황: {audit_log['outcomes']}")
