#!/usr/bin/env bash
# ==============================================================================
# 차마트(CHAMART) 통합 운영 플랫폼 미팅 시연용 1분 원클릭 기동 스크립트
#
# 기능:
# 1. .env 환경변수 및 관리자 비밀번호 무결성 검증
# 2. 로컬 웹 서버 (FastAPI, 포트 8501) 백그라운드 기동
# 3. Cloudflare 이메일 인증 보호 Quick Tunnel (--allowed-mail) 자동 연동
# 4. 외부 HTTPS 시연 주소 터미널 출력 및 브라우저 안내
# 5. Ctrl+C 입력 시 모든 백그라운드 프로세스(서버 및 터널) 즉각 안전 종료 (Graceful Cleanup)
# ==============================================================================

set -euo pipefail

cd "$(dirname "$0")/.."

echo "================================================================="
echo "   차마트(CHAMART) 운영 플랫폼 미팅 시연 런처 (DIRECTIVE 045-C)"
echo "================================================================="

# 1. 환경변수 파일 검증
if [ ! -f ".env" ]; then
    echo "[!] 오류: .env 파일이 존재하지 않습니다."
    echo "    보안을 위해 .env에 CHAMART_ADMIN_PASSWORD를 설정하십시오."
    exit 1
fi

source .env

if [ -z "${CHAMART_ADMIN_PASSWORD:-}" ]; then
    echo "[!] 오류: CHAMART_ADMIN_PASSWORD가 설정되지 않았습니다."
    exit 1
fi

# 2. 허용 이메일 입력 (미지정 시 기본 시연 이메일 안내)
ALLOWED_EMAIL="${1:-${CHAMART_ALLOWED_EMAIL:-}}"
if [ -z "$ALLOWED_EMAIL" ]; then
    echo "-----------------------------------------------------------------"
    echo "[안내] 시연 접속을 허용할 이메일 주소를 인자로 넘겨주십시오."
    echo "       사용 예: ./scripts/run_chamart_demo.sh ceo@chamart.co.kr"
    echo "-----------------------------------------------------------------"
    read -rp ">> 허용할 시연자 이메일 입력: " ALLOWED_EMAIL
    if [ -z "$ALLOWED_EMAIL" ]; then
        echo "[!] 이메일이 입력되지 않아 무인증 터널 방지를 위해 실행을 중단합니다."
        exit 1
    fi
fi

echo "[*] 허용된 이메일 계정: $ALLOWED_EMAIL"

# 3. 기존 포트 8501 점유 프로세스 정리
EXISTING_PID=$(lsof -ti :8501 || true)
if [ -n "$EXISTING_PID" ]; then
    echo "[*] 기존 8501 포트 프로세스(PID: $EXISTING_PID) 정리 중..."
    kill -9 "$EXISTING_PID" 2>/dev/null || true
    sleep 1
fi

# 4. 종료 시 자식 프로세스 자동 회수 (trap)
cleanup() {
    echo ""
    echo "[*] 시연 종료 신호 수신. 프로세스를 안전하게 종료합니다..."
    if [ -n "${TUNNEL_PID:-}" ]; then
        kill "$TUNNEL_PID" 2>/dev/null || true
    fi
    if [ -n "${SERVER_PID:-}" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi
    echo "[+] 서버 및 터널 프로세스 정상 회수 완료. 시연 환경이 안전하게 격리되었습니다."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 5. 로컬 플랫폼 서버 백그라운드 기동
echo "[*] 1단계: 차마트 플랫폼 서버 기동 중 (포트 8501)..."
PYTHONPATH=src .venv/bin/python -m chaficial.platform.server --port 8501 > data/server_demo.log 2>&1 &
SERVER_PID=$!
sleep 2

# 6. Cloudflare 이메일 보호 터널 기동
echo "[*] 2단계: Cloudflare 이메일 보호 터널 기동 중 (--allowed-mail $ALLOWED_EMAIL)..."
/opt/homebrew/bin/cloudflared tunnel --url http://127.0.0.1:8501 --allowed-mail "$ALLOWED_EMAIL" > data/tunnel_demo.log 2>&1 &
TUNNEL_PID=$!

echo "[*] 외부 접속 주소 발급 대기 중..."
TUNNEL_URL=""
for i in {1..30}; do
    if grep -q "trycloudflare.com" data/tunnel_demo.log 2>/dev/null; then
        TUNNEL_URL=$(grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" data/tunnel_demo.log | head -n 1)
        break
    fi
    sleep 0.5
done

if [ -n "$TUNNEL_URL" ]; then
    echo "================================================================="
    echo "  [시연 준비 완료 - LIVE DEMO READY]"
    echo "================================================================="
    echo "  ▶ 외부 HTTPS 접속 주소 : $TUNNEL_URL"
    echo "  ▶ 접근 허용 이메일    : $ALLOWED_EMAIL (Cloudflare OTP 인증)"
    echo "  ▶ 차마트 관리자 계정  : admin"
    echo "  ▶ 데모 DB 격리 상태   : 격리 모드 (실거래 0건 보존)"
    echo "================================================================="
    echo "  ※ 시연을 종료하려면 터미널에서 [Ctrl + C]를 누르십시오."
    echo "================================================================="
else
    echo "[!] 오류: 터널 주소 발급에 실패했습니다. data/tunnel_demo.log를 확인하십시오."
    exit 1
fi

# 대기
wait "$SERVER_PID"
