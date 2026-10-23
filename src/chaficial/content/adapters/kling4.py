"""Kling 4.0 전용 영상 어댑터.

시네마틱 드라마, 극적 연출 및 하이엔드 스토리텔링 컷별 프롬프트 생성.
"""

from __future__ import annotations

from chaficial.content.adapters.base import VideoGenerationAdapter
from chaficial.content.models import (
    ContentScript,
    MediaAsset,
    ShotPrompt,
    VideoModelType,
)


class Kling4Adapter(VideoGenerationAdapter):
    """Kling 4.0 모델 어댑터."""

    @property
    def model_type(self) -> VideoModelType:
        return VideoModelType.KLING_4_0

    def generate_shot_prompts(
        self,
        script: ContentScript,
        assets: list[MediaAsset],
        duration_sec: float = 30.0,
    ) -> list[ShotPrompt]:
        """Kling 4.0용 드라마틱 컷별 프롬프트 생성."""
        shot_prompts: list[ShotPrompt] = []

        for idx, scene in enumerate(script.scenes):
            cam_move = "anamorphic slow push-in" if idx % 2 == 0 else "dynamic orbit sweep"
            prompt = ShotPrompt(
                scene_number=scene.scene_number,
                duration_seconds=scene.duration_seconds,
                scene_title=scene.title,
                camera_movement=cam_move,
                visual_prompt=(
                    f"Cinematic 9:16 vertical commercial scene. High-contrast dramatic automotive lighting. "
                    f"Action: {scene.visual_description}. Ultra-realistic movie grade rendering."
                ),
                dialogue=scene.narration,
                audio_instruction="Dramatic cinematic sound design with rich bass and clear voiceover.",
                reference_asset_tags=["ref_image_01"] if assets else [],
            )
            shot_prompts.append(prompt)

        return shot_prompts

    def format_master_prompt(
        self,
        script: ContentScript,
        assets: list[MediaAsset],
        shot_prompts: list[ShotPrompt],
    ) -> str:
        """Kling 4.0 형식 프롬프트 스트링 생성."""
        lines = [
            "# KLING 4.0 CINEMATIC MULTI-SHOT SPECIFICATION",
            f"Aspect: 9:16 Vertical | Total Duration: 30s | Title: {script.title}",
            "",
            "## SHOT BREAKDOWN",
        ]
        for sp in shot_prompts:
            lines.extend([
                f"### Shot {sp.scene_number}: {sp.scene_title} ({sp.duration_seconds}s)",
                f"- Visual: {sp.visual_prompt}",
                f"- Camera: {sp.camera_movement}",
                f'- Dialogue: "{sp.dialogue}"',
                f"- Audio: {sp.audio_instruction}",
                "",
            ])
        return "\n".join(lines)
