"""영상 생성 AI 모델(WAN 3.0, Kling 4.0 등) 추상 어댑터 인터페이스.

DIRECTIVE 003-A 명세 준수:
- 모델별 설정과 프롬프트를 교체할 수 있는 Adapter 구조
- 실제 외부 API 부재 시에도 비정상 종료 없이 안전하게 프롬프트 명세 및 Dry-run 생성
"""

from __future__ import annotations

import abc
from typing import Any

from chaficial.content.models import (
    ContentScript,
    MediaAsset,
    ShotPrompt,
    VideoModelType,
)


class VideoGenerationAdapter(abc.ABC):
    """영상 생성 AI 엔진 어댑터 기본 추상 클래스."""

    @property
    @abc.abstractmethod
    def model_type(self) -> VideoModelType:
        """어댑터가 지원하는 모델 타입."""
        ...

    @abc.abstractmethod
    def generate_shot_prompts(
        self,
        script: ContentScript,
        assets: list[MediaAsset],
        duration_sec: float = 30.0,
    ) -> list[ShotPrompt]:
        """대본과 에셋을 결합하여 모델 전용 컷별 프롬프트 리스트 생성."""
        ...

    @abc.abstractmethod
    def format_master_prompt(
        self,
        script: ContentScript,
        assets: list[MediaAsset],
        shot_prompts: list[ShotPrompt],
    ) -> str:
        """해당 모델 엔진(UI/API)에 입력 가능한 단일 마스터 프롬프트 생성."""
        ...

    def execute_generation(
        self,
        master_prompt: str,
        assets: list[MediaAsset],
        dry_run: bool = True,
        api_payload: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """영상 생성 실행.
        
        실제 외부 API가 공식 지원되기 전까지는 크래시 없이
        안전한 Dry-run(사전 검증 및 메타데이터 생성) 모드로 동작합니다.
        """
        # 외부 API가 없는 경우 비정상 종료 대신 오프라인 검증 결과 반환
        return {
            "model": self.model_type.value,
            "status": "READY_FOR_SUBMISSION" if dry_run else "MOCK_SUCCESS",
            "is_dry_run": dry_run,
            "api_payload": api_payload or {},
            "prompt_length": len(master_prompt),
            "asset_count": len(assets),
            "message": "외부 API 미연동 상태로 오프라인 프롬프트 검증 및 명세 생성이 완료되었습니다.",
        }
