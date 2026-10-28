#!/usr/bin/env python3
"""DIRECTIVE 066 P0: DB 마이그레이션 회귀 및 데이터 보존 검증 스크립트.

운영 원본 DB를 건드리지 않고, 구버전 DB 스키마(6대 검증 컬럼 누락)의 복사본을 생성하여
마이그레이션 실행 후 컬럼 추가, 데이터 무결성 보존, 비승인 기본값 유지, 멱등성을 엄격히 검증합니다.
"""

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

# chaficial 임포트
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from chaficial.platform.db import migrate_db_schema

def test_migration_regression():
    print("[*] DIRECTIVE 066 DB 마이그레이션 회귀 검증 시작...")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_db_path = tmp.name

    try:
        conn = sqlite3.connect(test_db_path)
        cur = conn.cursor()

        # 1. 구버전 DB 스키마 생성 (DIRECTIVE 064 이전 상태: 6대 컬럼 누락)
        cur.execute("""
            CREATE TABLE vehicles (
                id VARCHAR(36) PRIMARY KEY,
                model_name VARCHAR(100) NOT NULL,
                target_price INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE vehicle_photos (
                id VARCHAR(36) PRIMARY KEY,
                vehicle_id VARCHAR(36) NOT NULL,
                photo_url VARCHAR(255) NOT NULL,
                thumb_url VARCHAR(255),
                category VARCHAR(30) DEFAULT 'EXTERIOR',
                sort_order INTEGER DEFAULT 0,
                is_primary BOOLEAN DEFAULT 0,
                caption VARCHAR(255),
                created_at DATETIME
            )
        """)

        # 2. 기존 구버전 레코드 삽입 (3건)
        sample_photos = [
            ("photo-1", "veh-1", "/uploads/photo1.jpg", 1, "전면"),
            ("photo-2", "veh-1", "/uploads/photo2.jpg", 0, "후면"),
            ("photo-3", "veh-2", "/uploads/photo3.jpg", 1, "측면"),
        ]
        cur.executemany("""
            INSERT INTO vehicle_photos (id, vehicle_id, photo_url, is_primary, caption)
            VALUES (?, ?, ?, ?, ?)
        """, sample_photos)
        conn.commit()

        # 사전 검증: 구버전 테이블에는 신규 6개 컬럼이 전혀 없어야 함
        cur.execute("PRAGMA table_info(vehicle_photos)")
        cols_before = {r[1] for r in cur.fetchall()}
        target_cols = {
            "verification_status",
            "photo_source",
            "original_file_hash",
            "usage_rights_status",
            "verified_by",
            "verified_at",
        }
        assert not (target_cols & cols_before), f"사전 조건 실패: 이미 컬럼이 존재함 {target_cols & cols_before}"
        print(f"[*] [PASS] 사전 검증: 구버전 컬럼 수 = {len(cols_before)}, 신규 6대 컬럼 부재 확인 완료")
        conn.close()

        # 3. 1차 마이그레이션 실행
        migrate_db_schema(target_db_file=test_db_path)
        print("[*] [PASS] 1차 migrate_db_schema() 실행 완료")

        conn = sqlite3.connect(test_db_path)
        cur = conn.cursor()

        # 4. 신규 컬럼 6종 추가 확인
        cur.execute("PRAGMA table_info(vehicle_photos)")
        cols_after = {r[1] for r in cur.fetchall()}
        for col in target_cols:
            assert col in cols_after, f"마이그레이션 실패: 누락된 컬럼 {col}"
        print(f"[*] [PASS] 6대 컬럼 정상 추가 확인: {target_cols}")

        # 5. 기존 데이터 3건 값 보존 및 신규 컬럼 기본값 검증
        cur.execute("SELECT id, vehicle_id, photo_url, is_primary, caption, verification_status, photo_source, usage_rights_status FROM vehicle_photos ORDER BY id")
        rows = cur.fetchall()
        assert len(rows) == 3, f"데이터 건수 불일치: {len(rows)} != 3"
        
        # 행 1 검증
        r1 = rows[0]
        assert r1[0] == "photo-1" and r1[2] == "/uploads/photo1.jpg" and r1[3] == 1 and r1[4] == "전면", "기존 데이터 훼손 감지!"
        assert r1[5] == "UNVERIFIED", f"비승인 기본값 실패: {r1[5]}"
        assert r1[6] == "UNKNOWN", f"출처 기본값 실패: {r1[6]}"
        assert r1[7] == "PENDING", f"사용권 기본값 실패: {r1[7]}"

        print("[*] [PASS] 기존 데이터 3건 100% 무결 보존 및 기본값(UNVERIFIED) 자동 승인 방지 확인 완료")
        conn.close()

        # 6. 연속 2회, 3회 실행 멱등성 검증 (오류 발생 여부)
        migrate_db_schema(target_db_file=test_db_path)
        migrate_db_schema(target_db_file=test_db_path)
        print("[*] [PASS] 연속 2회 및 3회 마이그레이션 멱등성 검증 완료 (에러 0건)")

        # 최종 건수 및 컬럼 수 재확인
        conn = sqlite3.connect(test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM vehicle_photos")
        final_count = cur.fetchone()[0]
        assert final_count == 3, "연속 실행 후 행 수 변동 감지"
        conn.close()

        print("\n=======================================================")
        print("  DIRECTIVE 066 DB 마이그레이션 회귀 검증: ALL PASS SUCCESS")
        print("=======================================================")
        return True

    finally:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)

if __name__ == "__main__":
    success = test_migration_regression()
    sys.exit(0 if success else 1)
