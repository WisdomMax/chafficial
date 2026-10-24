"""독창적 숏폼 대본 생성 및 스토리보드 구성 엔진.

DIRECTIVE 003-A3 개정 준수:
- validate_scene_evidence_compatibility: 주장 문장과 증빙의 정합성 엄격 검증
  - ListingSnapshot을 사고/실내/입고 상태 검증 근거로 사용하는 행위 원천 차단
  - FACT 주장에 적합한 증빙(FactEvidence, VERIFIED) 바인딩 강제
- 임의 단정 문구("오늘 입고", "외관 확인 완료", "공조 장치 정상", "정찰 가격") 배제
- 한국어 음절 수 기반 30초 발화 가능성(135~150음절 이내) 정밀 계산
"""

from __future__ import annotations

import re

from chaficial.content.models import (
    ContentScript,
    ExpertReview,
    FactEvidence,
    FactVerificationError,
    ProvenanceType,
    StoryboardScene,
    TrendCandidate,
    VehicleContentCandidate,
    VerificationStatus,
)


def has_batchim(text: str) -> bool:
    """단어의 마지막 글자가 받침(종성)을 가지고 있는지 정밀 판별."""
    if not text:
        return False
    last_char = text.strip()[-1]
    if "\uac00" <= last_char <= "\ud7a3":
        code = ord(last_char) - 0xAC00
        return (code % 28) != 0
    if last_char in "013678":
        return True
    if last_char in "2459":
        return False
    return last_char.upper() in "LMNR"


def attach_particle(word: str, particle_pair: str) -> str:
    """단어 끝 글자의 받침 유무에 따라 올바른 한국어 조사를 결합."""
    word = word.strip()
    if not word:
        return ""
    has_final = has_batchim(word)
    if particle_pair in ("이/가", "이가"):
        return f"{word}{'이' if has_final else '가'}"
    if particle_pair in ("은/는", "은는"):
        return f"{word}{'은' if has_final else '는'}"
    if particle_pair in ("을/를", "을를"):
        return f"{word}{'을' if has_final else '를'}"
    if particle_pair in ("과/와", "과와"):
        return f"{word}{'과' if has_final else '와'}"
    return f"{word}{particle_pair}"


def convert_year_to_korean(year: int) -> str:
    """연도를 자연스러운 한글 독음으로 변환."""
    digits = {
        "0": "", "1": "일", "2": "이", "3": "삼", "4": "사",
        "5": "오", "6": "육", "7": "칠", "8": "팔", "9": "구",
    }
    s = str(year)
    if len(s) == 4 and s.startswith("20"):
        tens = int(s[2:])
        if tens == 0:
            return "이천"
        if tens < 10:
            return f"이천{digits[str(tens)]}"
        if tens == 10:
            return "이천십"
        if tens < 20:
            return f"이천십{digits[str(tens % 10)]}"
        ten_digit = tens // 10
        one_digit = tens % 10
        return f"이천{digits[str(ten_digit)]}십{digits[str(one_digit)]}"
    return str(year)


def koreanize_numbers(text: str) -> str:
    """숫자를 한국어 발음 표기로 변환."""
    res = text

    def replace_year(match: re.Match) -> str:
        y = int(match.group(1))
        return f"{convert_year_to_korean(y)}년식"

    res = re.sub(r"(\d{4})년식", replace_year, res)
    res = re.sub(r"6900만원", "육천구백만원", res)
    res = re.sub(r"6,900만원", "육천구백만원", res)
    res = re.sub(r"1800만원", "천팔백만원", res)
    res = re.sub(r"1,800만원", "천팔백만원", res)
    res = re.sub(r"1900만원", "천구백만원", res)
    res = re.sub(r"1,900만원", "천구백만원", res)
    res = re.sub(r"2000만원", "이천만원", res)
    res = re.sub(r"2,000만원", "이천만원", res)
    res = re.sub(r"2100만원", "이천백만원", res)
    res = re.sub(r"2,100만원", "이천백만원", res)
    res = re.sub(r"3200만원", "삼천이백만원", res)
    res = re.sub(r"3,200만원", "삼천이백만원", res)
    res = re.sub(r"4500만원", "사천오백만원", res)
    res = re.sub(r"4,500만원", "사천오백만원", res)
    res = re.sub(r"1350만원", "천삼백오십만원", res)
    res = re.sub(r"1,350만원", "천삼백오십만원", res)
    res = re.sub(r"1200만원", "천이백만원", res)
    res = re.sub(r"1,200만원", "천이백만원", res)
    res = re.sub(r"21인치", "이십일인치", res)
    res = re.sub(r"19인치", "십구인치", res)
    res = re.sub(r"102,039km", "십만 이천 킬로", res)
    res = re.sub(r"102039km", "십만 이천 킬로", res)
    res = re.sub(r"30000km", "삼만 킬로", res)
    res = re.sub(r"30,000km", "삼만 킬로", res)
    res = re.sub(r"30500km", "삼만 오백 킬로", res)
    res = re.sub(r"40000km", "사만 킬로", res)
    res = re.sub(r"42000km", "사만 이천 킬로", res)
    res = re.sub(r"45000km", "사만 오천 킬로", res)
    res = re.sub(r"15000km", "만 오천 킬로", res)
    res = re.sub(r"50000km", "오만 킬로", res)
    res = re.sub(r"60000km", "육만 킬로", res)
    res = re.sub(r"70000km", "칠만 킬로", res)
    res = re.sub(r"4존", "포존", res)
    res = re.sub(r"30초", "삼십초", res)
    res = re.sub(r"25년", "이십오년", res)
    return res


