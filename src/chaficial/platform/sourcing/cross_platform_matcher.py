"""
Cross-Platform Vehicle Matcher (CHA-FICIAL DIRECTIVE 118 Standards)
- Standard Interfaces:
  * fetch_kb_candidate(): Connects to authorized KB API / scrape adapter (raises NotImplementedError if unauthorized)
  * fetch_encar_candidate(): Connects to authorized Encar API / scrape adapter (raises NotImplementedError if unauthorized)
  * validate_candidate(): Pure multi-attribute deterministic scoring
  * record_verified_match(): Saves only VERIFIED as ACTIVE, CANDIDATE as REVIEW_PENDING
- Explicit Observation Mode: OFFLINE_TEST, MANUAL_VERIFIED, LIVE_OBSERVED.
"""

import re
import os
import time
import json
import uuid
import sqlite3
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

class ObservationMode(str, Enum):
    OFFLINE_TEST = "OFFLINE_TEST"           # Hardcoded sample data for calculation testing
    MANUAL_VERIFIED = "MANUAL_VERIFIED"     # Verified manually via web UI with evidence URLs
    LIVE_OBSERVED = "LIVE_OBSERVED"         # Automated live network query via authorized adapter

class MatchingStatus(str, Enum):
    VERIFIED = "VERIFIED"       # High confidence match (Exact full plate + multi-spec match, score >= 0.85) -> ACTIVE
    CANDIDATE = "CANDIDATE"     # Moderate match requiring manual review (0.60 <= score < 0.85) -> REVIEW_PENDING
    REJECTED = "REJECTED"       # Low score / spec conflict (score < 0.60)
    NOT_FOUND = "NOT_FOUND"     # No matching car on external platform

@dataclass
class MatchResult:
    vehicle_id: str
    plate_number: Optional[str]
    source_platform: str  # KB_CHACHACHA, ENCAR
    external_car_id: Optional[str]
    external_url: Optional[str]
    advertised_price_manwon: Optional[int]
    photo_urls: List[str]
    status: MatchingStatus
    match_score: float
    match_evidence: Dict[str, Any]
    observation_mode: ObservationMode
    matched_at: str

ALLOWED_HOSTS = {
    "kbchachacha.com", "www.kbchachacha.com",
    "encar.com", "www.encar.com",
    "carmanager.co.kr", "www.carmanager.co.kr"
}

