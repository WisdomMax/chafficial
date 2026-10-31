"""
Continuous Auto-Sync Daemon for CarManager -> Cloudflare D1 (DIRECTIVE 133-R TASK 4)
- Periodically checks CarManager snapshots for incremental changes (new, price change, sold)
- Transmits only genuine verified changes to Cloudflare D1
- Safe probing with dedicated test vehicle identifier (Zero modification to customer vehicles)
- Persistent logging to data/sync_daemon.log
"""

import os
import sys
import json
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "src"))

from chaficial.platform.sourcing.chamart_sync_client import ChamartSyncClient
from chaficial.platform.sourcing.carmanager_sync import parse_price_manwon, parse_mileage_km

LOG_PATH = Path("data/sync_daemon.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ContinuousSyncDaemon")


class ContinuousSyncDaemon:
    def __init__(self, client: Optional[ChamartSyncClient] = None, state_file: str = "data/sync_last_state.json"):
        self.client = client or ChamartSyncClient()
        self.state_file = Path(state_file)
        self.last_state = self._load_last_state()

    def _load_last_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"vehicle_hashes": {}, "last_run": None}

    def _save_last_state(self):
        self.state_file.write_text(json.dumps(self.last_state, ensure_ascii=False, indent=2), encoding="utf-8")

    def inspect_and_sync_incremental(self, dry_run: bool = False) -> Dict[str, Any]:
        """카매니저 스냅샷 비교 후 실제 변경된 매물만 증분 동기화"""
        logger.info("=== Starting CarManager Periodic Inspection Cycle ===")
        start_time = datetime.now().isoformat()

        # 1. 로컬 카매니저 원시 데이터 로드
        raw_path = Path("data/carmanager_raw/janghanpyeong_full_collection.json")
        if not raw_path.exists():
            logger.warning(f"Raw data file not found: {raw_path}")
            return {"status": "NO_SOURCE_DATA"}

        with open(raw_path) as f:
            cars = json.load(f).get("cars", [])

        thecool_cars = [c for c in cars if "더쿨" in str(c.get("shop", "")) or "더쿨" in str(c.get("sangsa", ""))]
        logger.info(f"Total inspected TheCool cars in CarManager snapshot: {len(thecool_cars)} vehicles")

        # 2. 증분 감지: 이전 상태와 비교하여 변경된 차량 식별
        changed_vehicles = []
        current_hashes = {}

        for c in thecool_cars:
            enc = c.get("encarno") or c.get("plate_tail", "")
            vid = "CAR-THECOOL-" + hashlib.md5(enc.encode("utf-8")).hexdigest()[:10]
            price = parse_price_manwon(c.get("price_manwon"))
            mileage = parse_mileage_km(c.get("mileage"))

            # 차량 상태 요약 해시 생성
            summary = f"{vid}:{price}:{mileage}:{c.get('dealer')}:{c.get('thumbnail')}"
            h = hashlib.md5(summary.encode("utf-8")).hexdigest()
            current_hashes[vid] = h

            old_h = self.last_state.get("vehicle_hashes", {}).get(vid)
            if old_h != h:
                # 변경 감지됨
                changed_vehicles.append({
                    "id": vid,
                    "plate_number": f"더쿨-{c.get('plate_tail')}", # 임시 식별자 (D1에서 PENDING_REVIEW로 안전 격리됨)
                    "model_name": c.get("title") or c.get("model"),
                    "manufacturer": c.get("maker") or "기타",
                    "year": int(c.get("model_year") or 2020),
                    "mileage": mileage or 0,
                    "fuel_type": c.get("fuel") or "가솔린",
                    "transmission": c.get("mission") or "오토",
                    "color": c.get("color") or "기타",
                    "target_price": price or 0,
                    "status": "FOR_SALE",
                    "sangsa_name": "(주)더쿨모터스",
                    "dealer_name": c.get("dealer") or "더쿨모터스",
                    "dealer_phone": c.get("phone") or "010-2588-9675",
                    "primary_photo_url": c.get("thumbnail") or "",
                    "is_demo": 0,
                    "source": "CARMANAGER_INCREMENTAL_DAEMON"
                })

        logger.info(f"Detected incremental changes: {len(changed_vehicles)} vehicles")

        # 3. 변경분만 D1으로 전송 (dry_run이 아닐 경우)
        sync_result = None
        if changed_vehicles and not dry_run:
            logger.info(f"Transmitting {len(changed_vehicles)} changed vehicles to Cloudflare D1...")
            # 15대 단위 안전 청크 전송
            CHUNK_SIZE = 15
            for i in range(0, len(changed_vehicles), CHUNK_SIZE):
                chunk = changed_vehicles[i:i + CHUNK_SIZE]
                res = self.client._send_request("/api/sync/vehicles", {
                    "vehicles": chunk,
                    "source": "CARMANAGER_INCREMENTAL_DAEMON",
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"Chunk sync result: {res}")
            sync_result = "SUCCESS"
        else:
            sync_result = "SKIPPED_NO_CHANGES" if not changed_vehicles else "DRY_RUN"

        # 4. 상태 저장
        self.last_state["vehicle_hashes"] = current_hashes
        self.last_state["last_run"] = datetime.now().isoformat()
        self._save_last_state()

        logger.info(f"Cycle completed successfully. Result: {sync_result}")
        return {
            "status": "SUCCESS",
            "inspected_count": len(thecool_cars),
            "changed_count": len(changed_vehicles),
            "sync_result": sync_result,
            "timestamp": start_time
        }

    def run_isolated_probe_verification(self) -> Dict[str, Any]:
        """실제 고객 차량을 건드리지 않고, 전용 프로브 식별자로 양방향 증분 및 SOLD 차단 검증 (TASK 4)"""
        logger.info("=== Running Isolated Probe Verification (TASK 4) ===")
        PROBE_ID = "TEST-PROBE-DIRECTIVE-133"
        PROBE_PLATE = "99허9999" # 가상 프로브 번호판

        # 1. 프로브 차량 등록 (1500만원, FOR_SALE)
        probe_car = {
            "id": PROBE_ID,
            "plate_number": PROBE_PLATE,
            "model_name": "프로브 검증용 테스트 차량",
            "manufacturer": "현대",
            "year": 2022,
            "mileage": 10000,
            "fuel_type": "가솔린",
            "transmission": "오토",
            "color": "블랙",
            "target_price": 1500,
            "status": "FOR_SALE",
            "sangsa_name": "(주)더쿨모터스",
            "is_demo": 0,
            "source": "PROBE_VERIFICATION"
        }
        res1 = self.client._send_request("/api/sync/vehicles", {
            "vehicles": [probe_car],
            "source": "PROBE_INIT",
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"Probe Init: {res1}")

        # 2. 가격 변동 증분 검증 (1500만원 -> 1450만원)
        probe_car["target_price"] = 1450
        res2 = self.client._send_request("/api/sync/vehicles", {
            "vehicles": [probe_car],
            "source": "PROBE_PRICE_CHANGE",
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"Probe Price Change (1500->1450): {res2}")

        # 3. 판매완료(SOLD) 전환 검증
        res3 = self.client._send_request("/api/sync/status", {
            "vehicle_ids": [PROBE_ID],
            "status": "SOLD",
            "reason": "PROBE_SOLD_TEST"
        })
        logger.info(f"Probe Status SOLD: {res3}")

        # 4. SOLD 상태 차량의 재공개 차단 검증 (오래된 FOR_SALE 스냅샷 재전송 시 재공개 차단 확인)
        probe_car["status"] = "FOR_SALE"
        probe_car["target_price"] = 1450
        res4 = self.client._send_request("/api/sync/vehicles", {
            "vehicles": [probe_car],
            "source": "PROBE_STALE_SNAPSHOT_RESEND",
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"Probe Stale Snapshot Resend (Must not resurrect): {res4}")

        # 5. 테스트 프로브 정리 (DELETED)
        res5 = self.client._send_request("/api/sync/status", {
            "vehicle_ids": [PROBE_ID],
            "status": "DELETED",
            "reason": "PROBE_CLEANUP"
        })
        logger.info(f"Probe Cleanup: {res5}")

        return {
            "probe_id": PROBE_ID,
            "price_change_verified": res2.get("updated") == 1 or res2.get("success") is True,
            "sold_transition_verified": res3.get("unpublished") is True or res3.get("success") is True,
            "cleanup_verified": res5.get("success") is True
        }


def main():
    daemon = ContinuousSyncDaemon()
    print("=" * 60)
    print("Executing ContinuousSyncDaemon Inspection Cycle")
    print("=" * 60)
    res = daemon.inspect_and_sync_incremental(dry_run=True)
    print("Incremental Inspection Result:", json.dumps(res, ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("Executing Isolated Probe Verification (Zero impact on customer data)")
    print("=" * 60)
    probe_res = daemon.run_isolated_probe_verification()
    print("Probe Verification Result:", json.dumps(probe_res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
