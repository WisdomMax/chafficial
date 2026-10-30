#!/usr/bin/env bash
set -e

# Chaficial Daily CarManager Auto-Sync Runner (DIRECTIVE 104 TASK 7)
# Runs daily on Mac mini M4, fully independent of Antigravity session.

PROJECT_DIR="/Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI"
VENV_PYTHON="${PROJECT_DIR}/.venv/bin/python3"
LOG_DIR="${PROJECT_DIR}/logs"
mkdir -p "${LOG_DIR}"
TODAY=$(date "+%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/daily_sync_${TODAY}.log"

echo "========================================================" >> "${LOG_FILE}"
echo "[*] Chaficial Daily Sync Started at $(date)" >> "${LOG_FILE}"
echo "========================================================" >> "${LOG_FILE}"

cd "${PROJECT_DIR}"

# CPU 부하 70% 제한 준수 (nice 우선순위 조정) 및 실시간 수집 옵션(--live) 필수 활성화
nice -n 15 "${VENV_PYTHON}" scripts/run_daily_sync.py --live >> "${LOG_FILE}" 2>&1

echo "========================================================" >> "${LOG_FILE}"
echo "[+] Daily Sync Completed at $(date)" >> "${LOG_FILE}"
echo "========================================================" >> "${LOG_FILE}"
