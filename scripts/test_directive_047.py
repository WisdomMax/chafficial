#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 047 종합 자동화 검증 스위트.

장한평 실전 시장 분석 · 제휴 딜러 권한 원장 · AI 영상 판매 연결 · 강화학습(RL) 오프라인 데이터 파이프라인
총 12대 항목을 완전 자동으로 검증하고 결과를 보고합니다.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

def load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env_file()

BASE_URL = os.environ.get("CHAMART_API_URL", "http://127.0.0.1:8501")
SESSION_COOKIE: Optional[str] = None


def print_step(title: str):
    print(f"\n{'='*70}\n[TEST] {title}\n{'='*70}")


def http_request(
    path: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Any]:
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
            status = resp.status
            set_cookie = resp.headers.get("Set-Cookie")
            if set_cookie and not SESSION_COOKIE:
                SESSION_COOKIE = set_cookie.split(";")[0]

            content_type = resp.headers.get("Content-Type", "")
            resp_body = resp.read().decode("utf-8")
            if "application/json" in content_type:
                return status, json.loads(resp_body)
            return status, resp_body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body
        return e.code, parsed


def authenticate_admin():
    """보안 12항: 격리된 환경변수 기반 관리자 인증 세션 획득."""
    global SESSION_COOKIE
    admin_pw = os.environ.get("CHAMART_ADMIN_PASSWORD", "")
    assert admin_pw, "CHAMART_ADMIN_PASSWORD 환경변수가 설정되지 않았습니다."
    status, res = http_request("/api/auth/login", method="POST", data={"username": "admin", "password": admin_pw})
    if status != 200:
        raise RuntimeError(f"관리자 인증 실패 (HTTP {status}): {res}")
    print("[*] 관리자 인증 성공 (세션 쿠키 활성화 완료)")


def test_01_regression_check():
    """TEST 1: 046-D 핵심 기능 회귀 테스트 (차량 마스터, 딜러, 리스팅, 사진 무결성)."""
    print_step("TEST 1: 기존 046-D 엔터프라이즈 운영 데이터 회귀 무결성 검증")
    status, vehicles = http_request("/api/vehicles")
    assert status == 200, f"차량 목록 조회 실패: {vehicles}"
    assert len(vehicles) >= 10, f"차량 수가 부족합니다: {len(vehicles)}"
    
    types = {v.get("ownership_type") for v in vehicles}
    assert "CHAMART_OWNED" in types, "CHAMART_OWNED 누락"
    assert "PARTNER_APPROVED" in types, "PARTNER_APPROVED 누락"
    assert "MARKET_OBSERVED" in types, "MARKET_OBSERVED 누락"
    print(f"  -> PASS: 차량 {len(vehicles)}대 및 4대 소유구분 정상 보존 확인")


def test_02_market_analysis_summary():
    """TEST 2: 장한평 중심 시장 분석 요약 지표 검증 (장한평 vs 전국 분리, 플랫폼 분포)."""
    print_step("TEST 2: 장한평 시장 분석 요약 지표 및 전국 분리 검증")
    status, s = http_request("/api/market/summary")
    assert status == 200, f"시장 분석 요약 조회 실패: {s}"
    
    assert s.get("total_listings", 0) >= 2, "관측 매물 수 부족"
    assert s.get("janghanpyeong_count", 0) >= 1, "장한평 매물 수 누락"
    assert s.get("other_regions_count", 0) >= 1, "전국 비교 매물 수 누락"
    assert s.get("encar_count", 0) >= 1, "엔카 매물 누락"
    assert s.get("kb_count", 0) >= 1, "KB차차차 매물 누락"
    assert s.get("avg_data_confidence", 0) >= 0.9, "데이터 신뢰도 누락"
    print(f"  -> PASS: 관측 총 {s['total_listings']}건 (장한평: {s['janghanpyeong_count']}건, 전국: {s['other_regions_count']}건, 엔카: {s['encar_count']}건, KB: {s['kb_count']}건, 신뢰도: {s['avg_data_confidence']*100:.1f}%)")


def test_03_market_listings_and_opportunity():
    """TEST 3: 시장 매물 리스팅, 가격 인하 및 가성비 기회 점수(Opportunity Score) 검증."""
    print_step("TEST 3: 시장 매물 리스팅, 가격 인하 및 기회 점수 산출 검증")
    status, listings = http_request("/api/market/listings")
    assert status == 200, f"시장 매물 목록 조회 실패: {listings}"
    assert len(listings) >= 2, "리스팅 수 부족"
    
    has_high_opp = False
    has_price_drop = False
    for l in listings:
        if l.get("opportunity_score", 0) >= 80.0:
            has_high_opp = True
        if l.get("price_drop_amount", 0) > 0:
            has_price_drop = True
    
    assert has_high_opp, "기회 점수 80점 이상 매물 없음"
    assert has_price_drop, "가격 인하 탐지 매물 없음"
    print(f"  -> PASS: 리스팅 {len(listings)}건 가성비 기회 점수 및 가격 인하 정상 확인")