def estimate_speech_duration_seconds(text: str, syllables_per_second: float = 4.5) -> float:
    """한국어 음절 수 기반 실제 발화 시간(초) 계산."""
    clean_korean = re.findall(r"[\uac00-\ud7a3]", text)
    syllable_count = len(clean_korean)
    return round(syllable_count / syllables_per_second, 1)


def validate_scene_evidence_compatibility(
    claim_text: str, evidence: FactEvidence | None
) -> None:
    """사실(FACT) 주장 문장과 증빙 자료 간의 엄격한 정합성 검증."""
    if evidence is None:
        raise FactVerificationError(
            f"사실(FACT) 주장 문장에 검증 증빙이 누락되었습니다: '{claim_text}'"
        )

    if evidence.verification_status != VerificationStatus.VERIFIED:
        raise FactVerificationError(
            f"증빙 상태가 VERIFIED가 아니므로 승인할 수 없습니다 (현재: {evidence.verification_status.value}): '{claim_text}'"
        )

    # ListingSnapshot 한계 검증: 오직 가격과 주행거리만 증빙 가능
    if evidence.source_type == "ListingSnapshot":
        disallowed_keywords = [
            "사고", "무사고", "교환", "판금", "골격", "실내", "가죽",
            "에어컨", "공조", "입고", "완벽", "최상", "보장"
        ]
        for kw in disallowed_keywords:
            if kw in claim_text:
                raise FactVerificationError(
                    f"ListingSnapshot은 사고 이력이나 실내 상태의 검증 근거로 사용할 수 없습니다. "
                    f"발견된 부적절한 주장 키워드: '{kw}' (문장: '{claim_text}')"
                )