class CrossPlatformMatcher:
    def __init__(self, db_path: str = "data/chamart/chamart_platform_demo.db", is_production: Optional[bool] = None):
        self.db_path = db_path
        # 운영 저장소 물리적 판별: 절대 경로 및 파일 기반 불변 판별 (환경변수 조작 우회 차단)
        real_abs = os.path.realpath(self.db_path)
        is_real_prod_file = "chamart_platform_demo.db" in real_abs and "sandbox" not in real_abs and "test" not in real_abs
        
        if is_real_prod_file:
            self.is_production = True
        elif is_production is not None:
            self.is_production = is_production
        else:
            env_val = os.getenv("CHAFICIAL_ENV", "").lower()
            self.is_production = (env_val in ("production", "prod"))

    def fetch_kb_candidate(self, plate_number: str) -> Optional[Dict[str, Any]]:
        """
        Connects to authorized KB ChaChaCha interface.
        Throws NotImplementedError until formal scraping / API integration is authorized.
        """
        raise NotImplementedError("Live automated KB ChaChaCha query is not authorized. Use manual verification workflow.")

    def fetch_encar_candidate(self, plate_number: str) -> Optional[Dict[str, Any]]:
        """
        Connects to authorized Encar interface.
        Throws NotImplementedError until formal scraping / API integration is authorized.
        """
        raise NotImplementedError("Live automated Encar query is not authorized. Use manual verification workflow.")

    def validate_candidate(self, source_car: Dict[str, Any], candidate_car: Dict[str, Any]) -> Tuple[float, Dict[str, Any], MatchingStatus]:
        """
        Pure deterministic multi-attribute scoring.
        """
        score = 0.0
        evidence = {}

        # 1. Plate match
        s_plate = (source_car.get("plate_number") or "").replace(" ", "")
        c_plate = (candidate_car.get("plate_number") or "").replace(" ", "")

        if s_plate and c_plate and len(s_plate) > 4 and len(c_plate) > 4:
            if s_plate == c_plate:
                score += 0.50
                evidence["plate_match"] = "EXACT_FULL"
            else:
                evidence["plate_match"] = "FULL_MISMATCH"
                return 0.0, {"reason": "FULL_PLATE_MISMATCH", "s_plate": s_plate, "c_plate": c_plate}, MatchingStatus.REJECTED
        elif s_plate and c_plate and s_plate[-4:] == c_plate[-4:]:
            score += 0.20
            evidence["plate_match"] = "TAIL_4DIGIT_ONLY"
        else:
            evidence["plate_match"] = "NONE"

        # 2. Model match
        s_raw = (source_car.get("model_name") or "").lower()
        c_raw = (candidate_car.get("model_name") or "").lower()
        s_model = s_raw.replace(" ", "")
        c_model = c_raw.replace(" ", "")
        if s_model and c_model:
            if s_model in c_model or c_model in s_model:
                score += 0.25
                evidence["model_match"] = "HIGH_SUBSTRING"
            else:
                s_tokens = set(re.findall(r'[a-zA-Z0-9가-힣]+', s_raw))
                c_tokens = set(re.findall(r'[a-zA-Z0-9가-힣]+', c_raw))
                if s_tokens and c_tokens:
                    jaccard = len(s_tokens & c_tokens) / len(s_tokens | c_tokens)
                    score += 0.25 * jaccard
                    evidence["model_match"] = f"JACCARD_{jaccard:.2f}"

        # 3. Year match
        s_year = source_car.get("year")
        c_year = candidate_car.get("year")
        if s_year and c_year:
            try:
                diff = abs(int(str(s_year)[:4]) - int(str(c_year)[:4]))
                if diff == 0:
                    score += 0.10
                    evidence["year_match"] = "EXACT"
                elif diff <= 1:
                    score += 0.05
                    evidence["year_match"] = "WITHIN_1YR"
                else:
                    evidence["year_match"] = f"DIFF_{diff}YR"
            except Exception:
                pass

        # 4. Fuel match
        s_fuel = (source_car.get("fuel_type") or "").strip()
        c_fuel = (candidate_car.get("fuel_type") or "").strip()
        if s_fuel and c_fuel and (s_fuel in c_fuel or c_fuel in s_fuel):
            score += 0.05
            evidence["fuel_match"] = "MATCH"

        # 5. Color match
        s_color = (source_car.get("color") or "").strip()
        c_color = (candidate_car.get("color") or "").strip()
        if s_color and c_color and (s_color[:2] in c_color or c_color[:2] in s_color):
            score += 0.05
            evidence["color_match"] = "MATCH"

        # 6. Mileage match
        s_km = source_car.get("mileage")
        c_km = candidate_car.get("mileage")
        if s_km is not None and c_km is not None:
            try:
                s_km_val = float(s_km)
                c_km_val = float(c_km)
                if s_km_val > 0:
                    km_diff_pct = abs(s_km_val - c_km_val) / s_km_val
                    if km_diff_pct <= 0.15:
                        score += 0.05
                        evidence["mileage_match"] = f"TOLERANCE_{km_diff_pct*100:.1f}%"
            except Exception:
                pass

        final_score = min(1.0, round(score, 3))
        
        # Classification
        if evidence.get("plate_match") == "EXACT_FULL" and final_score >= 0.85:
            status = MatchingStatus.VERIFIED
        elif final_score >= 0.60:
            status = MatchingStatus.CANDIDATE
        elif final_score > 0.0:
            status = MatchingStatus.REJECTED
        else:
            status = MatchingStatus.NOT_FOUND

        return final_score, evidence, status

    def record_verified_match(self, match: MatchResult) -> None:
        """
        Saves match:
          - OFFLINE_TEST -> Strictly blocked on operational DB (Only allowed on sandbox DBs as TEST_MOCK).
          - MANUAL_VERIFIED -> Requires real URL, car_id, and verified_by evidence.
          - VERIFIED -> listing_status = 'ACTIVE'
          - CANDIDATE -> listing_status = 'REVIEW_PENDING' (isolated from active analytics)
        """
        if not match.external_url or match.status in (MatchingStatus.REJECTED, MatchingStatus.NOT_FOUND):
            return

        # 1. P0 가드: 운영 환경에서는 OFFLINE_TEST 데이터 쓰기 100% 원천 차단
        if match.observation_mode == ObservationMode.OFFLINE_TEST and self.is_production:
            return  # Operational storage protected: No writes permitted for mock/test data!

        # 2. MANUAL_VERIFIED 도메인 화이트리스트 및 증거 엄격성 검증 (TASK 2)
        if match.observation_mode == ObservationMode.MANUAL_VERIFIED:
            ev = match.match_evidence or {}
            
            # 2-1. 표준 URL 파서(urllib.parse) 기반 호스트네임 검증
            parsed_url = urllib.parse.urlparse(match.external_url)
            host = (parsed_url.hostname or "").lower()
            if host not in ALLOWED_HOSTS:
                raise ValueError(f"MANUAL_VERIFIED external_url hostname ('{host}') is not in authorized whitelist ({', '.join(sorted(ALLOWED_HOSTS))}).")

            # 2-2. URL과 external_car_id 대응 검증
            if not match.external_car_id or match.external_car_id not in match.external_url:
                raise ValueError("MANUAL_VERIFIED external_car_id must exist and be present in external_url path.")

            # 2-3. 서버 검증된 관리자 승인 기록(admin_approval 딕셔너리) 검증
            admin_approval = ev.get("admin_approval")
            if not isinstance(admin_approval, dict) or not admin_approval.get("admin_id") or not admin_approval.get("approved_at"):
                raise ValueError("MANUAL_VERIFIED requires valid admin_approval dict with 'admin_id' and 'approved_at'.")

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")

        ext_listing_id = match.external_car_id or f"{match.source_platform}_{match.vehicle_id}"
        
        if match.observation_mode == ObservationMode.OFFLINE_TEST:
            db_listing_status = "TEST_MOCK"
            is_demo_val = 1
        elif match.status == MatchingStatus.VERIFIED:
            db_listing_status = "ACTIVE"
            is_demo_val = 0
        else:
            db_listing_status = "REVIEW_PENDING"
            is_demo_val = 0

        c.execute("""
            SELECT id, listing_status FROM vehicle_listings 
            WHERE vehicle_id = ? AND platform = ?
        """, (match.vehicle_id, match.source_platform))
        existing = c.fetchone()

        # 기존 활성 매물이 존재할 때 OFFLINE_TEST로 덮어쓰기 차단
        if existing and match.observation_mode == ObservationMode.OFFLINE_TEST and existing[1] == "ACTIVE":
            conn.close()
            return

        notes = f"Mode: {match.observation_mode.value}, Status: {match.status.value}, Evidence: {json.dumps(match.match_evidence, ensure_ascii=False)}"

        if existing:
            c.execute("""
                UPDATE vehicle_listings SET
                    listing_id = ?,
                    listing_url = ?,
                    advertised_price = ?,
                    listing_status = ?,
                    last_observed_at = ?,
                    data_confidence = ?,
                    observation_notes = ?,
                    is_demo = ?
                WHERE id = ?
            """, (
                ext_listing_id,
                match.external_url,
                match.advertised_price_manwon,
                db_listing_status,
                now_iso,
                match.match_score,
                notes,
                is_demo_val,
                existing[0]
            ))
        else:
            new_id = str(uuid.uuid4())
            c.execute("""
                INSERT INTO vehicle_listings (
                    id, vehicle_id, platform, listing_id, listing_url, 
                    advertised_price, listing_status, first_observed_at, 
                    last_observed_at, data_confidence, observation_notes,
                    is_demo, source_confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_id,
                match.vehicle_id,
                match.source_platform,
                ext_listing_id,
                match.external_url,
                match.advertised_price_manwon,
                db_listing_status,
                now_iso,
                now_iso,
                match.match_score,
                notes,
                is_demo_val,
                match.match_score
            ))

        conn.commit()
        conn.close()
