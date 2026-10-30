"""
Chaficial Photo Ingestion & Preservation Pipeline (DIRECTIVE 104)
- Principle: ZERO artificial modification. All CarManager high-res photos preserved 100% as pristine originals.
- Status machine: PHOTO_MISSING -> HARVESTED_ORIGINAL -> VERIFIED -> READY_FOR_PUBLISH
- Rule: Local M4 rembg background removal completely DECOMMISSIONED by user & technical director mandate.
- Strict Verification: PIL Image decode verify + Resolution check + Dual SHA256 hash check.
"""

import os
import io
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
    CORRUPTED = "CORRUPTED"
    FAILED = "FAILED"

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

    def verify_and_preserve(self, raw_bytes: bytes, file_hash: str, ext: str = ".jpg") -> Tuple[bool, str, int, int]:
        """
        TASK 2 무결성 정밀 검증:
        1. PIL 디코딩 및 손상 여부 검사
        2. 해상도 (width, height) 추출
        3. 복사 및 디스크 저장 후 SHA256 재계산 일치 검증
        """
        try:
            with Image.open(io.BytesIO(raw_bytes)) as img:
                img.verify()
            
            # verify() 후 실제 로드하여 크기 및 포맷 확인
            with Image.open(io.BytesIO(raw_bytes)) as img:
                width, height = img.size
                img_format = (img.format or "JPEG").lower()
                if img_format == "jpeg":
                    ext = ".jpg"
                else:
                    ext = f".{img_format}"
                
            out_filename = f"{file_hash}{ext}"
            out_path = os.path.join(self.processed_dir, out_filename)

            # 이미 존재하면 캐시 파일의 SHA256 해시 검증
            if os.path.exists(out_path):
                with open(out_path, "rb") as f:
                    cached_bytes = f.read()
                if self.compute_sha256(cached_bytes) == file_hash:
                    return True, out_path, width, height
                else:
                    # 캐시 손상 시 재작성
                    pass

            # 디스크 저장
            with open(out_path, "wb") as f:
                f.write(raw_bytes)

            # 복사 후 디스크 파일 SHA256 재계산 및 100% 일치 검증
            with open(out_path, "rb") as f:
                disk_bytes = f.read()
            disk_hash = self.compute_sha256(disk_bytes)
            
            if disk_hash != file_hash:
                return False, "", 0, 0

            return True, out_path, width, height

        except Exception as e:
            return False, str(e), 0, 0

    def process_photo(self, image_path: str, sort_order: int = 1, label: str = "") -> Dict:
        """
        단일 사진 파이프라인 처리 (DIRECTIVE 104 원본 보존 및 완전 무결성 검증)
        - rembg 로컬 배경 합성 전면 폐기
        - PIL 디코딩 및 규격/해상도 검사
        - 이중 SHA256 해시 검증
        """
        if not os.path.exists(image_path):
            return {
                "error": "File not found",
                "status": PhotoStatus.FAILED.value,
                "bg_applied": False
            }

        with open(image_path, "rb") as f:
            raw_bytes = f.read()

        file_hash = self.compute_sha256(raw_bytes)
        category = self.classify_category(sort_order, label)

        valid, out_path_or_err, width, height = self.verify_and_preserve(raw_bytes, file_hash)

        if not valid:
            return {
                "hash": file_hash,
                "error": out_path_or_err,
                "status": PhotoStatus.CORRUPTED.value,
                "bg_applied": False
            }

        return {
            "hash": file_hash,
            "category": category.value,
            "processed_path": out_path_or_err,
            "width": width,
            "height": height,
            "bg_applied": False,  # 로컬 배경 합성 영구 비활성화
            "status": PhotoStatus.VERIFIED.value
        }
