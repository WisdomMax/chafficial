"""Runway Wan 3.0 전용 영상 어댑터.

한국어 대사 중심, 9:16 세로형 30초, 인물 일관성(@Image 1), 실차 에셋(@Image 2~10),
대표님 음성 락(@Audio 1)에 최적화된 마스터 프롬프트 생성.
"""

from __future__ import annotations

from chaficial.content.adapters.base import VideoGenerationAdapter
from chaficial.content.models import (
    AssetType,
    ContentScript,
    MediaAsset,
    ShotPrompt,
    VideoModelType,
)


class Wan3Adapter(VideoGenerationAdapter):
    """Runway Wan 3.0 모델 어댑터."""

    @property
    def model_type(self) -> VideoModelType:
        return VideoModelType.WAN_3_0

    def generate_shot_prompts(
        self,
        script: ContentScript,
        assets: list[MediaAsset],
        duration_sec: float = 30.0,
    ) -> list[ShotPrompt]:
        """Wan 3.0용 컷별 프롬프트 생성."""
        shot_prompts: list[ShotPrompt] = []

        # 에셋 태그 매핑 (기본 @Image 1은 대표님)
        image_assets = [a for a in assets if a.asset_type == AssetType.IMAGE]

        for idx, scene in enumerate(script.scenes):
            ref_tags = ["@Image 1"]
            if idx + 1 < len(image_assets):
                ref_tags.append(f"@Image {idx + 2}")

            cam_move = "rapid crash-zoom into face" if idx == 0 else "smooth cinematic tracking pan"

            prompt = ShotPrompt(
                scene_number=scene.scene_number,
                duration_seconds=scene.duration_seconds,
                scene_title=scene.title,
                camera_movement=cam_move,
                visual_prompt=(
                    f"Standing confidently beside vehicle, the Korean male dealer matching @Image 1 "
                    f"delivers commercial presentation directly to phone camera in 9:16 vertical shorts aspect. "
                    f"Visual focus: {scene.visual_description}."
                ),
                dialogue=scene.narration,
                audio_instruction=(
                    "Strictly inherit Korean male voice timbre from @Audio 1. "
                    "Rapid, brisk commercial tempo with razor-sharp articulation."
                ),
                reference_asset_tags=ref_tags,
            )
            shot_prompts.append(prompt)

        return shot_prompts

    def format_master_prompt(
        self,
        script: ContentScript,
        assets: list[MediaAsset],
        shot_prompts: list[ShotPrompt],
    ) -> str:
        """Runway Wan 3.0 공식 문법 규격에 맞춘 단일 마스터 프롬프트 스트링 생성."""
        lines: list[str] = [
            "Part-1 [Duration: 30s] [Aspect Ratio: 9:16]",
            "",
            "[Tags]",
        ]

        # 태그 목록 구성
        image_assets = [a for a in assets if a.asset_type == AssetType.IMAGE]
        for idx, asset in enumerate(image_assets[:10]):
            tag = f"@Image {idx + 1}"
            lines.append(f"{tag}: {asset.label}")

        has_audio = any(a.asset_type == AssetType.AUDIO for a in assets)
        if has_audio:
            lines.append("@Audio 1: Authentic Korean male vocal timbre reference for confident, clear voice delivery.")

        lines.extend([
            "",
            "[Roles]",
            "@Image 1: Charismatic lead dealer host delivering high-energy commercial presentation directly to phone camera.",
        ])

        for idx, asset in enumerate(image_assets[1:10], start=2):
            lines.append(f"@Image {idx}: Verified vehicle visual feature for {asset.label}.")

        if has_audio:
            lines.append("@Audio 1: Authentic male voice timbre for all spoken dialogue.")

        lines.extend([
            "",
            "[Style]",
            "- Texture: 70% tactile physical 35mm film grain, 30% crisp optical definition (0% plastic CGI render).",
            "- Tone & Lighting: 70% bright neutral outdoor showroom daylight, 30% crisp natural contrast.",
            "",
            "[Scene Flow]",
        ])

        for sp in shot_prompts:
            lines.append(f"{sp.scene_number}. [{sp.scene_title}]: {sp.visual_prompt}")
            lines.append("   The dealer speaks with rapid brisk commercial confidence:")
            lines.append(f'   @Image 1 Dialogue: "{sp.dialogue}"')
            lines.append("")

        lines.extend([
            "[Audio]",
            (
                "Voice: All spoken lines strictly inherit the authentic Korean male vocal timbre of @Audio 1, "
                "delivered in a rapid, brisk, fast-paced commercial tempo with razor-sharp Korean articulation."
            ),
            "Sound effects: Natural luxury vehicle acoustics, crisp audio focus with zero distortion.",
            "",
            "[Negative]",
            (
                "subtitles, text, words, captions, typography, lettering, waxy skin, plastic CGI render, "
                "deformed hands, out of sync lips, warped rims, blurry gauges, distorted speech."
            ),
        ])

        return "\n".join(lines)
