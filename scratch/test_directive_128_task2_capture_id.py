import os
import sys
import uuid
import sqlite3
import shutil
from datetime import datetime

sys.path.insert(0, ".")
sys.path.insert(0, "src")

from chaficial.platform.sourcing.market_timeseries_engine import MarketTimeSeriesEngine

TEST_DB = "data/chamart/sandbox_directive_128_task2.db"
PROD_DB = "data/chamart/chamart_platform_demo.db"

def setup_test_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    # 실제 운영 DB 스키마 복제 (데이터는 비운 상태로 초기화)
    conn_src = sqlite3.connect(PROD_DB)
    conn_dst = sqlite3.connect(TEST_DB)
    for line in conn_src.iterdump():
        if "sqlite_sequence" in line or line.startswith("INSERT INTO"):
            continue
        try:
            conn_dst.execute(line)
        except Exception:
            pass
    conn_dst.commit()
    conn_src.close()
    conn_dst.close()

def run_tests():
    print("=" * 60)
    print("[DIRECTIVE 128 TASK 2] source_capture_id 및 메타데이터 멱등성 테스트")
    print("=" * 60)

    setup_test_db()
    engine = MarketTimeSeriesEngine(db_path=TEST_DB, dry_run=False)

    sample_snapshot = [
        {"encarno": f"TEST_CAR_{i}", "price_manwon": 1500 + i * 10, "plate": f"{i}1가1234", "model_name": f"차량{i}", "shop": "상사A"}
        for i in range(1, 21)
    ]

    # TEST 1: 동일 capture_id 재전송 3회 -> 관측 1회 (ALREADY_RECORDED_CAPTURE_ID 멱등성)
    print("\n[TEST 1] 동일 source_capture_id 재전송 3회 멱등성 검증...")
    cap_id_1 = "CAP_20261101_001"
    res1_1 = engine.record_snapshot(
        sample_snapshot,
        source_capture_id=cap_id_1,
        source_capture_at="2026-11-01T10:00:00",
        observation_scope="JANGHANPYEONG_ALL",
        observation_mode="LIVE_OBSERVED"
    )
    assert res1_1["status"] == "SUCCESS", f"First run failed: {res1_1}"
    assert res1_1["observations_count"] == 20, f"Expected 20 observations, got {res1_1['observations_count']}"

    # 2회차 재전송 (동일 capture_id)
    res1_2 = engine.record_snapshot(
        sample_snapshot,
        source_capture_id=cap_id_1,
        source_capture_at="2026-11-01T10:00:00",
        observation_scope="JANGHANPYEONG_ALL",
        observation_mode="LIVE_OBSERVED"
    )
    assert res1_2["status"] == "ALREADY_RECORDED_CAPTURE_ID", f"Expected ALREADY_RECORDED_CAPTURE_ID, got {res1_2['status']}"
    assert res1_2["observations_count"] == 0, f"Duplicate observations leaked: {res1_2['observations_count']}"

    # 3회차 재전송 (동일 capture_id)
    res1_3 = engine.record_snapshot(
        sample_snapshot,
        source_capture_id=cap_id_1,
        source_capture_at="2026-11-01T10:00:00",
        observation_scope="JANGHANPYEONG_ALL",
        observation_mode="LIVE_OBSERVED"
    )
    assert res1_3["status"] == "ALREADY_RECORDED_CAPTURE_ID", f"Expected ALREADY_RECORDED_CAPTURE_ID, got {res1_3['status']}"

    # DB에 실제 저장된 observations 확인 (정확히 20개여야 함)
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM market_listing_observations")
    obs_cnt = c.fetchone()[0]
    c.execute("SELECT count(*) FROM market_collection_runs WHERE source_capture_id = ?", (cap_id_1,))
    runs_cnt = c.fetchone()[0]
    conn.close()

    assert runs_cnt == 1, f"Expected 1 run for cap_id_1, got {runs_cnt}"
    assert obs_cnt == 20, f"Expected 20 observations total, got {obs_cnt}"
    print("[PASS] TEST 1: 동일 capture_id 3회 재전송 시 정확히 1회만 적재되고 2회 중복 차단 입증!")

    # TEST 2: 서로 다른 날짜의 실제 capture_id 2개, 내용 동일 -> 관측 2회 (Days on Market 보존)
    print("\n[TEST 2] 서로 다른 날짜의 실제 capture_id 2개 (내용 동일) 연속 관측 검증...")
    cap_id_2 = "CAP_20261102_001"
    res2 = engine.record_snapshot(
        sample_snapshot,
        source_capture_id=cap_id_2,
        source_capture_at="2026-11-02T10:00:00",
        observation_scope="JANGHANPYEONG_ALL",
        observation_mode="LIVE_OBSERVED"
    )
    assert res2["status"] == "SUCCESS", f"Second day run failed: {res2}"
    assert res2["observations_count"] == 20, f"Expected 20 observations on day 2, got {res2['observations_count']}"

    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM market_listing_observations")
    total_obs = c.fetchone()[0]
    c.execute("SELECT count(*) FROM market_collection_runs WHERE status = 'SUCCESS'")
    total_runs = c.fetchone()[0]
    conn.close()

    assert total_runs == 2, f"Expected 2 successful runs across 2 days, got {total_runs}"
    assert total_obs == 40, f"Expected 40 observations total across 2 days (20 * 2), got {total_obs}"
    print(f"[PASS] TEST 2: 내용 동일하더라도 날짜가 다른 새 capture_id는 정상 적재됨 (총 Runs={total_runs}, Observations={total_obs}, Days on Market 보존!)")

    # TEST 3: 동일 ID·가격 목록의 두 번째 관측 -> 가격변경 이벤트 0건
    print("\n[TEST 3] 내용 및 가격 동일 시 변동 이벤트 0건 검증...")
    assert res2["events_count"] == 0, f"Events leaked on unchanged snapshot: {res2['events_count']}"
    assert res2["price_decreased_count"] == 0, f"Price decrease leaked: {res2['price_decreased_count']}"
    assert res2["price_increased_count"] == 0, f"Price increase leaked: {res2['price_increased_count']}"
    assert res2["appeared_count"] == 0, f"False appeared count: {res2['appeared_count']}"
    assert res2["disappeared_count"] == 0, f"False disappeared count: {res2['disappeared_count']}"
    print("[PASS] TEST 3: 동일 ID 및 가격 목록의 2일차 관측에서 가격 변동 및 허위 이벤트 0건 완벽 입증!")

    # TEST 4: 과거 원본 시각 NULL -> 현재 관측으로 승격 0건
    print("\n[TEST 4] 과거 원본 시각 NULL -> 현재 관측으로 승격 0건 및 중복 차단 검증...")
    res4_1 = engine.record_snapshot(
        sample_snapshot,
        source_capture_id=None,
        source_capture_at=None,
        observation_scope="JANGHANPYEONG_ALL",
        observation_mode="HISTORICAL_REPLAY"
    )
    assert res4_1["status"] == "SUCCESS", f"Initial NULL capture_at replay failed: {res4_1}"

    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("SELECT source_capture_at, observation_mode FROM market_collection_runs WHERE run_id = ?", (res4_1["run_id"],))
    db_cap_at, db_obs_mode = c.fetchone()
    conn.close()

    assert db_cap_at is None, f"source_capture_at falsely promoted to current time! Got: {db_cap_at}"
    assert db_obs_mode == "HISTORICAL_REPLAY", f"Wrong observation_mode: {db_obs_mode}"

    # 동일한 NULL capture_at 과거 파일 재실행 -> 현재 시각으로 승격되지 않고 중복 차단되어야 함!
    res4_2 = engine.record_snapshot(
        sample_snapshot,
        source_capture_id=None,
        source_capture_at=None,
        observation_scope="JANGHANPYEONG_ALL",
        observation_mode="HISTORICAL_REPLAY"
    )
    assert res4_2["status"] == "ALREADY_RECORDED_HISTORICAL_HASH", f"Expected ALREADY_RECORDED_HISTORICAL_HASH, got {res4_2['status']}"
    assert res4_2["observations_count"] == 0, f"Leaked observations: {res4_2['observations_count']}"
    print("[PASS] TEST 4: 과거 원본 시각 NULL 시 source_capture_at=NULL 엄격 유지, 재실행 시 현재 관측으로 승격 0건 차단 입증!")

    # TEST 5: 부분 목록 -> DELISTED/SOLD 이벤트 0건
    print("\n[TEST 5] 부분 목록 관측 시 DELISTED/SOLD 이벤트 0건 검증...")
    partial_snapshot = sample_snapshot[:10]  # 절반만 관측됨
    cap_id_partial = "CAP_20261103_PARTIAL"
    res5 = engine.record_snapshot(
        partial_snapshot,
        source_capture_id=cap_id_partial,
        source_capture_at="2026-11-03T10:00:00",
        observation_scope="JANGHANPYEONG_PARTIAL",
        observation_mode="LIVE_OBSERVED"
    )
    assert res5["status"] == "SUCCESS", f"Partial run failed: {res5}"
    # 스코프가 다르거나 부분 관측이므로 이전 전체 스코프 대비 거짓 DELISTED가 발생하지 않아야 함
    assert res5["disappeared_count"] == 0, f"False disappeared count leaked on partial snapshot: {res5['disappeared_count']}"
    print("[PASS] TEST 5: 부분 목록 관측 시 DELISTED/SOLD 이벤트 0건 안전 검증 완료!")

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    print("\n" + "=" * 60)
    print(">>> [DIRECTIVE 128 TASK 2] 5대 필수 멱등성 및 메타데이터 테스트 전수 통과 <<<")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
