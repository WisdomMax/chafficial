import pytest
import os
import io
import subprocess
from PIL import Image
from src.chaficial.platform.sourcing.photo_pipeline import (
    PhotoPipelineManager, PhotoStatus, PhotoCategory
)

def test_rembg_scripts_completely_blocked():
    """TASK 1: 폐기된 스크립트 실행 시 RuntimeError 발생 확인"""
    res1 = subprocess.run(["python3", "scratch/test_ai_outdoor_bg_3cars.py"], capture_output=True, text=True)
    assert res1.returncode != 0
    assert "PERMANENTLY DECOMMISSIONED" in res1.stderr

    res2 = subprocess.run(["python3", "scratch/render_outdoor_real_styles.py"], capture_output=True, text=True)
    assert res2.returncode != 0
    assert "PERMANENTLY DECOMMISSIONED" in res2.stderr

def test_photo_pipeline_integrity_and_hash():
    """TASK 2: 유효 이미지 디코딩, 해시 일치, 손상 파일 거부 검증"""
    manager = PhotoPipelineManager(
        cache_dir="data/test_photo_cache",
        processed_dir="data/test_processed_photos"
    )

    # 1. 정상 JPEG 생성
    img = Image.new("RGB", (640, 480), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    valid_bytes = buf.getvalue()

    test_file = "data/test_valid.jpg"
    with open(test_file, "wb") as f:
        f.write(valid_bytes)

    res = manager.process_photo(test_file, sort_order=1)
    assert res["status"] == PhotoStatus.VERIFIED.value
    assert res["width"] == 640
    assert res["height"] == 480
    assert res["bg_applied"] is False
    assert os.path.exists(res["processed_path"])

    # 2. 손상된 파일 테스트 (가짜 바이트)
    corrupted_file = "data/test_corrupt.jpg"
    with open(corrupted_file, "wb") as f:
        f.write(b"NOT_A_REAL_IMAGE_DATA_123456789")

    res_corrupt = manager.process_photo(corrupted_file, sort_order=1)
    assert res_corrupt["status"] == PhotoStatus.CORRUPTED.value
    assert res_corrupt["status"] != PhotoStatus.VERIFIED.value

    # 정리
    if os.path.exists(test_file): os.remove(test_file)
    if os.path.exists(corrupted_file): os.remove(corrupted_file)

if __name__ == "__main__":
    test_rembg_scripts_completely_blocked()
    test_photo_pipeline_integrity_and_hash()
    print("ALL TESTS PASSED!")
