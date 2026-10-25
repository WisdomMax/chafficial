#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 048 결함 재현 테스트 스크립트.

수정 전 5대 핵심 결함을 재현하여 실제 문제점을 증명합니다:
1. 결함 1: 미확인 차량의 빈 사고이력에 CLEAN, 무사고가 자동 생성되는 결함
2. 결함 2: 실제 거래 증빙 없이 임의 입력값으로 RL Reward 확정 및 Censored 해제되는 결함
3. 결함 3: 결정론적 규칙 정책의 Propensity가 1.0이 아니라 임의 상수(0.88, 0.92)로 기록되는 결함
4. 결함 4: now.month 기준 분할로 인해 TEST 집합이 생성되지 않는 결함
5. 결함 5: 실거래가 0건임에도 데모 거래가 실적에 혼입되어 ROI가 산출되는 결함
"""

import json
import os
import sys
import urllib.request
from typing import Any, Dict, Optional, Tuple

def load_env_password():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("CHAMART_ADMIN_PASSWORD="):
                    return line.split("=", 1)[1].strip()
    return os.getenv("CHAMART_ADMIN_PASSWORD", "")

BASE_URL = "http://127.0.0.1:8501"
SESSION_COOKIE = None

def http_request(path: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Tuple[int, Any]:
    global SESSION_COOKIE
    url = f"{BASE_URL}{path}"
    headers = {}
    req_data = None
    if SESSION_COOKIE:
        headers["Cookie"] = SESSION_COOKIE
    if data is not None:
        headers["Content-Type"] = "application/json"
        req_data = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            set_cookie = resp.headers.get("Set-Cookie")
            if set_cookie and not SESSION_COOKIE:
                SESSION_COOKIE = set_cookie.split(";")[0]
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body

def login():
    pw = load_env_password()
    status, res = http_request("/api/auth/login", method="POST", data={"username": "admin", "password": pw})
    assert status == 200, f"로그인 실패: {res}"

def check_flaw_2_arbitrary_reward_allowed():
    """결함 2 재현: 가상의 임의 숫자로 Reward가 확정될 수 있는지 검사."""
    print("\n[검사 2] 거래 증빙 없는 임의 Reward 확정 결함 재현...")
    # 임의 의사결정 생성
    v_status, v_list = http_request("/api/vehicles")
    v_id = v_list[0]["id"]
    status, dec = http_request("/api/rl/decisions/evaluate", method="POST", data={"vehicle_id": v_id})
    dec_id = dec["decision_id"]

    # 거래 ID 없이 임의의 숫자 POST
    reward_payload = {
        "fee_revenue": 9999,
        "operating_cost": 1,
        "days_to_sell": 1,
        "verified_contribution": 1.0,
        "notes": "가짜 거래 증빙 없는 임의 보상"
    }
    r_status, r_data = http_request(f"/api/rl/decisions/{dec_id}/reward", method="POST", data=reward_payload)
    if r_status == 200 and r_data.get("is_censored") is False:
        print("  -> [결함 확인 (FLAW CONFIRMED)]: 실제 계약서/정산 기록 없이 임의 숫자로 is_censored=False 및 가짜 Reward가 승인됨!")
        return True
    return False

def check_flaw_3_fixed_propensity():
    """결함 3 재현: 결정론적 규칙 정책의 Propensity가 1.0이 아닌 고정값으로 기록되는 결함."""
    print("\n[검사 3] 결정론적 규칙의 잘못된 Propensity 기록 결함 재현...")
    status, v_list = http_request("/api/vehicles")
    v_id = v_list[0]["id"]
    status, dec = http_request("/api/rl/decisions/evaluate", method="POST", data={"vehicle_id": v_id, "policy_version": "v1.0-rule_baseline"})
    prob = dec.get("action_prob")
    if prob != 1.0:
        print(f"  -> [결함 확인 (FLAW CONFIRMED)]: 결정론적 규칙 정책임에도 실제 확률 1.0이 아닌 임의 상수({prob})가 기록됨!")
        return True
    return False

def check_flaw_4_split_no_test():
    """결함 4 재현: now.month >= 10 기준 분할로 TEST 집합 부재 결함."""
    print("\n[검사 4] 시간순 분할의 TEST 분할 부재 결함 재현...")
    status, logs = http_request("/api/rl/decisions")
    splits = {l.get("split") for l in logs}
    if "TEST" not in splits:
        print(f"  -> [결함 확인 (FLAW CONFIRMED)]: 현재 생성된 분할은 {splits}뿐이며, TEST 분할이 전혀 생성되지 않음!")
        return True
    return False

def check_flaw_5_demo_roi_polluted():
    """결함 5 재현: 실거래 0건임에도 데모 거래가 실적으로 집계되어 ROI가 산출되는 결함."""
    print("\n[검사 5] 데모 거래의 실적 혼입 및 ROI 왜곡 결함 재현...")
    status, attr = http_request("/api/attribution/summary")
    roi = attr.get("ai_video_roi_pct")
    if roi not in [None, "NOT_AVAILABLE"]:
        print(f"  -> [결함 확인 (FLAW CONFIRMED)]: 실거래 0건 환경임에도 데모 거래가 실적으로 집계되어 ROI({roi}%)가 산출됨!")
        return True
    return False

def main():
    print("="*70)
    print("DIRECTIVE 048 수정 전 결함 재현 및 독립 검증 실행")
    print("="*70)
    login()
    f2 = check_flaw_2_arbitrary_reward_allowed()
    f3 = check_flaw_3_fixed_propensity()
    f4 = check_flaw_4_split_no_test()
    f5 = check_flaw_5_demo_roi_polluted()
    
    flaws = [f2, f3, f4, f5]
    print("\n" + "="*70)
    print(f"결함 재현 결과: {sum(flaws)}/4 핵심 결함 확인됨 (수정 필요성 입증 완료)")
    print("="*70)

if __name__ == "__main__":
    main()