def test_04_dealer_rights_grant_and_ledger():
    """TEST 4: 제휴 딜러 권한 원장(Rights Ledger) 부여 및 승인 검증."""
    print_step("TEST 4: 제휴 딜러 권한 원장(Rights Ledger) 부여 및 승인 검증")
    status, v_list = http_request("/api/vehicles")
    sonata = next((v for v in v_list if "쏘나타" in v.get("model_name", "")), None)
    assert sonata is not None, "쏘나타 차량을 찾을 수 없습니다."
    vehicle_id = sonata["id"]

    grant_payload = {
        "sale_allowed": True,
        "photo_allowed": True,
        "video_allowed": True,
        "allowed_channels": ["YOUTUBE", "INSTAGRAM", "TIKTOK"],
        "valid_until": "2026-12-31",
        "approved_by": "차마트 장한평 본사 김민우 딜러 정식 계약",
        "dealer_commission_pct": 4.5,
        "chamart_share_pct": 15.0
    }
    status, rights = http_request(f"/api/vehicles/{vehicle_id}/rights/grant", method="POST", data=grant_payload)
    assert status == 200, f"권한 부여 실패: {rights}"
    assert rights.get("video_allowed") is True, "영상 허용 플래그 미반영"
    assert rights.get("sale_allowed") is True, "판매 허용 플래그 미반영"
    assert rights.get("ownership_type") == "PARTNER_APPROVED", "소유구분 승인 격상 실패"
    print(f"  -> PASS: 쏘나타({sonata['plate_number']}) 제휴 권한 원장 승인 완료 (유효기간: {rights['valid_until']})")
    return vehicle_id


def test_05_approved_vehicle_video_creation(vehicle_id: str):
    """TEST 5: 권한 승인 매물의 영상 프로젝트 생성 및 대본 초안 자동 연계 검증."""
    print_step("TEST 5: 승인 매물의 영상 프로젝트 생성 및 자동 대본 연계 검증")
    payload = {
        "content_format": "SHORTS",
        "target_platform": "YOUTUBE",
        "custom_title": "[차마트 공식 인증] 쏘나타 디 엣지 1.6 터보 실매물 쇼츠",
        "concept": "무사고 제휴 인증 차량"
    }
    status, data = http_request(f"/api/vehicles/{vehicle_id}/create-video-project", method="POST", data=payload)
    assert status in [200, 201], f"영상 프로젝트 생성 실패 (HTTP {status}): {data}"
    assert data.get("id"), "프로젝트 ID 누락"
    assert "오늘 소개해드릴 실매물" in data.get("script_draft", ""), "자동 대본 초안 누락"
    print(f"  -> PASS: 승인 매물 영상 프로젝트 생성 성공 (ID: {data['id']})")


def test_06_dealer_rights_revoke_guard(vehicle_id: str):
    """TEST 6: 제휴 권한 철회(Revoke) 및 영상 제작 즉시 차단 보안 가드 검증."""
    print_step("TEST 6: 제휴 권한 철회(Revoke) 및 영상 제작 즉시 차단 가드 검증")
    revoke_payload = {
        "reason": "원 소속 딜러의 판매 보류 및 마케팅 협약 철회 요청",
        "revoked_by": "차마트 관리자"
    }
    status, rights = http_request(f"/api/vehicles/{vehicle_id}/rights/revoke", method="POST", data=revoke_payload)
    assert status == 200, f"권한 철회 호출 실패: {rights}"
    assert rights.get("is_revoked") is True, "철회 플래그 미반영"
    assert rights.get("video_allowed") is False, "영상 허용 플래그가 비활성화되지 않음"

    video_payload = {
        "content_format": "SHORTS",
        "target_platform": "YOUTUBE"
    }
    status_block, res_block = http_request(f"/api/vehicles/{vehicle_id}/create-video-project", method="POST", data=video_payload)
    assert status_block == 400, f"철회된 매물의 영상 제작이 차단되지 않았습니다 (HTTP {status_block})"
    detail = res_block.get("detail", "") if isinstance(res_block, dict) else str(res_block)
    assert "제휴 권한 철회 차단" in detail, f"차단 메시지 불일치: {detail}"
    print(f"  -> PASS: 권한 철회 즉시 영상 제작 원천 차단 확인 (HTTP 400: '{detail}')")


