"""SQLite 기반 로컬 영속화 저장소.

DIRECTIVE 004-A 명세 준수:
- 서버 재시작 및 재접속 시에도 수집 영상, 추천 토픽, 기획서, 사장님 답변 유지
- 토픽 상태(ADOPTED, SHELVED, DISMISSED) 변경 영구 보존
- 검색 키워드, 플랫폼 연결 상태, 쿼터 사용 로그 영속화
- 외부 종속성 없이 Python 내장 sqlite3 모듈 사용
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chaficial.studio.models import (
    AnalysisConfidence,
    ContentFormat,
    ContentPlatform,
    FormatConfidence,
    ProductionBrief,
    TopicRecommendation,
    TopicStatus,
    VideoRecord,
)


class StudioStorage:
    """스튜디오 데이터 영속화 저장소 (SQLite 기반)."""

    def __init__(self, db_path: str = "data/studio_storage.db") -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            # 1. 비디오 테이블
            cur.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    video_id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    content_format TEXT NOT NULL,
                    format_confidence TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    channel_name TEXT NOT NULL,
                    channel_id TEXT,
                    description TEXT,
                    published_at TEXT NOT NULL,
                    duration_seconds INTEGER DEFAULT 0,
                    view_count INTEGER DEFAULT 0,
                    like_count INTEGER DEFAULT 0,
                    comment_count INTEGER DEFAULT 0,
                    discovered_at TEXT NOT NULL,
                    has_captions INTEGER DEFAULT 0,
                    caption_text TEXT,
                    matched_keywords TEXT,
                    topic_ids TEXT,
                    raw_json TEXT
                )
            """)

            # 2. 추천 토픽 테이블
            cur.execute("""
                CREATE TABLE IF NOT EXISTS topic_recommendations (
                    recommendation_id TEXT PRIMARY KEY,
                    topic_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    rank INTEGER DEFAULT 1,
                    popularity_score REAL DEFAULT 0.0,
                    velocity_score REAL DEFAULT 0.0,
                    dealer_fit_score REAL DEFAULT 0.0,
                    composite_score REAL DEFAULT 0.0,
                    status TEXT NOT NULL,
                    confidence_level TEXT NOT NULL,
                    supporting_video_ids TEXT,
                    selection_reason TEXT,
                    trend_summary TEXT,
                    is_newly_discovered INTEGER DEFAULT 1,
                    prompt_version TEXT,
                    model_name TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # 3. 제작 기획서 테이블
            cur.execute("""
                CREATE TABLE IF NOT EXISTS production_briefs (
                    brief_id TEXT PRIMARY KEY,
                    recommendation_id TEXT NOT NULL,
                    topic_name TEXT NOT NULL,
                    recommended_titles TEXT,
                    hook_sentences TEXT,
                    strategy_json TEXT,
                    interview_questions TEXT,
                    fact_check_items TEXT,
                    experience_vs_opinion_questions TEXT,
                    expert_answers_json TEXT,
                    has_expert_answered INTEGER DEFAULT 0,
                    draft_script_text TEXT,
                    scene_guides_json TEXT,
                    linked_project_id TEXT,
                    is_approved INTEGER DEFAULT 0,
                    revision_count INTEGER DEFAULT 1,
                    updated_at TEXT NOT NULL
                )
            """)

            # 4. 설정 및 키워드 테이블
            cur.execute("""
                CREATE TABLE IF NOT EXISTS studio_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    # =========================================================================
    # 비디오 CRUD
    # =========================================================================

    def save_videos(self, videos: list[VideoRecord]) -> None:
        if not videos:
            return
        with self._get_connection() as conn:
            cur = conn.cursor()
            for v in videos:
                cur.execute("""
                    INSERT INTO videos (
                        video_id, platform, content_format, format_confidence,
                        url, title, channel_name, channel_id, description,
                        published_at, duration_seconds, view_count, like_count, comment_count,
                        discovered_at, has_captions, caption_text, matched_keywords, topic_ids, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(video_id) DO UPDATE SET
                        view_count=excluded.view_count,
                        like_count=excluded.like_count,
                        comment_count=excluded.comment_count,
                        matched_keywords=excluded.matched_keywords,
                        topic_ids=excluded.topic_ids
                """, (
                    v.video_id,
                    v.platform.value,
                    v.content_format.value,
                    v.format_confidence.value,
                    v.url,
                    v.title,
                    v.channel_name,
                    v.channel_id,
                    v.description,
                    v.published_at.isoformat(),
                    v.duration_seconds,
                    v.view_count,
                    v.like_count,
                    v.comment_count,
                    v.discovered_at.isoformat(),
                    1 if v.has_captions else 0,
                    v.caption_text,
                    json.dumps(v.matched_keywords, ensure_ascii=False),
                    json.dumps(v.topic_ids, ensure_ascii=False),
                    json.dumps(v.raw_metadata, ensure_ascii=False),
                ))
            conn.commit()

    def list_videos(
        self,
        platform: ContentPlatform | None = None,
        content_format: ContentFormat | None = None,
        limit: int = 100,
    ) -> list[VideoRecord]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM videos WHERE 1=1"
            params: list[Any] = []
            if platform:
                query += " AND platform = ?"
                params.append(platform.value)
            if content_format:
                query += " AND content_format = ?"
                params.append(content_format.value)
            query += " ORDER BY published_at DESC LIMIT ?"
            params.append(limit)

            rows = cur.execute(query, params).fetchall()
            results: list[VideoRecord] = []
            for r in rows:
                results.append(
                    VideoRecord(
                        video_id=r["video_id"],
                        platform=ContentPlatform(r["platform"]),
                        content_format=ContentFormat(r["content_format"]),
                        format_confidence=FormatConfidence(r["format_confidence"]),
                        url=r["url"],
                        title=r["title"],
                        channel_name=r["channel_name"],
                        channel_id=r["channel_id"],
                        description=r["description"] or "",
                        published_at=datetime.fromisoformat(r["published_at"]),
                        duration_seconds=r["duration_seconds"],
                        view_count=r["view_count"],
                        like_count=r["like_count"],
                        comment_count=r["comment_count"],
                        discovered_at=datetime.fromisoformat(r["discovered_at"]),
                        has_captions=bool(r["has_captions"]),
                        caption_text=r["caption_text"],
                        matched_keywords=json.loads(r["matched_keywords"] or "[]"),
                        topic_ids=json.loads(r["topic_ids"] or "[]"),
                        raw_metadata=json.loads(r["raw_json"] or "{}"),
                    )
                )
            return results

    # =========================================================================
    # 토픽 추천 CRUD
    # =========================================================================

    def save_topic_recommendations(self, recs: list[TopicRecommendation]) -> None:
        if not recs:
            return
        with self._get_connection() as conn:
            cur = conn.cursor()
            for r in recs:
                cur.execute("""
                    INSERT INTO topic_recommendations (
                        recommendation_id, topic_name, category, rank,
                        popularity_score, velocity_score, dealer_fit_score, composite_score,
                        status, confidence_level, supporting_video_ids,
                        selection_reason, trend_summary, is_newly_discovered,
                        prompt_version, model_name, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(recommendation_id) DO UPDATE SET
                        rank=excluded.rank,
                        composite_score=excluded.composite_score,
                        status=excluded.status,
                        updated_at=excluded.updated_at
                """, (
                    r.recommendation_id,
                    r.topic_name,
                    r.category,
                    r.rank,
                    r.popularity_score,
                    r.velocity_score,
                    r.dealer_fit_score,
                    r.composite_score,
                    r.status.value,
                    r.confidence_level.value,
                    json.dumps(r.supporting_video_ids, ensure_ascii=False),
                    r.selection_reason,
                    r.trend_summary,
                    1 if r.is_newly_discovered else 0,
                    r.prompt_version,
                    r.model_name,
                    r.created_at.isoformat(),
                    r.updated_at.isoformat(),
                ))
            conn.commit()

    def list_topic_recommendations(self, status: TopicStatus | None = None) -> list[TopicRecommendation]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM topic_recommendations WHERE 1=1"
            params: list[Any] = []
            if status:
                query += " AND status = ?"
                params.append(status.value)
            query += " ORDER BY rank ASC, composite_score DESC"

            rows = cur.execute(query, params).fetchall()
            results: list[TopicRecommendation] = []
            for r in rows:
                results.append(
                    TopicRecommendation(
                        recommendation_id=r["recommendation_id"],
                        topic_name=r["topic_name"],
                        category=r["category"],
                        rank=r["rank"],
                        popularity_score=r["popularity_score"],
                        velocity_score=r["velocity_score"],
                        dealer_fit_score=r["dealer_fit_score"],
                        composite_score=r["composite_score"],
                        status=TopicStatus(r["status"]),
                        confidence_level=AnalysisConfidence(r["confidence_level"]),
                        supporting_video_ids=json.loads(r["supporting_video_ids"] or "[]"),
                        selection_reason=r["selection_reason"] or "",
                        trend_summary=r["trend_summary"] or "",
                        is_newly_discovered=bool(r["is_newly_discovered"]),
                        prompt_version=r["prompt_version"] or "v1.0.0",
                        model_name=r["model_name"] or "default",
                        created_at=datetime.fromisoformat(r["created_at"]),
                        updated_at=datetime.fromisoformat(r["updated_at"]),
                    )
                )
            return results

    def update_topic_status(self, recommendation_id: str, status: TopicStatus) -> bool:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE topic_recommendations
                SET status = ?, updated_at = ?
                WHERE recommendation_id = ?
            """, (status.value, datetime.now(UTC).isoformat(), recommendation_id))
            conn.commit()
            return cur.rowcount > 0

    # =========================================================================
    # 기획서 CRUD
    # =========================================================================

    def save_brief(self, brief: ProductionBrief) -> None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO production_briefs (
                    brief_id, recommendation_id, topic_name,
                    recommended_titles, hook_sentences, strategy_json,
                    interview_questions, fact_check_items, experience_vs_opinion_questions,
                    expert_answers_json, has_expert_answered, draft_script_text,
                    scene_guides_json, linked_project_id, is_approved, revision_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(brief_id) DO UPDATE SET
                    recommended_titles=excluded.recommended_titles,
                    hook_sentences=excluded.hook_sentences,
                    strategy_json=excluded.strategy_json,
                    expert_answers_json=excluded.expert_answers_json,
                    has_expert_answered=excluded.has_expert_answered,
                    draft_script_text=excluded.draft_script_text,
                    scene_guides_json=excluded.scene_guides_json,
                    linked_project_id=excluded.linked_project_id,
                    is_approved=excluded.is_approved,
                    revision_count=excluded.revision_count,
                    updated_at=excluded.updated_at
            """, (
                brief.brief_id,
                brief.recommendation_id,
                brief.topic_name,
                json.dumps(brief.recommended_titles, ensure_ascii=False),
                json.dumps(brief.hook_sentences, ensure_ascii=False),
                brief.strategy.model_dump_json(),
                json.dumps(brief.interview_questions, ensure_ascii=False),
                json.dumps(brief.fact_check_items, ensure_ascii=False),
                json.dumps(brief.experience_vs_opinion_questions, ensure_ascii=False),
                json.dumps(brief.expert_answers, ensure_ascii=False),
                1 if brief.has_expert_answered else 0,
                brief.draft_script_text,
                json.dumps([s.model_dump() for s in brief.scene_guides], ensure_ascii=False),
                brief.linked_project_id,
                1 if brief.is_approved else 0,
                brief.revision_count,
                brief.updated_at.isoformat(),
            ))
            conn.commit()

    def get_brief_by_recommendation(self, recommendation_id: str) -> ProductionBrief | None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            row = cur.execute(
                "SELECT * FROM production_briefs WHERE recommendation_id = ? LIMIT 1",
                (recommendation_id,),
            ).fetchone()
            if not row:
                return None
            from chaficial.studio.models import ProductionSceneGuide, VideoStrategy
            return ProductionBrief(
                brief_id=row["brief_id"],
                recommendation_id=row["recommendation_id"],
                topic_name=row["topic_name"],
                recommended_titles=json.loads(row["recommended_titles"] or "[]"),
                hook_sentences=json.loads(row["hook_sentences"] or "[]"),
                strategy=VideoStrategy.model_validate_json(row["strategy_json"]),
                interview_questions=json.loads(row["interview_questions"] or "[]"),
                fact_check_items=json.loads(row["fact_check_items"] or "[]"),
                experience_vs_opinion_questions=json.loads(row["experience_vs_opinion_questions"] or "[]"),
                expert_answers=json.loads(row["expert_answers_json"] or "{}"),
                has_expert_answered=bool(row["has_expert_answered"]),
                draft_script_text=row["draft_script_text"] or "",
                scene_guides=[ProductionSceneGuide.model_validate(s) for s in json.loads(row["scene_guides_json"] or "[]")],
                linked_project_id=row["linked_project_id"],
                is_approved=bool(row["is_approved"]),
                revision_count=row["revision_count"],
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    # =========================================================================
    # 설정 및 키워드 CRUD
    # =========================================================================

    def get_setting(self, key: str, default: str = "") -> str:
        with self._get_connection() as conn:
            cur = conn.cursor()
            row = cur.execute("SELECT setting_value FROM studio_settings WHERE setting_key = ?", (key,)).fetchone()
            return row["setting_value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO studio_settings (setting_key, setting_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(setting_key) DO UPDATE SET
                    setting_value=excluded.setting_value,
                    updated_at=excluded.updated_at
            """, (key, value, datetime.now(UTC).isoformat()))
            conn.commit()
