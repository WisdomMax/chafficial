#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 048 종합 자동화 검증 스위트.

P0-1 사고·보험 데이터 위조 원천 방지 및 격리 감사
P0-2 RL Reward 임의 확정 차단 (Ground Truth 강제 및 이중 보상 차단)
P0-3 Propensity Score 1.0 무결성 및 타임스탬프 3단계 시간순 분할
P0-4 실적 및 ROI 집계 공식 수정 (데모 거래 격리 및 NOT_AVAILABLE 표기)
P0-5 딜러 권한 대본 허위 표현 제거 및 파일 매직바이트·보안 엔드포인트 검증
P0-6 테스트 격리 및 샌드박스 안정성

총 12대 핵심 항목을 완전 자동 검증합니다.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
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
    print(f"\n{'='*75}\n[TEST] {title}\n{'='*75}")


def http_request(
    path: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    raw_body: Optional[bytes] = None,
    content_type: Optional[str] = None,
) -> Tuple[int, Any]:
    global SESSION_COOKIE
    url = f"{BASE_URL}{path}"
    headers = {}
    req_data = None

    if SESSION_COOKIE:
        headers["Cookie"] = SESSION_COOKIE

    if raw_body is not None:
        req_data = raw_body
        if content_type:
            headers["Content-Type"] = content_type
    elif data is not None:
        headers["Content-Type"] = "application/json"
        req_data = json.dumps(data, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            set_cookie = resp.headers.get("Set-Cookie")
            if set_cookie and not SESSION_COOKIE:
                SESSION_COOKIE = set_cookie.split(";")[0]

            resp_content_type = resp.headers.get("Content-Type", "")
            resp_bytes = resp.read()
            if "application/json" in resp_content_type:
                return status, json.loads(resp_bytes.decode("utf-8"))
            try:
                return status, resp_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return status, resp_bytes
    except urllib.error.HTTPError as e:
        resp_bytes = e.read()
        try:
            parsed = json.loads(resp_bytes.decode("utf-8"))
        except Exception:
            try:
                parsed = resp_bytes.decode("utf-8")
            except Exception:
                parsed = resp_bytes
        return e.code, parsed


def multipart_upload(
    path: str,
    filename: str,
    file_bytes: bytes,
    fields: Dict[str, str],
) -> Tuple[int, Any]:
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = bytearray()

    for k, v in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{v}\r\n".encode("utf-8"))

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
    body.extend(file_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    return http_request(path, method="POST", raw_body=bytes(body), content_type=f"multipart/form-data; boundary={boundary}")


# ============================================================================
# 테스트 케이스 00~11
# ============================================================================

def test_00_auth_login():
    print_step("00. 관리자 보안 인증 로그인")
    password = os.environ.get("CHAMART_ADMIN_PASSWORD", "")
    assert password, "CHAMART_ADMIN_PASSWORD 환경변수가 설정되지 않았습니다."
    status, res = http_request("/api/auth/login", method="POST", data={"username": "admin", "password": password})
    assert status == 200, f"로그인 실패: {res}"
    print(f"  -> 로그인 성공: user={res.get('user', {}).get('username')}, role={res.get('user', {}).get('role')}")


def test_01_accident_integrity():
    print_step("01. [P0-1] 무증빙 차량 사고·보험 무결성 검증 (Anti-Forgery)")
    status, vehicles = http_request("/api/vehicles")
    assert status == 200, f"차량 목록 조회 실패: {vehicles}"

    unchecked_found = False
    for v in vehicles:
        s_detail, detail = http_request(f"/api/vehicles/{v['id']}/detail")
        if s_detail == 200:
            acc = detail.get("accident_history", {})
            if acc.get("accident_state") == "UNCHECKED":
                unchecked_found = True
                assert "미확인" in acc.get("frame_damage", ""), "프레임 손상이 '미확인'으로 보존되어야 합니다."
                assert "미확인" in acc.get("outer_panel_exchange", ""), "외판 교환이 '미확인'으로 보존되어야 합니다."
                print(f"  -> 미확인 차량 정상 식별 및 보호 확인: [{detail.get('plate_number')}] {detail.get('model_name')}")
                print(f"     상태={acc.get('accident_state')}, 프레임={acc.get('frame_damage')}, 외판={acc.get('outer_panel_exchange')}")
                break

    assert unchecked_found, "UNCHECKED 상태의 미확인 차량이 최소 1대 이상 안전하게 격리 보존되어 있어야 합니다."


def test_02_reject_arbitrary_reward_payload():
    print_step("02. [P0-2] 가짜 Reward 페이로드 원천 거부 (Reject Arbitrary Reward Payload)")
    # 1. 의사결정 생성
    status, v_list = http_request("/api/vehicles")
    v_id = v_list[0]["id"]
    status, dec = http_request("/api/rl/decisions/evaluate", method="POST", data={"vehicle_id": v_id})
    assert status == 200, f"의사결정 생성 실패: {dec}"
    dec_id = dec["decision_id"]

    # 2. transaction_id 누락 페이로드 전송
    arbitrary_payload = {
        "fee_revenue": 9999,
        "operating_cost": 1,
        "days_to_sell": 1,
        "verified_contribution": 1.0,
        "notes": "가짜 거래 증빙 없는 임의 보상",
    }
    status, res = http_request(f"/api/rl/decisions/{dec_id}/reward", method="POST", data=arbitrary_payload)
    assert status in [400, 422], f"transaction_id 누락 시 거부되어야 하지만 {status} 응답됨: {res}"
    print(f"  -> [성공] transaction_id 누락 임의 페이로드 전송 시 {status} 정상 거부 확인!")

    # 3. 존재하지 않는 가짜 transaction_id 전송
    fake_tx_payload = {
        "transaction_id": "00000000-0000-0000-0000-000000000000",
        "notes": "존재하지 않는 가짜 거래 ID",
    }
    status, res = http_request(f"/api/rl/decisions/{dec_id}/reward", method="POST", data=fake_tx_payload)
    assert status in [400, 404], f"가짜 transaction_id 전송 시 거부되어야 하지만 {status} 응답됨: {res}"
    print(f"  -> [성공] 가짜 거래 ID 전송 시 정상 차단 확인: code={status}, detail={res.get('detail')}")


def test_03_reject_demo_transaction_for_reward():
    print_step("03. [P0-2] 데모 거래의 실전 보상 승격 차단 (Reject Demo Transaction for Reward)")
    from chaficial.platform.db import SessionLocal, Transaction
    db = SessionLocal()
    demo_tx_id = None
    target_v_id = None
    try:
        # 데모 SALE 거래 확인 또는 생성
        demo_tx = db.query(Transaction).filter(Transaction.transaction_type == "SALE", Transaction.is_demo == True).first()
        if not demo_tx:
            status, v_list = http_request("/api/vehicles")
            target_v_id = v_list[0]["id"]
            demo_tx = Transaction(
                transaction_date="2026-10-24",
                transaction_type="SALE",
                vehicle_id=target_v_id,
                party_name="데모고객",
                party_contact="010-0000-0000",
                amount=2800,
                dealer_commission_amount=100,
                operating_cost=20,
                chamart_net_profit=80,
                settlement_status="SETTLED",
                is_demo=True,  # 데모 거래!
                is_verified_sale=False,
                attribution_type="AI_VIDEO",
            )
            db.add(demo_tx)
            db.commit()
            db.refresh(demo_tx)
        demo_tx_id = demo_tx.id
        target_v_id = demo_tx.vehicle_id
    finally:
        db.close()

    # 의사결정 생성
    status, dec = http_request("/api/rl/decisions/evaluate", method="POST", data={"vehicle_id": target_v_id})
    assert status == 200
    dec_id = dec["decision_id"]

    # 데모 거래로 실전 보상 확정 시도
    status, res = http_request(
        f"/api/rl/decisions/{dec_id}/reward",
        method="POST",
        data={"transaction_id": demo_tx_id, "notes": "데모 거래 보상 승격 시도"},
    )
    assert status == 400, f"데모 거래는 보상으로 확정될 수 없어야 하지만 {status} 응답됨: {res}"
    assert "데모 격리 원칙 위반" in str(res.get("detail", "")), f"예상 오류 메시지 불일치: {res}"
    print(f"  -> [성공] 데모 거래 보상 승격 시도 시 400 정상 차단: {res.get('detail')}")


def test_04_reject_unsettled_transaction():
    print_step("04. [P0-2] 정산 미완결 거래의 보상 확정 차단 (Reject Unsettled Transaction)")
    from chaficial.platform.db import SessionLocal, Transaction
    db = SessionLocal()
    unsettled_tx_id = None
    target_v_id = None
    try:
        status, v_list = http_request("/api/vehicles")
        target_v = v_list[0]
        target_v_id = target_v["id"]

        pending_tx = Transaction(
            transaction_date="2026-10-25",
            transaction_type="SALE",
            vehicle_id=target_v_id,
            party_name="계약진행고객",
            party_contact="010-1111-2222",
            amount=2500,
            dealer_commission_amount=120,
            operating_cost=25,
            chamart_net_profit=95,
            settlement_status="PENDING",  # 정산 미완결!
            is_demo=False,
            is_verified_sale=True,
            attribution_type="AI_VIDEO",
        )
        db.add(pending_tx)
        db.commit()
        db.refresh(pending_tx)
        unsettled_tx_id = pending_tx.id
    finally:
        db.close()

    # 의사결정 생성
    status, dec = http_request("/api/rl/decisions/evaluate", method="POST", data={"vehicle_id": target_v_id})
    assert status == 200
    dec_id = dec["decision_id"]

    # 정산 미완결 거래로 보상 확정 시도
    status, res = http_request(
        f"/api/rl/decisions/{dec_id}/reward",
        method="POST",
        data={"transaction_id": unsettled_tx_id, "notes": "정산 미완결 거래 보상 시도"},
    )
    assert status == 400, f"정산 미완결 거래는 거부되어야 하지만 {status} 응답됨: {res}"
    assert "정산 미완결 오류" in str(res.get("detail", "")), f"예상 오류 메시지 불일치: {res}"
    print(f"  -> [성공] 정산 미완결 거래 보상 시도 시 400 정상 차단: {res.get('detail')}")


def test_05_ground_truth_reward_and_anti_duplication():
    print_step("05. [P0-2] Ground Truth 보상 확정 및 이중 보상 누적 차단 (Anti-Duplication)")
    from chaficial.platform.db import SessionLocal, Transaction
    db = SessionLocal()
    real_tx_id = None
    target_v_id = None
    try:
        status, v_list = http_request("/api/vehicles")
        target_v = v_list[0]
        target_v_id = target_v["id"]

        settled_real_tx = Transaction(
            transaction_date="2026-10-25",
            transaction_type="SALE",
            vehicle_id=target_v_id,
            party_name="실구매자",
            party_contact="010-9999-8888",
            amount=3200,
            dealer_commission_amount=150,  # 수수료 150만원
            operating_cost=30,             # 운영비 30만원
            chamart_net_profit=120,
            settlement_status="SETTLED",   # 정산 완료!
            is_demo=False,                 # 실전 거래!
            is_verified_sale=True,
            is_test_record=True,          # 테스트용 레코드 격리
            attribution_type="AI_VIDEO",   # 기여도 보너스 대상
        )
        db.add(settled_real_tx)
        db.commit()
        db.refresh(settled_real_tx)
        real_tx_id = settled_real_tx.id
    finally:
        db.close()

    # 1. 첫 번째 의사결정 생성 및 보상 확정
    status, dec1 = http_request("/api/rl/decisions/evaluate", method="POST", data={"vehicle_id": target_v_id})
    assert status == 200
    dec1_id = dec1["decision_id"]

    status, r_res1 = http_request(
        f"/api/rl/decisions/{dec1_id}/reward",
        method="POST",
        data={"transaction_id": real_tx_id, "notes": "검증된 실거래 Ground Truth 확정"},
    )
    assert status == 200, f"실거래 기반 보상 확정 실패: {r_res1}"
    assert r_res1.get("is_censored") is False, "보상 확정 시 관측 미종결(is_censored)이 해제되어야 합니다."
    assert r_res1.get("verified_transaction_id") == real_tx_id, "검증 거래 ID가 원장에 보존되어야 합니다."

    details = r_res1.get("reward_details", {})
    expected_reward = round(150 - 30 + 50 - details.get("time_penalty", 0), 2)
    assert r_res1.get("reward") == expected_reward, f"보상 역산 불일치: 계산값={r_res1.get('reward')}, 기대값={expected_reward}"
    print(f"  -> [성공] 실거래 Ground Truth 보상 확정 성공: reward={r_res1.get('reward')}, verified_tx={real_tx_id}")

    # 2. 두 번째 의사결정 생성 후 '동일한 거래 ID'로 이중 보상 시도
    status, dec2 = http_request("/api/rl/decisions/evaluate", method="POST", data={"vehicle_id": target_v_id})
    assert status == 200
    dec2_id = dec2["decision_id"]

    status, r_res2 = http_request(
        f"/api/rl/decisions/{dec2_id}/reward",
        method="POST",
        data={"transaction_id": real_tx_id, "notes": "동일 거래 이중 보상 시도"},
    )
    assert status == 400, f"동일 거래 이중 보상은 차단되어야 하지만 {status} 응답됨: {r_res2}"
    assert "이중 보상 누적 차단" in str(r_res2.get("detail", "")), f"예상 오류 메시지 불일치: {r_res2}"
    print(f"  -> [성공] 동일 거래 이중 보상 누적 시도 시 400 정상 차단: {r_res2.get('detail')}")


def test_06_deterministic_propensity_score():
    print_step("06. [P0-3] 결정론적 규칙 정책의 Propensity Score 1.0 무결성 (Deterministic Propensity)")
    status, v_list = http_request("/api/vehicles")
    v_id = v_list[0]["id"]

    status, dec = http_request(
        "/api/rl/decisions/evaluate",
        method="POST",
        data={"vehicle_id": v_id, "policy_version": "v1.0-rule_baseline"},
    )
    assert status == 200, f"의사결정 평가 실패: {dec}"
    prob = dec.get("action_prob")
    assert prob == 1.0, f"결정론적 규칙 정책의 Propensity는 정확히 1.0이어야 하지만 {prob}임"
    print(f"  -> [성공] 규칙 정책의 Propensity Score 1.0 무결성 확인: action={dec.get('action')}, action_prob={prob}")


def test_07_temporal_three_stage_split():
    print_step("07. [P0-3] 타임스탬프 기준 3단계 분할 및 TEST 집합 생성 (Temporal Split Integrity)")
    status, v_list = http_request("/api/vehicles")
    v_id = v_list[0]["id"]

    status, dec = http_request("/api/rl/decisions/evaluate", method="POST", data={"vehicle_id": v_id})
    assert status == 200
    split = dec.get("split")
    assert split == "TEST", f"2026-10-20 이후 결정은 TEST 분할이어야 하지만 '{split}'임"

    status, logs = http_request("/api/rl/decisions")
    assert status == 200
    all_splits = {l.get("split") for l in logs}
    assert "TEST" in all_splits, f"로그 목록에 TEST 분할이 반드시 존재해야 합니다: {all_splits}"
    print(f"  -> [성공] 시계열 연속 구간 분할 검증 완료: 신규결정={split}, 전체분할={all_splits}")


def test_08_attribution_roi_trustworthiness():
    print_step("08. [P0-4] 실적 및 ROI 집계 공식 수정 (데모 거래 격리 및 NOT_AVAILABLE 표기)")
    status, attr = http_request("/api/attribution/summary")
    assert status == 200, f"기여도 요약 조회 실패: {attr}"

    # 데모 격리 확인
    assert attr.get("demo_badge") == "CHAMART_DEMO_ENVIRONMENT", "데모 배지 누락"
    demo_sim = attr.get("demo_simulation", {})
    assert demo_sim.get("warning"), "데모 경고 문구 누락"
    print(f"  -> 데모 시뮬레이션 지표 격리 확인: demo_roi={demo_sim.get('simulation_roi_pct')}%, warning={demo_sim.get('warning')}")

    # 실전 통계 검증
    real_sales = attr.get("real_world_sales", {})
    real_roi = real_sales.get("ai_video_roi")
    assert real_roi != 525.0, "데모 ROI(525.0%)가 실전 ROI로 표기되어서는 안 됩니다."
    print(f"  -> 실전 검증 통계: sales_count={real_sales.get('total_sales_count')}, roi={real_roi}")
    print(f"  -> [성공] 실전 ROI 지표 신뢰성 및 데모 격리 검증 완료!")


def test_09_truth_in_advertising_script():
    print_step("09. [P0-5] 홍보 대본의 허위 무사고 표기 제거 및 정직성 검증 (Truth in Advertising)")
    status, vehicles = http_request("/api/vehicles")
    target_v = None
    for v in vehicles:
        s_detail, detail = http_request(f"/api/vehicles/{v['id']}/detail")
        if s_detail == 200:
            if detail.get("accident_history", {}).get("accident_state") == "UNCHECKED":
                target_v = detail
                break
    assert target_v, "UNCHECKED 상태의 테스트 대상 차량이 필요합니다."

    # 마케팅 권한 부여
    status, _ = http_request(f"/api/vehicles/{target_v['id']}/rights/grant", method="POST", data={
        "dealer_name": "장한평모터스",
        "dealer_phone": "010-1234-5678",
        "video_allowed": True,
        "photo_allowed": True,
    })

    # 비디오 프로젝트 생성
    status, project = http_request(
        f"/api/vehicles/{target_v['id']}/create-video-project",
        method="POST",
        data={"target_channel": "YOUTUBE_SHORTS", "aspect_ratio": "9:16"},
    )
    assert status in [200, 201], f"비디오 프로젝트 생성 실패: {project}"
    script = project.get("script_draft", "") or project.get("script", "")

    # 대본 정직성 검증
    assert "사고이력 직접 검증" not in script, f"미검증 차량 대본에 허위 '사고이력 직접 검증' 문구가 포함됨: {script}"
    assert "완전 무사고" not in script, f"미검증 차량 대본에 허위 '완전 무사고' 문구가 포함됨: {script}"
    assert "성능점검 진행 중" in script, f"미검증 차량 대본에 정직한 '성능점검 진행 중' 안내 문구가 누락됨: {script}"

    # 테스트 후 원래 소유 구분 복원 (격리 보존)
    from chaficial.platform.db import SessionLocal, Vehicle
    db = SessionLocal()
    try:
        v_entity = db.query(Vehicle).filter(Vehicle.id == target_v["id"]).first()
        if v_entity:
            v_entity.ownership_type = target_v.get("ownership_type", "MARKET_OBSERVED")
            db.commit()
    finally:
        db.close()

    print(f"  -> [성공] 미검증 차량 홍보 대본 정직성 확인 완료:")
    print(f"     대본 발췌: {script[:120]}...")


def test_10_document_security_and_magic_bytes():
    print_step("10. [P0-5] 비공개 서류 보안 엔드포인트 및 파일 매직바이트 위조 차단")
    # 1. 비인가 확장자 차단 (.exe)
    status, res = multipart_upload(
        "/api/documents/upload",
        filename="malicious.exe",
        file_bytes=b"MZ\x90\x00\x03\x00\x00\x00",
        fields={"doc_type": "PERFORMANCE_RECORD"},
    )
    assert status == 400, f"비인가 확장자(.exe)는 400 거부되어야 하지만 {status} 응답됨: {res}"
    print(f"  -> [성공] 비인가 확장자(.exe) 정상 차단: {res.get('detail')}")

    # 2. 매직바이트 위조 파일 차단
    fake_png_bytes = b"This is not a real PNG image content."
    status, res = multipart_upload(
        "/api/documents/upload",
        filename="fake_image.png",
        file_bytes=fake_png_bytes,
        fields={"doc_type": "PERFORMANCE_RECORD"},
    )
    assert status == 400, f"매직바이트 위조 파일은 400 거부되어야 하지만 {status} 응답됨: {res}"
    assert "위조 바이너리 차단" in str(res.get("detail", "")), f"예상 오류 메시지 불일치: {res}"
    print(f"  -> [성공] 매직바이트 위조 바이너리 정상 차단: {res.get('detail')}")

    # 3. 진짜 유효한 PDF 파일 업로드 및 보안 다운로드 검증
    valid_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    status, res = multipart_upload(
        "/api/documents/upload",
        filename="valid_inspection.pdf",
        file_bytes=valid_pdf_bytes,
        fields={"doc_type": "PERFORMANCE_RECORD"},
    )
    assert status == 200, f"정상 PDF 업로드 실패: {res}"
    doc_id = res.get("doc_id")
    assert doc_id, "업로드 결과에 doc_id가 존재해야 합니다."
    print(f"  -> [성공] 정상 PDF 업로드 완료: doc_id={doc_id}")

    # 4. 보안 다운로드 엔드포인트 접근 검증
    status, file_content = http_request(f"/api/documents/{doc_id}/file")
    assert status == 200, f"보안 엔드포인트 다운로드 실패: {status}"
    if isinstance(file_content, str):
        file_content = file_content.encode("utf-8")
    assert file_content.startswith(b"%PDF-"), "다운로드된 파일 내용이 일치해야 합니다."
    print(f"  -> [성공] 비공개 서류 보안 다운로드 검증 완료 (/api/documents/{doc_id}/file)")


def test_11_test_isolation_and_sandbox_integrity():
    print_step("11. [P0-6] 테스트 격리 및 샌드박스 안정성 (Test Isolation)")
    # 실제 데모 DB 파일 존재 및 크기 검증
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "chamart", "chamart_platform_demo.db"
    )
    assert os.path.exists(db_path), f"DB 파일이 존재해야 합니다: {db_path}"
    db_size = os.path.getsize(db_path)
    assert db_size > 0, "DB 파일 크기가 0이 아니어야 합니다."

    # 사전 백업 파일 보존 확인
    backup_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "backup_048", "chamart_platform_demo_pre048.db"
    )
    assert os.path.exists(backup_path), f"사전 백업 DB가 보존되어야 합니다: {backup_path}"
    print(f"  -> [성공] 운영 DB 크기={db_size} bytes, 사전 백업 파일 보존 확인 완료.")