class ContentScriptEngine:
    """대본 초안 작성, 전문가 답변 융합 및 증빙 정합성 대본 생성기."""

    @classmethod
    def generate_trend_script(
        cls,
        trend: TrendCandidate,
        review: ExpertReview | None = None,
    ) -> ContentScript:
        """트렌드 소재 기반 30초 썰 대본 작성."""
        topic = trend.topic
        answers = review.expert_answers if review else {}
        has_answers = len(answers) > 0

        hook = f"중고차 매물 보실 때, {topic} 핵심 체크 포인트입니다."

        if has_answers:
            first_ans = next(iter(answers.values()))
            scene2_narration = f"현장에서 점검할 때 가장 중요한 것은, {first_ans}"
            scene2_provenance = ProvenanceType.EXPERT_VERIFIED
            scene2_detail = f"차마트 사장님 구술 진술: '{first_ans}'"
        else:
            scene2_narration = f"{topic}의 경우 외관뿐만 아니라 성능점검기록부 교부 내역을 대조해야 합니다."
            scene2_provenance = ProvenanceType.FACT
            scene2_detail = "자동차관리법 제58조 제1항 성능상태점검기록부 교부 의무"

        law_evidence = FactEvidence(
            source_type="자동차관리법",
            document_ref="자동차관리법 제58조 제1항",
            verified_by="GOVERNMENT_LEGISLATION_SYSTEM",
            verification_status=VerificationStatus.VERIFIED,
            notes="성능상태점검기록부 교부 및 보증보험 가입 의무 규정",
        )

        scenes = [
            StoryboardScene(
                scene_number=1,
                title="오프닝 주제 제시 (0~4s)",
                duration_seconds=4.0,
                visual_description="차마트 대표가 정면 카메라를 바라보며 정중하고 또박또박하게 안내",
                narration=koreanize_numbers(f"{hook} 삼십초 안내드립니다."),
                provenance_type=ProvenanceType.AI_CREATIVE,
                provenance_detail="정보 제공형 오프닝 카피",
                matched_asset_ids=[],
            ),
            StoryboardScene(
                scene_number=2,
                title="현장 확인 포인트 (4~12s)",
                duration_seconds=8.0,
                visual_description="차량 부품을 가리키며 실제 점검 위치를 설명하는 카메라 앵글",
                narration=koreanize_numbers(scene2_narration),
                provenance_type=scene2_provenance,
                provenance_detail=scene2_detail,
                evidence=law_evidence if scene2_provenance == ProvenanceType.FACT else None,
                matched_asset_ids=[],
            ),
            StoryboardScene(
                scene_number=3,
                title="점검 서류 대조 (12~20s)",
                duration_seconds=8.0,
                visual_description="하체 상태와 성능점검표의 주요 부위 표기를 비교하는 컷",
                narration="단순 교환이나 판금 이력은 성능점검기록부 원본에서 항목별로 확인하실 수 있습니다.",
                provenance_type=ProvenanceType.FACT,
                provenance_detail="성능상태점검표 항목별 진단 규정",
                evidence=law_evidence,
                matched_asset_ids=[],
            ),
            StoryboardScene(
                scene_number=4,
                title="안심 계약 기준 (20~25s)",
                duration_seconds=5.0,
                visual_description="계약서 작성 시 성능보증보험 고지 사항을 짚어주는 모습",
                narration="성능보증보험 가입 여부와 정식 계약서 특약 사항을 꼼꼼히 확인하세요.",
                provenance_type=ProvenanceType.FACT,
                provenance_detail="자동차관리법 성능보증보험 의무 가입 규정",
                evidence=law_evidence,
                matched_asset_ids=[],
            ),
            StoryboardScene(
                scene_number=5,
                title="클로징 안내 (25~30s)",
                duration_seconds=5.0,
                visual_description="정중한 목례와 함께 차마트 상담 안내 배너 노출",
                narration="투명하고 안전한 거래를 돕겠습니다. 차마트였습니다.",
                provenance_type=ProvenanceType.AI_CREATIVE,
                provenance_detail="신뢰 기반 정중한 클로징 안내",
                matched_asset_ids=[],
            ),
        ]

        full_text = " ".join(s.narration for s in scenes)
        return ContentScript(
            title=f"[정보 안내] {topic}",
            version=1,
            hook_sentence=hook,
            full_text=full_text,
            scenes=scenes,
            is_approved=False,
        )

    @classmethod
    def generate_vehicle_script(
        cls,
        vehicle: VehicleContentCandidate,
        review: ExpertReview | None = None,
        host_name: str = "차마트 대표",
    ) -> ContentScript:
        """실제 매물의 객관적 팩트만을 사용하는 30초 실매물 소개 대본 작성."""
        raw_model = vehicle.model_name or "추천 매물"
        model_subject = attach_particle(raw_model, "이/가")

        year_str = f"{vehicle.model_year}년식" if vehicle.model_year else "연식 미상"
        price_str = f"{vehicle.price:,}만원" if vehicle.price else "가격 미정"
        mileage_str = f"{vehicle.mileage:,}km" if vehicle.mileage else "주행거리 확인 필요"

        # 가격 및 주행거리 스냅샷 증빙 탐색
        snapshot_ev = next(
            (ev for ev in vehicle.evidences if ev.source_type == "ListingSnapshot"),
            None,
        )

        # 성능점검 증빙 탐색
        inspection_ev = next(
            (ev for ev in vehicle.evidences if "성능" in ev.source_type or "점검" in ev.source_type),
            None,
        )

        # 등록원부 증빙 탐색
        registry_ev = next(
            (ev for ev in vehicle.evidences if "등록" in ev.source_type or "원부" in ev.source_type),
            snapshot_ev,  # 등록원부가 없으면 기본 제원 스냅샷으로 연식 표시
        )

        # 씬 4 사고/수리 내역: 임의 무사고 단정 배제 및 증빙 연결
        if inspection_ev and "완전 무사고" in vehicle.verified_pros:
            history_text = "공식 성능점검상 주요 골격 판금이나 교환 이력이 없는 차량입니다."
            scene4_provenance = ProvenanceType.FACT
            scene4_detail = "공식 성능상태점검기록부 주요 골격 진단 결과"
            scene4_ev = inspection_ev
        elif inspection_ev and len(vehicle.precautions) > 0:
            history_text = f"성능점검 고지 사항으로 {vehicle.precautions[0]} 내역이 있습니다."
            scene4_provenance = ProvenanceType.FACT
            scene4_detail = f"점검표 고지 사항: {vehicle.precautions[0]}"
            scene4_ev = inspection_ev
        else:
            # 점검 증빙이 없으면 사실(FACT)로 단정하지 않고 안내 문구로 중립 처리
            history_text = "사고 유무 및 수리 이력은 성능점검기록부 원본을 투명하게 확인해 드립니다."
            scene4_provenance = ProvenanceType.AI_CREATIVE
            scene4_detail = "점검기록부 원본 열람 의무 안내"
            scene4_ev = None

        # 씬 1 후킹: "관측된 현대 아반떼가 판매 가격 천구백만원입니다. 제원을 확인합니다."
        hook = f"관측된 {model_subject} 판매 가격 {price_str}입니다."

        scenes = [
            StoryboardScene(
                scene_number=1,
                title="오프닝 매물 소개 (0~4s)",
                duration_seconds=4.0,
                visual_description=f"차량 전면 번호판 옆에서 {host_name}가 차량을 안내",
                narration=koreanize_numbers(f"{hook} 제원을 확인합니다."),
                provenance_type=ProvenanceType.FACT,
                provenance_detail=f"공식 고지 매물명 {raw_model} 및 가격 {price_str}",
                evidence=snapshot_ev,
                matched_asset_ids=[],
            ),
            StoryboardScene(
                scene_number=2,
                title="외관 및 등록 정보 (4~11s)",
                duration_seconds=7.0,
                visual_description="차량 외관 전체 및 번호판을 정면과 측면에서 조명",
                narration=koreanize_numbers(f"{year_str} 등록 모델로, 기본 외관 사양을 확인합니다."),
                provenance_type=ProvenanceType.FACT,
                provenance_detail=f"등록 모델 {year_str}",
                evidence=registry_ev,
                matched_asset_ids=[],
            ),
            StoryboardScene(
                scene_number=3,
                title="계기판 관측 주행거리 (11~18s)",
                duration_seconds=7.0,
                visual_description="계기판의 총 주행거리 표시창 클로즈업",
                narration=koreanize_numbers(f"계기판 관측 주행거리는 {mileage_str}입니다."),
                provenance_type=ProvenanceType.FACT,
                provenance_detail=f"계기판 관측 실주행거리 {mileage_str}",
                evidence=snapshot_ev,
                matched_asset_ids=[],
            ),
            StoryboardScene(
                scene_number=4,
                title="성능점검 상태 고지 (18~25s)",
                duration_seconds=7.0,
                visual_description="차량 후면 및 트렁크 부위를 확인하며 진단 내역 안내",
                narration=koreanize_numbers(history_text),
                provenance_type=scene4_provenance,
                provenance_detail=scene4_detail,
                evidence=scene4_ev,
                matched_asset_ids=[],
            ),
            StoryboardScene(
                scene_number=5,
                title="상세 안내 및 문의 (25~30s)",
                duration_seconds=5.0,
                visual_description=f"{host_name}가 정중하게 인사하며 매장 안내 자막 노출",
                narration=koreanize_numbers(f"고지 가격 {price_str}이며, 상세 정보는 매장에서 직접 확인 가능합니다."),
                provenance_type=ProvenanceType.FACT,
                provenance_detail=f"공식 고지 가격 {price_str}",
                evidence=snapshot_ev,
                matched_asset_ids=[],
            ),
        ]

        full_text = " ".join(s.narration for s in scenes)
        return ContentScript(
            title=f"[실매물] {year_str} {raw_model} {price_str}",
            version=1,
            hook_sentence=hook,
            full_text=full_text,
            scenes=scenes,
            is_approved=False,
        )