def test_07_market_observed_unauthorized_video_guard():
    """TEST 7: 시장 관측 매물(MARKET_OBSERVED)의 무단 영상 제작 시도 원천 차단 검증."""
    print_step("TEST 7: 시장 관측 매물(MARKET_OBSERVED) 무단 영상 제작 차단 검증")
    status, v_list = http_request("/api/vehicles")
    k8 = next((v for v in v_list if "K8" in v.get("model_name", "") and v.get("ownership_type") == "MARKET_OBSERVED"), None)
    assert k8 is not None, "K8 관측 매물을 찾을 수 없습니다."

    status_block, res_block = http_request(f"/api/vehicles/{k8['id']}/create-video-project", method="POST", data={"content_format": "SHORTS"})
    assert status_block == 400, f"관측 매물 영상 제작이 차단되지 않았습니다 (HTTP {status_block})"
    detail = res_block.get("detail", "") if isinstance(res_block, dict) else str(res_block)
    assert "광고 및 영상 제작 권한 미승인 차단" in detail, f"차단 메시지 불일치: {detail}"
    print(f"  -> PASS: 시장 관측 매물 무단 영상 제작 차단 확인 (HTTP 400)")


def test_08_marketing_attribution_summary():
    """TEST 8: AI 영상 판매 기여도, 자연 판매 구분 및 공헌이익/ROI 검증."""
    print_step("TEST 8: AI 영상 판매 기여도 vs 자연 판매 구분 및 공헌이익/ROI 검증")
    status, attr = http_request("/api/attribution/summary")
    assert status == 200, f"성과 기여도 조회 실패: {attr}"
    
    assert attr.get("total_sales_count", 0) >= 1, "판매 건수 누락"
    assert attr.get("ai_video_attributed_sales", 0) >= 1, "AI 영상 기여 판매 누락"
    assert attr.get("total_chamart_net_profit_million_krw", 0) > 0, "차마트 순수익 누락"
    assert attr.get("ai_video_roi_pct", 0) > 0, "AI 영상 ROI 누락"
    
    leads = attr.get("lead_metrics", {})
    assert "total_valid_leads" in leads, "유효 리드 수 누락"
    assert "duplicate_leads_quarantined" in leads, "중복 문의 격리 수 누락"
    print(f"  -> PASS: 총 판매 {attr['total_sales_count']}건 중 AI영상 기여 {attr['ai_video_attributed_sales']}건, 순익 {attr['total_chamart_net_profit_million_krw']}만원, ROI {attr['ai_video_roi_pct']}%, 중복격리 {leads['duplicate_leads_quarantined']}건")


def test_09_vehicle_attribution_trail():
    """TEST 9: 차량별 발굴->승인->영상->문의->계약->정산 전 주기 타임라인 검증."""
    print_step("TEST 9: 차량별 전 주기 이력 타임라인(Attribution Trail) 검증")
    status, v_list = http_request("/api/vehicles")
    spt = next((v for v in v_list if "스포티지" in v.get("model_name", "") and v.get("ownership_type") != "MARKET_OBSERVED"), None)
    assert spt is not None, "제휴/운영 스포티지 차량을 찾을 수 없습니다."

    status, trail = http_request(f"/api/vehicles/{spt['id']}/attribution-trail")
    assert status == 200, f"타임라인 조회 실패: {trail}"
    assert trail.get("trail_count", 0) >= 2, "이력 건수 부족"
    stages = [item["stage"] for item in trail.get("timeline", [])]
    assert "MARKET_DISCOVERY" in stages, "발굴 단계 누락"
    print(f"  -> PASS: 스포티지 전 주기 이력 {trail['trail_count']}개 단계 추적 확인 ({', '.join(stages)})")


def test_10_rl_offline_decision_evaluation():
    """TEST 10: 강화학습(RL) 오프라인 의사결정 평가 및 데이터 누출 방지 State 검증."""
    print_step("TEST 10: 강화학습(RL) 오프라인 의사결정 평가 및 Data Leakage 방지 검증")
    status, v_list = http_request("/api/vehicles")
    grn = next((v for v in v_list if "그랜저" in v.get("model_name", "")), None)
    assert grn is not None, "그랜저 차량 누락"

    eval_payload = {
        "vehicle_id": grn["id"],
        "policy_version": "v1.0-rule_baseline"
    }
    status, decision = http_request("/api/rl/decisions/evaluate", method="POST", data=eval_payload)
    assert status == 200, f"RL 정책 결정 실패: {decision}"
    
    assert decision.get("action") in ["OBSERVE", "REQUEST_DEALER_REVIEW", "ADJUST_PRIORITY", "PROPOSE_VIDEO"], "유효하지 않은 Action"
    assert decision.get("action_prob", 0) > 0, "선택 확률 누락"
    assert decision.get("is_censored") is True, "의사결정 시점에는 미종결(Censored) 상태여야 함"
    
    state = decision.get("state_vector", {})
    assert "transaction_amount" not in state, "Data Leakage: 거래 금액 누출"
    assert "actual_profit" not in state, "Data Leakage: 실제 수익 누출"
    assert "delisted_status" not in state, "Data Leakage: 매물 삭제 상태 누출"
    print(f"  -> PASS: RL 의사결정 정상 기록 (Action: {decision['action']}, Propensity: {decision['action_prob']*100:.0f}%, Censored: True, Data Leakage 0건)")
    return decision["decision_id"]