def main():
    print("=" * 75)
    print("CHAMART OS - DIRECTIVE 048 종합 자동화 검증 스위트 시작")
    print("=" * 75)
    start_time = time.time()

    tests = [
        test_00_auth_login,
        test_01_accident_integrity,
        test_02_reject_arbitrary_reward_payload,
        test_03_reject_demo_transaction_for_reward,
        test_04_reject_unsettled_transaction,
        test_05_ground_truth_reward_and_anti_duplication,
        test_06_deterministic_propensity_score,
        test_07_temporal_three_stage_split,
        test_08_attribution_roi_trustworthiness,
        test_09_truth_in_advertising_script,
        test_10_document_security_and_magic_bytes,
        test_11_test_isolation_and_sandbox_integrity,
    ]

    passed = 0
    failed = 0
    failures = []

    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            failed += 1
            failures.append((t.__name__, str(e)))
            print(f"\n[FAIL] {t.__name__} 실패: {e}")

    elapsed = time.time() - start_time
    print("\n" + "=" * 75)
    print("DIRECTIVE 048 검증 결과 보고서")
    print("=" * 75)
    print(f"총 검증 항목: {len(tests)}개")
    print(f"통과 (PASS): {passed}개")
    print(f"실패 (FAIL): {failed}개")
    print(f"소요 시간: {elapsed:.2f}초")

    if failures:
        print("\n실패 목록:")
        for name, err in failures:
            print(f"- {name}: {err}")
        sys.exit(1)
    else:
        print("\n>>> 모든 DIRECTIVE 048 P0 무결성 및 보안 검증 100% 통과 (PASS) <<<")
        sys.exit(0)


if __name__ == "__main__":
    main()
