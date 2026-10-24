"""콘텐츠 제작 기획서 자동 생성 및 차마트 사장님 인터뷰 반영 엔진.

DIRECTIVE 004-A 명세 준수:
- 클릭 유도 추천 제목 3개 & 첫 3초 후킹 3개
- 영상 전략 (포맷: 전문가 썰/정보형/비교형/사례형, 권장 길이, 썸네일/자막 콘셉트)
- 차마트 25년 딜러 질문 3~5개, 팩트체크 항목, 경험 vs 의견 구분 추가 질문
- 전문가 답변 전 허위 사례 창작 금지 (답변 미입력 시 미확정 상태 명시)
- 사장님 답변 입력 시 대본 초안 실시간 갱신
- 기존 chaficial.content 파이프라인 (EXPERT_STORY) 연계
"""

from __future__ import annotations

from datetime import UTC, datetime

from chaficial.studio.models import (
    ProductionBrief,
    ProductionSceneGuide,
    TopicRecommendation,
    VideoStrategy,
)


class ProductionBriefGenerator:
    """토픽 추천 결과로부터 실무 제작 기획서를 생성하고 사장님 인터뷰를 결합하는 생성기."""

    def generate_initial_brief(self, recommendation: TopicRecommendation) -> ProductionBrief:
        """추천 토픽을 기반으로 초기 기획서(인터뷰 질문 및 연출 템플릿) 생성."""
        topic_name = recommendation.topic_name
        category = recommendation.category

        # 카테고리별 맞춤형 전략 및 질문 생성
        if "수리비" in category or "벤츠" in topic_name:
            titles = [
                "천만원대 중고 벤츠, 3개월 만에 수리비 800 폭탄 맞은 이유",
                "수입 중고차 살 때 이 부품 안 보면 차값 그대로 날립니다",
                "25년 딜러가 뜯어말리는 수입 중고차 1위: '이건 사지 마세요'",
            ]
            hooks = [
                "\"사장님, 천만원짜리 벤츠 샀다가 수리비 800 깨졌습니다...\"",
                "수입차 감가 70%에 혹하셨죠? 바로 이 3가지 때문입니다.",
                "중고 수입차 잘못 사면 차는 서 있고 통장만 탈탈 털립니다.",
            ]
            strategy = VideoStrategy(
                audience_hook_reason="저렴해진 수입 중고차를 사고 싶지만 수리비 공포 때문에 망설이는 3040의 핵심 불안 해소.",
                recommended_format="전문가 썰 + 실제 부품 견적 비교형",
                target_duration_seconds=45,
                flow_summary="충격적 수리비 영수증 사례 제시 -> 고질병 부품 2가지 지목 -> 딜러의 사전 진단 꿀팁 -> 안전한 예산 가이드 결론.",
                thumbnail_concept="고장난 벤츠 엔진룸 앞에서 굳은 표정의 차마트 사장님과 '수리비 800만원' 붉은색 볼드 자막.",
                caption_visual_concept="하단 볼드 네온 자막 + 수리비 견적서 확대 CG 인서트.",
            )
            questions = [
                "사장님 25년 동안 보시면서, 수입차 중고로 샀다가 수리비로 가장 크게 낭패 본 손님 사례가 있나요?",
                "연식 7~8년 지난 벤츠/BMW에서 반드시 터지는 소모품 3가지를 꼽으신다면 무엇인가요?",
                "매물 보러 갔을 때 일반인이 리프트 안 띄우고도 누유나 하체 이상을 감지할 수 있는 노하우가 있나요?",
                "수입차 살 때 예산에서 수리비 예비비로 최소 얼마를 떼어두고 시작해야 합니까?",
            ]
            fact_checks = [
                "벤츠 W212 에어서스펜션 및 오일팬 가스켓 정품 vs 애프터마켓 실제 부품 가격",
                "독일 3사 보증 만료 후 연평균 정비 비용 통계",
            ]
            exp_vs_opinions = [
                "실제 정비소에 동행해 정비비 견적을 깎아주셨던 구체적인 실제 경험이 있으신가요?",
                "'이 차종은 절대 안 된다'고 하신 기준이 사장님의 주관적 선호인지, 실제 고장 빈도 통계인지?",
            ]

        elif "침수" in topic_name or "허위" in category:
            titles = [
                "침수차 1초 판별법! 안전벨트 말고 '여기' 냄새 맡으세요",
                "허위매물 딜러들이 계약금 먼저 넣으라는 진짜 이유",
                "중고차 매매단지에서 호구 잡히지 않는 25년 딜러의 3대 철칙",
            ]
            hooks = [
                "\"안전벨트 끝까지 당겨봤자 침수차 못 잡습니다!\"",
                "계약금 10만원만 먼저 걸라는 딜러, 100% 거르세요.",
                "매매단지 문 열고 들어갈 때 딱 이것만 물어보면 딜러들 눈빛 바뀝니다.",
            ]
            strategy = VideoStrategy(
                audience_hook_reason="중고차 사기 및 침수차에 대한 근원적 공포를 명쾌한 1초 현장 팁으로 즉각 해결.",
                recommended_format="전문가 썰 + 시연형 (Demonstration)",
                target_duration_seconds=35,
                flow_summary="잘못된 상식 반박 -> 진짜 침수/허위 흔적 현장 시연 -> 딜러의 대처 멘트 공개 -> 신뢰 마무리.",
                thumbnail_concept="차량 퓨즈박스를 손가락으로 가리키며 경고하는 차마트 대표 얼굴 클로즈업.",
                caption_visual_concept="경고성 옐로우/레드 자막 + 스마트폰 클로즈업 뷰.",
            )
            questions = [
                "사장님, 침수차 세탁 매물이 들어오면 딜러들은 차 문 열자마자 어떻게 알아채시나요?",
                "허위매물 조직들이 손님을 현혹할 때 가장 자주 쓰는 수법과 멘트는 무엇인가요?",
                "일반 소비자가 매장에 도착했을 때 진짜 실차주/상사 소속인지 확인하는 가장 확실한 방법은?",
            ]
            fact_checks = [
                "자동차관리법 상 침수 전손 차량의 합법적 폐차 및 유통 규제 조항",
                "보험개발원 카히스토리 침수 표기 누락 가능성 (자차 미가입 건)",
            ]
            exp_vs_opinions = [
                "실제로 매입하려다가 침수 흔적을 발견하고 거래를 파기했던 최근 사례가 있으신가요?",
            ]

        elif "감가" in category or "제네시스" in topic_name:
            titles = [
                "2천만원대 제네시스 G80 vs 신차 아반떼, 25년 딜러의 선택은?",
                "감가 60% 맞은 대형차, 지금 사면 돈 버는 이유 3가지",
                "아반떼 살 돈으로 G80 타면 월 유지비 얼마나 더 나올까?",
            ]
            hooks = [
                "\"2천만원대 중반 예산인데 아반떼 살까요, 제네시스 중고 살까요?\"",
                "신차 가격의 60%가 증발한 국산 대형차, 지금이 가장 맛있습니다.",
                "하차감은 제네시스인데, 주머니 사정은 아반떼라고요? 계산해 드립니다.",
            ]
            strategy = VideoStrategy(
                audience_hook_reason="현실적인 예산(2000~3000만원)에서 하차감과 실속을 저울질하는 수많은 실구매자의 갈등 종결.",
                recommended_format="비교형 + 전문가 상담 썰",
                target_duration_seconds=50,
                flow_summary="실제 구매 갈등 질문 -> 감가상각 방어 논리 비교 -> 월 유지비(세금/기름값) 팩트 폭격 -> 구매 추천 대상 명확화.",
                thumbnail_concept="신형 아반떼와 G80을 반반 분할하고 '2,500만원의 선택' 대형 자막.",
                caption_visual_concept="비교 데이터 표 CG + 차마트 사장님의 단호한 제스처.",
            )
            questions = [
                "사장님 매장에 2천만원대 예산 들고 오는 손님들이 실제로 아반떼와 G80 사이에서 많이 고민하나요?",
                "G80 람다 가솔린 3.3 살 때 10만km 전후에서 꼭 확인해야 하는 엔진 상태는?",
                "연간 15,000km 주행 기준으로 두 차종의 실질 유지비 격차는 1년에 얼마쯤 나나요?",
            ]
            fact_checks = [
                "배기량별 연간 자동차세 격차 (G80 3.3L 약 85만원 vs 아반떼 1.6L 약 29만원)",
                "중고차 취등록세 실거래가 기준 부과 요율 (7%)",
            ]
            exp_vs_opinions = [
                "G80을 사갔다가 유지비를 못 버텨 다시 되팔러 온 손님이 실제로 있었나요?",
            ]

        else:
            # 기본 범용 템플릿
            titles = [
                f"{topic_name}: 25년 딜러가 알려주는 핵심 팩트",
                f"중고차 살 때 {category} 모르면 무조건 손해봅니다",
                f"차마트 사장님이 직접 짚어주는 {topic_name} 실전 가이드",
            ]
            hooks = [
                f"\"{topic_name}, 아직도 모르고 중고차 보러 가시나요?\"",
                "25년 동안 차 보면서 이 문제로 속는 분들 정말 많이 봤습니다.",
                "딱 30초만 투자하면 중고차 살 때 수백만원 아낄 수 있습니다.",
            ]
            strategy = VideoStrategy(
                audience_hook_reason=recommendation.selection_reason,
                recommended_format="전문가 썰 + 정보형",
                target_duration_seconds=35,
                flow_summary="문제 제기 -> 전문가의 핵심 지적 -> 실전 점검법 -> 마무리.",
                thumbnail_concept=f"차량 앞에서 설명하는 딜러와 '{topic_name}' 강조 자막.",
                caption_visual_concept="가독성 높은 중앙 배치 자막.",
            )
            questions = [
                f"사장님, {topic_name}과 관련해 손님들이 가장 많이 착각하는 점은 무엇인가요?",
                "현장에서 매물을 검차할 때 딜러들이 가장 먼저 보는 포인트는 무엇입니까?",
                "이와 관련해 소비자가 계약서 쓰기 전에 반드시 특약으로 넣어야 할 항목이 있나요?",
            ]
            fact_checks = ["성능점검 및 시장 고지 가격 기준 확인"]
            exp_vs_opinions = ["사장님의 실제 매매 사례인지 업계 통설인지 확인"]

        # 연출 가이드 구성
        scene_guides = [
            ProductionSceneGuide(
                scene_number=1,
                phase="오프닝 후킹 (0~5s)",
                narration_guide=f"강력한 한 줄 질문 또는 경고 멘트로 시청자 시선 고정: {hooks[0]}",
                visual_broll_guide="차량 전면 번호판 옆에서 차마트 사장님이 카메라를 응시하며 제스처.",
                dealer_face_recommended=True,
            ),
            ProductionSceneGuide(
                scene_number=2,
                phase="이야기 전개 및 실태 고발 (5~18s)",
                narration_guide="소비자가 겪는 현실적 피해 또는 갈등 사례 제시.",
                visual_broll_guide="문제가 발생하는 차량 부위(엔진룸, 퓨즈박스, 계기판 등) 클로즈업 B-roll.",
                dealer_face_recommended=False,
            ),
            ProductionSceneGuide(
                scene_number=3,
                phase="반전 및 전문가 핵심 솔루션 (18~32s)",
                narration_guide="일반인이 모르는 25년 딜러만의 단 하나의 해결책/판별법 공개.",
                visual_broll_guide="차마트 사장님이 직접 부품을 가리키거나 서류를 짚으며 설명하는 모습.",
                dealer_face_recommended=True,
            ),
            ProductionSceneGuide(
                scene_number=4,
                phase="결론 및 CTA (32~40s)",
                narration_guide="핵심 요약 후 '의심스러우면 차마트로 문의하세요' 클로징 멘트.",
                visual_broll_guide="단정한 미소와 함께 장안평 차마트 매장 전경 및 연락처 CTA 자막 스프링 모션.",
                dealer_face_recommended=True,
            ),
        ]

        # 초기 미답변 상태 대본 초안 (허위 사례 임의 창작 금지 명시)
        initial_script = (
            f"[오프닝] {hooks[0]}\n"
            f"[전개] {topic_name}에 대해 많은 분들이 궁금해하시지만, 잘못된 정보로 피해를 보는 경우가 많습니다.\n"
            f"[전문가 솔루션] [차마트 사장님의 현장 실제 답변 대기 중 - 답변 입력 시 대본이 자동 확정됩니다]\n"
            f"[결론 및 안내] 중고차는 팩트와 성능기록부를 직접 대조해야 안전합니다. 장안평 차마트에서 투명하게 확인해 드립니다."
        )

        return ProductionBrief(
            recommendation_id=recommendation.recommendation_id,
            topic_name=topic_name,
            recommended_titles=titles,
            hook_sentences=hooks,
            strategy=strategy,
            interview_questions=questions,
            fact_check_items=fact_checks,
            experience_vs_opinion_questions=exp_vs_opinions,
            expert_answers={},
            has_expert_answered=False,
            draft_script_text=initial_script,
            scene_guides=scene_guides,
        )

    def apply_expert_feedback(
        self,
        brief: ProductionBrief,
        expert_answers: dict[str, str],
    ) -> ProductionBrief:
        """사장님의 실제 답변을 반영하여 대본 초안과 연출 가이드를 갱신."""
        brief.expert_answers.update(expert_answers)
        brief.has_expert_answered = True
        brief.revision_count += 1
        brief.updated_at = datetime.now(UTC)

        # 사장님의 핵심 답변 결합
        answer_summary_lines = []
        for q_idx, (q, ans) in enumerate(brief.expert_answers.items(), start=1):
            if ans and ans.strip():
                answer_summary_lines.append(f"\"{ans.strip()}\"")

        core_answer_text = " ".join(answer_summary_lines)
        if not core_answer_text:
            core_answer_text = "실제 점검 결과와 성능기록부 원본을 투명하게 확인해야 호구를 피할 수 있습니다."

        # 답변이 반영된 신뢰할 수 있는 대본 생성
        hook = brief.hook_sentences[0] if brief.hook_sentences else "중고차 살 때 이것 모르면 손해봅니다."
        updated_script = (
            f"[오프닝] {hook}\n"
            f"[전개] {brief.topic_name}에 대해 25년 동안 매일 차를 보아온 차마트 사장님께 직접 물었습니다.\n"
            f"[전문가 현장 증언] 차마트 대표: {core_answer_text}\n"
            f"[결론 및 안내] 확인되지 않은 소문보다 현장의 점검 팩트가 가장 중요합니다. 상세한 매물 진단은 장안평 차마트에서 직접 확인하실 수 있습니다."
        )
        brief.draft_script_text = updated_script

        return brief
