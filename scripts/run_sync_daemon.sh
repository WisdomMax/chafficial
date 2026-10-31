#!/bin/zsh
cd /Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI || exit 1
export PYTHONPATH=src
exec /Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/.venv/bin/python src/chaficial/platform/sourcing/continuous_sync_daemon.py --daemon --interval 300
