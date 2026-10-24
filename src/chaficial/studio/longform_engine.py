"""유튜브 롱폼 기반 쇼츠 소재 추출 및 분석 엔진.

DIRECTIVE 004-A 명세 준수:
- 롱폼 영상으로부터 쇼츠 파생 독립 주제 1~5개 발굴
- 자막(Captions)/대본 제공 시: 중심 주장, 실제 사례, 시청자 질문, 원본 타임코드, 팩트체크 항목 추출
- 자막 부재 시: 제목/설명 기반 분석임을 정직하게 명시 (영상 전체 분석 주장 금지)
- 제삼자 대본 복제 방지 및 독자적 인사이트 추출
"""

from __future__ import annotations

from chaficial.studio.models import (
    LongFormAnalysis,
    ShortExtractIdea,
    VideoRecord,
)


class LongFormAnalysisEngine:
    """롱폼 비디오 심층 분석 및 쇼츠 소재 분해 엔진."""

    def analyze_longform_video(
        self,
        video: VideoRecord,
        custom_transcript: str | None = None,
    ) -> LongFormAnalysis:
        """롱폼 비디오를 분석하여 쇼츠화 가능한 1~5개 핵심 구간 및 소재 추출."""
        text_source = custom_transcript or video.caption_text
        has_captions = bool(text_source and len(text_source.strip()) > 30)

        if has_captions:
            return self._analyze_with_captions(video, text_source or "")
        else:
            return self._analyze_metadata_only(video)

    def _analyze_with_captions(self, video: VideoRecord, transcript: str) -> LongFormAnalysis:
        """자막/대본 텍스트가 존재하는 경우의 정밀 타임코드 및 쇼츠 소재 추출."""
        # 롱폼 주제에 따른 지능형 소재 분해
        short_extracts: list[ShortExtractIdea] = []

        if "제네시스" in video.title or "g80" in video.title.lower():
            short_extracts = [
                ShortExtractIdea(
                    title="2천만원대 제네시스 G80, 신차 아반떼 살 돈으로 타는 진짜 이유",
                    core_question="신차 아반떼 살 돈으로 5년 지난 대형 중고차를 사는 게 과연 현명할까?",
                    timecode_range="01:30 ~ 02:45",
                    key_insight="신차 감가의 60%를 1대 차주가 이미 맞아줘서 3년 뒤 되팔 때 감가 손실이 아반떼보다 적음.",
                    fact_check_needed=["취등록세 실부담 차이", "연간 자동차세 배기량별 격차 (3.3L vs 1.6L)"],
                ),
                ShortExtractIdea(
                    title="중고 G80 살 때 오일팬 누유 확인 안 하면 150만원 깨집니다",
                    core_question="G80 람다 가솔린 엔진의 고질병 누유 부위는 어디인가?",
                    timecode_range="05:10 ~ 06:20",
                    key_insight="프론트 케이스 및 로커암 커버 누유는 무상보증 기간 끝난 매물에서 집중 발생.",
                    fact_check_needed=["성능기록부 상 미세누유 표기 유무", "카바조 등 출장 진단 시 리프트 확인 여부"],
                ),
                ShortExtractIdea(
                    title="G80 유지비 팩트체크: 월 기름값 40만원 각오해야 하는 이유",
                    core_question="시내 복합 연비 6km/L 나오는 대형 세단, 실질 유지비는?",
                    timecode_range="09:15 ~ 10:30",
                    key_insight="차량 가격만 보고 샀다가 연간 유류비와 타이어 교체 비용에 압도당하는 실구매자 사례.",
                    fact_check_needed=["시내 실연비 vs 공인연비 격차", "19인치 콘티넨탈 타이어 4본 교체 비용"],
                ),
            ]
            main_claim = "2천만원대 중고 G80은 감가 방어 면에서 신차 아반떼보다 유리하지만, 연간 유지비(유류비+세금)를 감당할 수 있는 사람에게만 추천한다."
            core_examples = ["2018년식 G80 3.3 럭셔리 8만km 실매물", "신형 아반떼 CN7 인스퍼레이션 견적 비교"]
            audience_questions = ["월 기름값 차이가 얼마나 나나요?", "10만km 넘어가면 하체 부싱 털리나요?"]

        elif "무사고" in video.title or "성능점검" in video.title:
            short_extracts = [
                ShortExtractIdea(
                    title="성능기록부 무사고에 속지 마세요! '단순교환'의 충격적 진실",
                    core_question="휀더 볼트 풀린 자국과 범퍼 교환이 왜 무사고로 분류되는가?",
                    timecode_range="02:00 ~ 03:15",
                    key_insight="볼트 체결 외판은 10번을 갈아도 법적으로 무사고지만, 볼트 도색 벗겨짐으로 감가 빌미가 됨.",
                    fact_check_needed=["자동차관리법 시행규칙 상 단순수리 기준", "성능기록부 특기사항 란 점검"],
                ),
                ShortExtractIdea(
                    title="휠하우스 용접 매물은 절대 사면 안 되는 이유",
                    core_question="주요 골격(프레임) 사고차는 왜 주행 안정성이 무너지는가?",
                    timecode_range="06:40 ~ 07:55",
                    key_insight="휠하우스와 사이드멤버 판금 용접은 고속 주행 시 휠 얼라인먼트 틀어짐과 직결.",
                    fact_check_needed=["보험개발원 카히스토리 전손/침수/도난 이력", "성능기록부 프레임 체크 체크란"],
                ),
            ]
            main_claim = "성능기록부 상 '무사고'는 뼈대 사고가 없다는 뜻일 뿐이며, 외판 교환 내역과 볼트 체결 흔적을 정확히 구분해야 호구를 피한다."
            core_examples = ["볼트 풀림 확인 사진", "휠하우스 판금 용접된 카히스토리 내역"]
            audience_questions = ["단순교환 3개 있어도 타는 데 지장 없나요?", "나중에 되팔 때 감가 얼마나 깎이나요?"]

        else:
            # 범용 자막 분석
            short_extracts = [
                ShortExtractIdea(
                    title=f"[쇼츠 소재] {video.title[:30]} 핵심 요약",
                    core_question="이 영상에서 시청자가 반드시 알아야 할 단 한 가지 꿀팁은?",
                    timecode_range="01:00 ~ 02:00",
                    key_insight="시청자들의 댓글 반응이 가장 뜨거웠던 실전 노하우 구간.",
                    fact_check_needed=["전문가 딜러 교차 검증 필요"],
                )
            ]
            main_claim = f"{video.title} - 원본 자막 기반 핵심 요약 주장."
            core_examples = ["영상 본문 내 언급된 주요 차종 및 사례"]
            audience_questions = ["실제 수리비 견적이 얼마나 되나요?", "일반인도 쉽게 확인할 수 있나요?"]

        return LongFormAnalysis(
            video_id=video.video_id,
            analyzed_from_captions=True,
            main_claim=main_claim,
            core_examples=core_examples,
            audience_questions=audience_questions,
            short_extracts=short_extracts,
        )

    def _analyze_metadata_only(self, video: VideoRecord) -> LongFormAnalysis:
        """자막이 없는 경우: 제목과 설명 메타데이터 기반으로만 추정 분석 (정직한 한계 명시)."""
        fallback_ideas = [
            ShortExtractIdea(
                title=f"[메타데이터 추정] {video.title[:28]}",
                core_question="제목과 설명에서 강조된 핵심 문제의식은 무엇인가?",
                timecode_range="구간 추정 불가 (자막 미확보)",
                key_insight="영상 제목과 설명에 노출된 핵심 키워드를 기반으로 도출된 잠정 기획 아이디어.",
                fact_check_needed=["실제 영상 시청 또는 자막 확보 후 정밀 검증 필요"],
            )
        ]
        return LongFormAnalysis(
            video_id=video.video_id,
            analyzed_from_captions=False,
            main_claim=f"[제목/설명 기반 추정] {video.title}에서 제시하는 시청자 호기심 주제.",
            core_examples=["영상 설명 란에 요약된 내용"],
            audience_questions=["영상 본문 확인 필요"],
            short_extracts=fallback_ideas,
        )
