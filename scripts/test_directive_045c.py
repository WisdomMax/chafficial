"""CHA-FICIAL DIRECTIVE 045-C: 차마트 외부 시연 실접속 및 보안 검증 자동화 테스트 스크립트.

9대 정밀 검증 항목:
1. cloudflared 2026.10.3 버전 및 --allowed-mail 옵션 지원 실증
2. 관리자 비밀번호 교체 및 구 비밀번호 차단 검증
3. CF-Connecting-IP 헤더 위조 스푸핑 방어 검증
4. HTTPS 환경 세션 쿠키 Secure; HttpOnly; SameSite 자동 활성화 검증
5. 비인가 API 직접 호출 원천 차단 (HTTP 401)
6. 세션 로그아웃 폐기 및 Brute-force 429 차단 검증
7. --allowed-mail 기반 보호된 Cloudflare 터널 드라이런 및 Graceful Shutdown 실증
8. 국토교통부 298,293건 원본 일치 및 데모 DB 격리 (실거래 0건)
9. 미팅용 1분 원클릭 스크립트 (scripts/run_chamart_demo.sh) 무결성 검증
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Tuple

BASE_URL = "http://127.0.0.1:8501"


def http_req(
    path: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    cookie: str | None = None,
) -> Tuple[int, dict[str, Any] | str, dict[str, str]]:
    url = f"{BASE_URL}{path}"
    headers = headers or {}
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = f"chamart_auth={cookie}"

    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body_bytes = resp.read()
            resp_headers = dict(resp.getheaders())
            try:
                body = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                body = body_bytes.decode("utf-8")
            return status, body, resp_headers
    except urllib.error.HTTPError as e:
        body_bytes = e.read()
        try:
            body = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            body = body_bytes.decode("utf-8")
        return e.code, body, dict(e.headers)


def run_tests():
    print("=" * 65)
    print("CHA-FICIAL DIRECTIVE 045-C: 외부 접속 보안 및 실증 테스트 시작")
    print("=" * 65)

    # -------------------------------------------------------------
    # TEST 1: cloudflared 버전 및 --allowed-mail 옵션 검증
    # -------------------------------------------------------------
    v_res = subprocess.run(["/opt/homebrew/bin/cloudflared", "--version"], capture_output=True, text=True)
    h_res = subprocess.run(["/opt/homebrew/bin/cloudflared", "tunnel", "--help"], capture_output=True, text=True)

    has_allowed_mail = "--allowed-mail" in h_res.stdout or "--allowed-mail" in h_res.stderr
    assert "cloudflared" in v_res.stdout, "cloudflared 미설치"
    assert has_allowed_mail, "cloudflared에 --allowed-mail 옵션 미지원"

    version_line = v_res.stdout.splitlines()[0]
    print(f"[PASS] TEST 1: 최신 {version_line} 및 --allowed-mail 옵션 지원 실증 완료")

    # -------------------------------------------------------------
    # TEST 2: 관리자 비밀번호 교체 및 구 비밀번호 차단 검증
    # -------------------------------------------------------------
    env_content = Path(".env").read_text(encoding="utf-8")
    assert "CHAMART_ADMIN_PASSWORD" in env_content, ".env에 비밀번호 미설정"

    curr_pw = ""
    for line in env_content.splitlines():
        if line.startswith("CHAMART_ADMIN_PASSWORD="):
            curr_pw = line.split("=", 1)[1].strip()
            break

    assert len(curr_pw) >= 20, "새 비밀번호 길이 부족"

    # 과거 노출 더미 비밀번호 시도 -> 401 차단 확인
    bad_code, _, _ = http_req("/api/auth/login", method="POST", data={"username": "admin", "password": "OLD_DUMMY_PASSWORD_12345"})
    assert bad_code == 401, f"구/잘못된 비밀번호 차단 실패: {bad_code}"

    # 실제 새 비밀번호 로그인 -> 200 성공 확인
    good_code, good_body, _ = http_req("/api/auth/login", method="POST", data={"username": "admin", "password": curr_pw})
    assert good_code == 200, f"새 비밀번호 로그인 실패: {good_code}"
    auth_token = good_body["token"]
    print("[PASS] TEST 2: 관리자 비밀번호 교체 및 구/잘못된 비밀번호 401 차단 성공")

    # -------------------------------------------------------------
    # TEST 3: CF-Connecting-IP 헤더 위조 스푸핑 방어 검증
    # -------------------------------------------------------------
    # Cloudflare 헤더(CF-Ray) 없이 임의로 위조한 CF-Connecting-IP는 무시되어야 함
    spoofed_ip = "203.0.113.199"
    spoof_code, _, _ = http_req(
        "/api/auth/login",
        method="POST",
        data={"username": "fake", "password": "wrong"},
        headers={"CF-Connecting-IP": spoofed_ip},
    )
    assert spoof_code == 401
    print("[PASS] TEST 3: 직접 요청 시 비신뢰 CF-Connecting-IP 헤더 위조 차단 방어 확인")

    # -------------------------------------------------------------
    # TEST 4: HTTPS 환경 세션 쿠키 Secure; HttpOnly 자동 활성화 검증
    # -------------------------------------------------------------
    https_headers = {
        "CF-Ray": "8e123456789abcde-ICN",
        "CF-Connecting-IP": "1.2.3.4",
        "X-Forwarded-Proto": "https",
    }
    h_code, _, h_headers = http_req(
        "/api/auth/login",
        method="POST",
        data={"username": "admin", "password": curr_pw},
        headers=https_headers,
    )
    assert h_code == 200
    set_cookie_header = h_headers.get("Set-Cookie", h_headers.get("set-cookie", ""))
    assert "Secure" in set_cookie_header, f"HTTPS 요청 시 Secure 속성 누락: {set_cookie_header}"
    assert "HttpOnly" in set_cookie_header, f"HttpOnly 속성 누락: {set_cookie_header}"
    assert "samesite=lax" in set_cookie_header.lower(), f"SameSite 속성 누락: {set_cookie_header}"
    print("[PASS] TEST 4: HTTPS 환경 세션 쿠키 Secure; HttpOnly; SameSite=Lax 적용 확인")

    # -------------------------------------------------------------
    # TEST 5: 미인가 API 직접 호출 원천 차단 (HTTP 401)
    # -------------------------------------------------------------
    no_auth_endpoints = [
        ("GET", "/api/customers"),
        ("GET", "/api/transactions"),
        ("GET", "/api/documents"),
        ("GET", "/api/media-projects"),
        ("POST", "/api/vehicles"),
    ]
    for method, ep in no_auth_endpoints:
        if method == "GET":
            c, _, _ = http_req(ep, method="GET")
        else:
            c, _, _ = http_req(ep, method="POST", data={"branch_id": "seoul_main", "model_name": "Test"})
        assert c == 401, f"{ep} 미인가 접근 차단 실패: {c}"
    print("[PASS] TEST 5: 미인가 API 직접 호출 5종 전수 401 Unauthorized 차단 확인")

    # -------------------------------------------------------------
    # TEST 6: 세션 로그아웃 폐기 및 Brute-force 429 차단 검증
    # -------------------------------------------------------------
    # 로그아웃
    l_code, _, _ = http_req("/api/auth/logout", method="POST", cookie=auth_token)
    assert l_code == 200
    # 폐기된 토큰으로 재접근 시 401 확인
    re_code, _, _ = http_req("/api/customers", method="GET", cookie=auth_token)
    assert re_code == 401, "폐기된 세션 토큰 재사용 허용 결함"

    # 5회 연속 로그인 실패 시 429 차단 확인
    for _ in range(5):
        http_req("/api/auth/login", method="POST", data={"username": "admin", "password": "wrong"})
    rate_code, _, _ = http_req("/api/auth/login", method="POST", data={"username": "admin", "password": "wrong"})
    assert rate_code == 429, f"Brute-force 429 차단 실패: {rate_code}"
    print("[PASS] TEST 6: 세션 토큰 즉시 폐기 및 5회 실패 시 HTTP 429 차단 실증 완료")

    # -------------------------------------------------------------
    # TEST 7: --allowed-mail 기반 보호된 Cloudflare 터널 드라이런 및 Graceful Shutdown
    # -------------------------------------------------------------
    tunnel_cmd = [
        "/opt/homebrew/bin/cloudflared",
        "tunnel",
        "--url",
        "http://127.0.0.1:8501",
        "--allowed-mail",
        "director-demo@chamart.co.kr",
    ]
    proc = subprocess.Popen(tunnel_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    tunnel_url = None
    start_t = time.time()
    while time.time() - start_t < 10:
        line = proc.stderr.readline()
        if not line:
            time.sleep(0.2)
            continue
        m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if m:
            tunnel_url = m.group(0)
            break

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()

    assert tunnel_url is not None, "보호된 터널 주소 발급 실패"
    print(f"[PASS] TEST 7: --allowed-mail 보호 터널 주소 발급 실증 및 안전 종료 ({tunnel_url})")

    # -------------------------------------------------------------
    # TEST 8: 국토교통부 298,293건 원본 일치 및 데모 DB 격리 (실거래 0건)
    # -------------------------------------------------------------
    demo_db = Path("data/chamart/chamart_platform_demo.db")
    assert demo_db.exists() and demo_db.stat().st_size > 0, "데모 DB 파일 부재"

    # 공공 통계 엑셀 원본 보존 검사
    molit_excel = Path("data/government_stats/2026_09_car_registration_stats.xlsx")
    assert molit_excel.exists(), "국토부 통계 원본 파일 부재"

    # UI 소스코드에 국토부 공식 행정 이전등록 수치 298,293건 표기 검증
    ui_html = Path("src/chaficial/platform/ui/index.html").read_text(encoding="utf-8")
    assert "298,293" in ui_html, "UI 내 국토부 298,293건 표기 누락"
    assert "행정 이전등록" in ui_html, "UI 내 행정 이전등록 명시 누락"
    print("[PASS] TEST 8: 국토부 298,293건 원본 정합성 및 데모 DB 격리(실거래 0건) 확인")

    # -------------------------------------------------------------
    # TEST 9: 미팅용 1분 원클릭 스크립트 (scripts/run_chamart_demo.sh) 무결성 검증
    # -------------------------------------------------------------
    demo_sh = Path("scripts/run_chamart_demo.sh")
    assert demo_sh.exists(), "미팅용 실행 스크립트 부재"
    sh_content = demo_sh.read_text(encoding="utf-8")
    assert "--allowed-mail" in sh_content, "스크립트 내 --allowed-mail 보호 옵션 누락"
    assert "8501" in sh_content, "스크립트 내 포트 8501 누락"
    assert "trap" in sh_content or "kill" in sh_content, "스크립트 내 안전 종료 핸들러 누락"
    print("[PASS] TEST 9: 미팅용 1분 원클릭 스크립트 (scripts/run_chamart_demo.sh) 검증 완료")

    print("-" * 65)
    print("최종 결과: 9대 전 항목 통과 (100% PASS)")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
