"""
Chaficial Photo Ingestion & Preservation Pipeline (DIRECTIVE 103)
- Principle: ZERO artificial modification. All CarManager high-res photos preserved 100% as pristine originals.
- Status machine: PHOTO_MISSING -> HARVESTED_ORIGINAL -> VERIFIED -> READY_FOR_PUBLISH
- Rule: Local M4 rembg background removal completely DECOMMISSIONED by user & technical director mandate.
- Caching: SHA256 image hashing ensures idempotency, deduplication, and zero redundant storage.
"""

import os
import hashlib
import time
from typing import Dict, List, Optional, Tuple
from enum import Enum
from PIL import Image

class PhotoStatus(str, Enum):
    PHOTO_MISSING = "PHOTO_MISSING"
    HARVESTED_ORIGINAL = "HARVESTED_ORIGINAL"
    VERIFIED = "VERIFIED"
    READY_FOR_PUBLISH = "READY_FOR_PUBLISH"

class PhotoCategory(str, Enum):
    EXTERIOR_FRONT = "EXTERIOR_FRONT"
    EXTERIOR_REAR = "EXTERIOR_REAR"
    EXTERIOR_SIDE = "EXTERIOR_SIDE"
    INTERIOR_DASHBOARD = "INTERIOR_DASHBOARD"
    INTERIOR_SEATS = "INTERIOR_SEATS"
    TIRE_WHEEL = "TIRE_WHEEL"
    ENGINE_ROOM = "ENGINE_ROOM"
    DEFECT_DAMAGE = "DEFECT_DAMAGE"
    UNKNOWN = "UNKNOWN"

class PhotoPipelineManager:
    def __init__(self, cache_dir: str = "data/photo_cache", processed_dir: str = "data/processed_photos"):
        self.cache_dir = cache_dir
        self.processed_dir = processed_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)

    @staticmethod
    def compute_sha256(image_bytes: bytes) -> str:
        return hashlib.sha256(image_bytes).hexdigest()

    def classify_category(self, sort_order: int, label: str = "") -> PhotoCategory:
        """사진 순서 및 라벨 기반 외관 vs 실내/기계/하자 판별"""
        label_lower = label.lower()
        if "하자" in label_lower or "흠집" in label_lower or "손상" in label_lower:
            return PhotoCategory.DEFECT_DAMAGE
        if "실내" in label_lower or "계기판" in label_lower or "시트" in label_lower:
            return PhotoCategory.INTERIOR_DASHBOARD
        if "엔진" in label_lower:
            return PhotoCategory.ENGINE_ROOM
        if "휠" in label_lower or "타이어" in label_lower:
            return PhotoCategory.TIRE_WHEEL
        
        # 순서 기반 표준 매핑 (카매니저 표준: 1~4번 외관, 5~7번 실내, 8~9번 휠/엔진, 10번 이후 기타)
        if sort_order in [1, 2, 3, 4]:
            return PhotoCategory.EXTERIOR_FRONT
        elif sort_order in [5, 6, 7]:
            return PhotoCategory.INTERIOR_DASHBOARD
        elif sort_order in [8, 9]:
            return PhotoCategory.TIRE_WHEEL
        else:
            return PhotoCategory.UNKNOWN

    def process_photo(self, image_path: str, sort_order: int = 1, label: str = "") -> Dict:
        """
        단일 사진 파이프라인 처리 (DIRECTIVE 103 원본 보존 전용)
        - rembg 로컬 배경 합성 전면 폐기 완료 (어떠한 누끼나 인위적 배경 합성도 적용하지 않음)
        - 원본 이미지 무손실 100% 보존
        - SHA256 해시 무결성 검증 및 멱등성 캐싱
        """
        with open(image_path, "rb") as f:
            raw_bytes = f.read()

        file_hash = self.compute_sha256(raw_bytes)
        category = self.classify_category(sort_order, label)
        cached_out_name = f"{file_hash}.jpg"
        cached_out_path = os.path.join(self.processed_dir, cached_out_name)

        # 1. 캐시 적중 검사
        if os.path.exists(cached_out_path):
            return {
                "hash": file_hash,
                "category": category.value,
                "is_cached": True,
                "processed_path": cached_out_path,
                "bg_applied": False,  # 로컬 배경 합성 영구 비활성화
                "status": PhotoStatus.VERIFIED.value
            }

        # 2. 100% 원본 무손실 보존 복제
        with open(cached_out_path, "wb") as f:
            f.write(raw_bytes)

        return {
            "hash": file_hash,
            "category": category.value,
            "is_cached": False,
            "processed_path": cached_out_path,
            "bg_applied": False,  # 로컬 배경 합성 영구 비활성화
            "status": PhotoStatus.VERIFIED.value
        }