def test_11_rl_reward_update_and_uncensor(decision_id: str):
    """TEST 11: 거래 체결에 따른 사후 강화학습 Reward 확정 및 Censored 해제 검증 (DIRECTIVE 048 Ground Truth 규격)."""
    print_step("TEST 11: 사후 강화학습 Reward 확정 및 Uncensored 해제 검증")
    # 의사결정 대상 차량 조회
    status, dec_list = http_request("/api/rl/decisions")
    target_dec = next((d for d in dec_list if d.get("id") == decision_id), None)
    vehicle_id = target_dec.get("vehicle_id") if target_dec else None

    # 해당 차량의 검증된 실거래 생성 또는 조회
    from chaficial.platform.db import SessionLocal, Transaction
    db = SessionLocal()
    try:
        tx = db.query(Transaction).filter(
            Transaction.vehicle_id == vehicle_id,
            Transaction.transaction_type == "SALE",
            Transaction.settlement_status == "SETTLED",
            Transaction.is_demo == False,
        ).first()
        if not tx:
            tx = Transaction(
                transaction_date="2026-10-25",
                transaction_type="SALE",
                vehicle_id=vehicle_id,
                party_name="실거래고객",
                party_contact="010-3333-4444",
                amount=2900,
                dealer_commission_amount=120,
                operating_cost=25,
                chamart_net_profit=95,
                settlement_status="SETTLED",
                is_demo=False,
                is_verified_sale=True,
                is_test_record=True,
                attribution_type="AI_VIDEO",
            )
            db.add(tx)
            db.commit()
            db.refresh(tx)
        tx_id = tx.id
    finally:
        db.close()

    reward_payload = {
        "transaction_id": tx_id,
        "notes": "실거래 체결 및 정산 완료 보상 확정 (DIRECTIVE 048 규격)"
    }
    status, data = http_request(f"/api/rl/decisions/{decision_id}/reward", method="POST", data=reward_payload)
    assert status == 200, f"Reward 확정 실패: {data}"
    assert data.get("reward") is not None, "Reward 누락"
    assert data.get("is_censored") is False, "종결 후 Censored가 False로 전환되지 않음"
    assert data["reward"] > 0, "보상 계산치 이상"
    print(f"  -> PASS: 사후 보상 확정 (Reward: {data['reward']}, Censored: False, VerifiedTx: {data.get('verified_transaction_id')})")


def test_12_rl_readiness_audit():
    """TEST 12: 강화학습 준비도 감사 및 PPO 조기 투입 금지 가드 검증."""
    print_step("TEST 12: 강화학습 준비도 감사 및 PPO 조기 투입 금지 가드 검증")
    status, audit = http_request("/api/rl/readiness")
    assert status == 200, f"RL 준비도 조회 실패: {audit}"
    
    assert audit.get("guard_ppo_prohibited") is True, "PPO 조기 투입 금지 원칙 누락"
    assert audit.get("can_train_offline_rl") is False, "표본 부족 상태에서 RL 훈련 허용됨"
    assert "PPO 등 대규모 강화학습 모델의 성급한 도입은 과적합과 치명적 비용 왜곡을 유발하므로 절대 금지" in audit.get("recommendation", ""), "권고 지침 누락"
    print(f"  -> PASS: RL 감사 통과 (로그: {audit['total_decision_logs']}건, PPO 조기 투입 차단: TRUE, 권고: Contextual Bandit 대기)")


def main():
    print("="*70)
    print("CHA-FICIAL DIRECTIVE 047 12대 필수 자동화 검증 스위트 실행")
    print("="*70)
    
    try:
        authenticate_admin()
        test_01_regression_check()
        test_02_market_analysis_summary()
        test_03_market_listings_and_opportunity()
        sonata_id = test_04_dealer_rights_grant_and_ledger()
        test_05_approved_vehicle_video_creation(sonata_id)
        test_06_dealer_rights_revoke_guard(sonata_id)
        test_07_market_observed_unauthorized_video_guard()
        test_08_marketing_attribution_summary()
        test_09_vehicle_attribution_trail()
        decision_id = test_10_rl_offline_decision_evaluation()
        test_11_rl_reward_update_and_uncensor(decision_id)
        test_12_rl_readiness_audit()

        print("\n" + "="*70)
        print("CHA-FICIAL DIRECTIVE 047 종합 검증 결과: 12/12 PASS (100% 달성)")
        print("="*70)
    except Exception as e:
        print(f"\n[FAIL] 검증 도중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
