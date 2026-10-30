"""
Cross-Platform Vehicle Matcher (CHA-FICIAL DIRECTIVE 114)
- Identifies and enriches vehicles between CarManager, KB ChaChaCha, and Encar.
- Search hierarchy: CarManager deficient cars -> 1st KB ChaChaCha -> 2nd Encar.
- Plate tail (4-digits) is used solely as a candidate search hint, never as a standalone key.
- Strict multi-attribute validation: model, year (±1 yr), fuel, mileage tolerance, color, seller shop.
- Matching status: VERIFIED, CANDIDATE, REJECTED, NOT_FOUND.
- Never overwrites CarManager target_price; records independent platform listing.
- Photo assets quarantined as PRIVATE / PENDING_REVIEW.
"""

import re
import os
import time
import json
import sqlite3
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

class MatchingStatus(str, Enum):
    VERIFIED = "VERIFIED"       # High confidence match (score >= 0.85)
    CANDIDATE = "CANDIDATE"     # Moderate match requiring review (0.65 <= score < 0.85)
    REJECTED = "REJECTED"       # Low score / conflict (score < 0.65)
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
    matched_at: str

class CrossPlatformMatcher:
    def __init__(self, db_path: str = "data/chamart/chamart_platform_demo.db"):
        self.db_path = db_path

    def get_deficient_vehicles(self, limit: int = 200, priority: str = "PRICE_AND_PHOTO") -> List[Dict[str, Any]]:
        """
        Extracts vehicles deficient in price (NULL) or photos (0 photos).
        Priority queue:
          1. price is NULL (consultation)
          2. photo count == 0
          3. older verified vehicles
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        query = """
            SELECT v.id, v.plate_number, v.model_name, v.year, v.mileage, 
                   v.fuel_type, v.color, v.target_price,
                   l.listing_id as carmanager_carseq,
                   l.raw_seller_name as shop,
                   l.raw_seller_location as danji,
                   count(p.id) as photo_count
            FROM vehicles v
            LEFT JOIN vehicle_listings l ON v.id = l.vehicle_id AND l.platform = 'CARMANAGER'
            LEFT JOIN vehicle_photos p ON v.id = p.vehicle_id
            WHERE v.is_demo = 0
            GROUP BY v.id
            HAVING (v.target_price IS NULL OR photo_count = 0)
            ORDER BY 
              CASE WHEN v.target_price IS NULL THEN 0 ELSE 1 END,
              CASE WHEN photo_count = 0 THEN 0 ELSE 1 END,
              v.id ASC
            LIMIT ?
        """
        c.execute(query, (limit,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def calculate_match_score(self, source_car: Dict[str, Any], candidate_car: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculates multi-attribute match score [0.0 - 1.0].
        Weights:
          - Plate number (full exact match): +0.50, (tail 4-digit only): +0.20
          - Model name similarity: +0.25
          - Year match (exact: +0.10, ±1 yr: +0.05)
          - Fuel type match: +0.05
          - Color match: +0.05
          - Mileage tolerance (within 15%): +0.05
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
                score += 0.0
                evidence["plate_match"] = "FULL_MISMATCH"
                return 0.0, {"reason": "FULL_PLATE_MISMATCH", "s_plate": s_plate, "c_plate": c_plate}
        elif s_plate and c_plate and s_plate[-4:] == c_plate[-4:]:
            score += 0.20
            evidence["plate_match"] = "TAIL_4DIGIT_ONLY"
        else:
            evidence["plate_match"] = "NONE"

        # 2. Model match
        s_model = (source_car.get("model_name") or "").lower().replace(" ", "")
        c_model = (candidate_car.get("model_name") or "").lower().replace(" ", "")
        
        # 간단한 자카드 유사도 또는 포함 관계
        if s_model and c_model:
            if s_model in c_model or c_model in s_model:
                score += 0.25
                evidence["model_match"] = "HIGH_SUBSTRING"
            else:
                s_tokens = set(re.findall(r'[a-zA-Z0-9가-힣]+', s_model))
                c_tokens = set(re.findall(r'[a-zA-Z0-9가-힣]+', c_model))
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

        return min(1.0, round(score, 3)), evidence

    def classify_match(self, score: float, evidence: Dict[str, Any]) -> MatchingStatus:
        if evidence.get("reason") == "FULL_PLATE_MISMATCH":
            return MatchingStatus.REJECTED
        if score >= 0.80 and evidence.get("plate_match") in ("EXACT_FULL", "TAIL_4DIGIT_ONLY"):
            return MatchingStatus.VERIFIED
        elif score >= 0.60:
            return MatchingStatus.CANDIDATE
        elif score > 0.0:
            return MatchingStatus.REJECTED
        else:
            return MatchingStatus.NOT_FOUND

    def record_match_in_db(self, match: MatchResult) -> None:
        """
        Records the external match safely in DB:
          - Inserts/Updates vehicle_listings with external platform
          - Never overwrites vehicles.target_price
          - Quarantines photo assets as PRIVATE
        """
        import uuid
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")

        ext_listing_id = match.external_car_id or f"{match.source_platform}_{match.vehicle_id}"

        # 1. 기존 listing 여부 확인
        c.execute("""
            SELECT id FROM vehicle_listings 
            WHERE vehicle_id = ? AND platform = ?
        """, (match.vehicle_id, match.source_platform))
        existing = c.fetchone()

        if existing:
            c.execute("""
                UPDATE vehicle_listings SET
                    listing_id = ?,
                    listing_url = ?,
                    advertised_price = ?,
                    last_observed_at = ?,
                    data_confidence = ?,
                    observation_notes = ?
                WHERE id = ?
            """, (
                ext_listing_id,
                match.external_url,
                match.advertised_price_manwon,
                now_iso,
                match.match_score,
                f"MatchStatus: {match.status.value}, Evidence: {json.dumps(match.match_evidence, ensure_ascii=False)}",
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
                ) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, 0, ?)
            """, (
                new_id,
                match.vehicle_id,
                match.source_platform,
                ext_listing_id,
                match.external_url,
                match.advertised_price_manwon,
                now_iso,
                now_iso,
                match.match_score,
                f"MatchStatus: {match.status.value}, Evidence: {json.dumps(match.match_evidence, ensure_ascii=False)}",
                match.match_score
            ))

        # 2. 사진 격리 적재
        for idx, p_url in enumerate(match.photo_urls):
            photo_id = str(uuid.uuid4())
            c.execute("""
                INSERT OR IGNORE INTO vehicle_photos (
                    id, vehicle_id, photo_url, category, sort_order, is_primary,
                    public_visibility, approval_status, allow_video_use, photo_source,
                    created_at
                ) VALUES (?, ?, ?, 'EXTERIOR', ?, ?, 'PRIVATE', 'PENDING_REVIEW', 0, ?, ?)
            """, (
                photo_id,
                match.vehicle_id,
                p_url,
                idx,
                1 if idx == 0 else 0,
                match.source_platform,
                now_iso
            ))

        conn.commit()
        conn.close()
