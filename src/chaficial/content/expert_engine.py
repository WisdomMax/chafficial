"""전문가(차마트 사장님) 인터뷰 질문 생성 및 답변/검토 관리 엔진.

DIRECTIVE 003-A 명세 준수:
- 25년 경력 중고차 전문가인 차마트 사장님에게 실전 질문 자동 생성
- 사용자가 직접 입력한 사장님의 답변 수집 및 기록
- 사실 확인이 필요한 항목(fact_check_items) 추적
- 승인 상태 관리 (PENDING -> APPROVED / REJECTED)
"""

from __future__ import annotations

from datetime import UTC, datetime

from chaficial.content.models import (
    ContentType,
    ExpertReview,
    TrendCandidate,
    VehicleContentCandidate,
)
from chaficial.content.repository import ContentRepository


class ExpertIntelligenceEngine:
    """차마트 사장님과의 질의응답을 관리하고 실전 지식을 대본에 연결하는 규칙 기반 인터뷰 엔진.
    
    [알고리즘 명세]:
    - 질문 생성: 25년 현장 딜러 검증 체크리스트에 기반한 '규칙 기반 도메인 템플릿(Rule-based Domain Template)'
    - 답변 관리: 사용자가 직접 입력한 대표님 음성/텍스트 구술 답변을 1:1로 매핑하여 영속화
    - (LLM 자동 생성 질의가 아닌 사전 정의된 전문가 안전 검증 템플릿을 조합하여 출력합니다.)
    """

    def __init__(self, repository: ContentRepository) -> None:
        self.repository = repository

    def generate_interview_questions_for_trend(
        self, trend: TrendCandidate
    ) -> list[str]:
        """트렌드 인기 영상 소재를 바탕으로 사장님께 여쭤볼 핵심 질문 3개 생성."""
        topic = trend.topic
        questions = [
            f"사장님, 최근 숏폼에서 '{topic}' 관련 영상이 큰 인기를 끌고 있습니다. 25년 동안 매매단지에 계시면서 실제로 이런 사례를 직접 보신 적이 있으신가요?",
            "일반 소비자들이 유튜브만 보고 따라 하다가 오히려 놓치기 쉬운 '현직 딜러만 아는 진짜 핵심 팁'은 무엇인가요?",
            "이 영상을 보고 우리 차마트에 문의하시는 고객님들께 '이것만큼은 확실하게 보장해 드린다'고 약속할 수 있는 사장님만의 원칙은 무엇인가요?",
        ]
        return questions

    def generate_interview_questions_for_vehicle(
        self, vehicle: VehicleContentCandidate
    ) -> list[str]:
        """추천 매물을 바탕으로 사장님께 확인받을 질문 생성."""
        model_name = vehicle.model_name or "해당 차량"
        year = vehicle.model_year or "연식미상"
        price = f"{vehicle.price}만원" if vehicle.price else "가격미정"

        questions = [
            f"사장님, 이번 추천 매물은 '{year}년식 {model_name}({price})'입니다. 이 차량을 매입하셨을 때 가장 마음에 드셨던 핵심 매력(장점)은 무엇인가요?",
            f"주행거리 {vehicle.mileage or 0:,}km 기준, 하체 잡소리나 누유, 엔진 미션 상태는 직접 시운전해 보셨을 때 어떠셨나요?",
            "사고/교환 이력이나 고객이 미리 알아두면 오히려 신뢰가 올라갈 '솔직한 특이사항'이 있다면 말씀해 주세요.",
        ]
        return questions

    def create_expert_review_session(
        self,
        target_id: str,
        target_type: ContentType,
        source_data: TrendCandidate | VehicleContentCandidate,
    ) -> ExpertReview:
        """전문가 인터뷰 및 팩트 체크 세션 생성."""
        if target_type == ContentType.EXPERT_STORY and isinstance(source_data, TrendCandidate):
            questions = self.generate_interview_questions_for_trend(source_data)
            fact_checks = [
                f"원천 영상({source_data.platform})의 주장이 실제 자동차관리법 및 성능점검 기준에 부합하는지 여부",
                "자극적인 허위 과장 표현 배제 여부",
            ]
        elif target_type == ContentType.VEHICLE_PROMOTION and isinstance(source_data, VehicleContentCandidate):
            questions = self.generate_interview_questions_for_vehicle(source_data)
            fact_checks = [
                f"차량등록원부 및 성능상태점검기록부와 일치 여부 (연식: {source_data.model_year}, 주행: {source_data.mileage}km)",
                f"고지된 가격({source_data.price}만원)이 실판매 가능 가격인지 여부",
                "사용 권한(republication_allowed)이 확보된 정품 실차 사진인지 여부",
            ]
        else:
            questions = ["기본 확인 질문: 이 콘텐츠를 실제 제작해도 안전합니까?"]
            fact_checks = ["기본 팩트 체크"]

        review = ExpertReview(
            target_id=target_id,
            target_type=target_type,
            generated_questions=questions,
            expert_answers={},
            fact_check_items=fact_checks,
            approval_status="PENDING",
            reviewer_name="차마트 사장님 (25년 경력)",
        )
        return self.repository.save_review(review)

    def record_expert_answers(
        self,
        review_id: str,
        answers: dict[str, str],
        revision_notes: str | None = None,
        approve: bool = False,
    ) -> ExpertReview:
        """사장님의 구술 답변 및 수정 지침을 기록하고 승인 여부 갱신."""
        review = self.repository.get_review(review_id)
        if not review:
            raise ValueError(f"검토 세션 ID '{review_id}'를 찾을 수 없습니다.")

        review.expert_answers.update(answers)
        if revision_notes:
            review.revision_notes = revision_notes

        if approve:
            review.approval_status = "APPROVED"
            review.reviewed_at = datetime.now(UTC)

        return self.repository.save_review(review)
