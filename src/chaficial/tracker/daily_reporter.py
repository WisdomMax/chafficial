"""CHA-FICIAL 일별 시장 관측 요약 보고서 생성 모듈 (DIRECTIVE 013-A).

- UTC 시각의 KST(UTC+9) 날짜 정확한 변환
- 임시 파일 저장 후 원자적 교체(Atomic replace)로 보고서 무결성 보장
- 파싱률, 재관측률, 가격 인하/인상 건수 및 누적 현황 구조화 집계
"""

from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from chaficial.models import Listing, ListingSnapshot, PriceEvent, BatchAuditLog


def to_kst_date_str(dt: datetime | None) -> str | None:
    """UTC 시각을 KST(UTC+9) 기준 날짜 문자열(YYYY-MM-DD)로 변환합니다."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt_aware = dt.replace(tzinfo=UTC)
    else:
        dt_aware = dt.astimezone(UTC)
    kst_dt = dt_aware + timedelta(hours=9)
    return kst_dt.strftime("%Y-%m-%d")


class DailyMarketReporter:
    """일별 시장 관측 요약 보고서 생성기 (KST 기준, 원자적 저장 보장)."""

    def __init__(self, db_path: Path, output_dir: Path | None = None):
        self.db_path = db_path
        self.output_dir = output_dir or Path("reports/daily_summaries")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.db_path}")

    def generate_daily_summary(self, target_date_str: str | None = None) -> Path:
        """지정된 날짜(YYYY-MM-DD KST 기준, 기본 오늘 KST)의 일별 시장 요약 보고서를 원자적으로 생성합니다."""
        now_utc = datetime.now(UTC)
        if not target_date_str:
            target_date_str = to_kst_date_str(now_utc)

        with Session(self.engine) as session:
            # 1. 누적 총계
            total_listings = session.execute(select(func.count(Listing.listing_id))).scalar() or 0
            total_snapshots = session.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar() or 0
            total_events = session.execute(select(func.count(PriceEvent.event_id))).scalar() or 0
            total_batches = session.execute(select(func.count(BatchAuditLog.batch_id))).scalar() or 0

            # 2. 해당 일자의 관측 배치 조회 (KST 기준)
            all_batches = session.execute(
                select(BatchAuditLog).order_by(BatchAuditLog.processed_at.desc())
            ).scalars().all()

            daily_batches = [
                b for b in all_batches
                if b.processed_at and to_kst_date_str(b.processed_at) == target_date_str
            ]

            # 3. 해당 일자의 이벤트 집계 (KST 기준)
            all_events = session.execute(
                select(PriceEvent).order_by(PriceEvent.event_timestamp.desc())
            ).scalars().all()

            daily_events = [
                e for e in all_events
                if e.event_timestamp and to_kst_date_str(e.event_timestamp) == target_date_str
            ]

            first_seen_count = sum(1 for e in daily_events if e.event_type in ("NEW_LISTING", "FIRST_SEEN"))
            price_drop_events = [e for e in daily_events if e.event_type == "PRICE_DROP"]
            price_increase_events = [e for e in daily_events if e.event_type == "PRICE_INCREASE"]

            total_price_drop_krw = sum(abs(e.price_delta_krw) for e in price_drop_events)
            total_price_inc_krw = sum(e.price_delta_krw for e in price_increase_events)

            # 배치 메타데이터 기반 파싱 수 및 재관측 수 집계
            daily_parsed_count = sum(b.record_count for b in daily_batches)
            daily_reobserved_count = 0
            for b in daily_batches:
                meta = b.get_audit_metadata()
                if meta:
                    daily_reobserved_count += meta.get("re_observed_count", 0)

            # 4. 보고서 마크다운 생성
            date_clean = target_date_str.replace("-", "")
            report_file = self.output_dir / f"daily_market_summary_{date_clean}.md"
            temp_file = self.output_dir / f".tmp_{date_clean}_{os.getpid()}.md"

            content = [
                f"# CHA-FICIAL 일별 시장 관측 요약 보고서 ({target_date_str})",
                "",
                f"- **보고서 생성 일시**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                f"- **대상 DB**: `{self.db_path}`",
                f"- **기준 일자 (KST)**: `{target_date_str}`",
                "",
                "---",
                "",
                "## 1. 당일 핵심 시장 관측 지표",
                "",
                "| 지표 | 실측 수치 | 비고 |",
                "| :--- | :---: | :--- |",
                f"| **실행된 관측 배치 수** | **{len(daily_batches)}회** | 당일 수집 시도 배치 |",
                f"| **정밀 파싱 수집 매물 수** | **{daily_parsed_count}대** | 아반떼 CN7 정밀 파싱 완료 |",
                f"| **당일 신규 발견 매물 (`FIRST_SEEN`)** | **{first_seen_count}대** | 시스템 최초 관측 실매물 |",
                f"| **당일 재관측 매물 (`RE_OBSERVED`)** | **{daily_reobserved_count}대** | 기존 관측 이력 보유 매물 |",
                f"| **당일 가격 인하 (`PRICE_DROP`)** | **{len(price_drop_events)}건** | 실제 가격 하향 조정 포착 |",
                f"| **총 가격 인하 누적액** | **{total_price_drop_krw:,}원** | 당일 인하 총액 |",
                f"| **당일 가격 인상 (`PRICE_INCREASE`)** | **{len(price_increase_events)}건** | 실제 가격 상향 조정 포착 |",
                f"| **총 가격 인상 누적액** | **{total_price_inc_krw:,}원** | 당일 인상 총액 |",
                "",
                "---",
                "",
                "## 2. 데이터베이스 누적 보존 현황",
                "",
                "| 테이블명 | 누적 총 레코드 수 | 설명 |",
                "| :--- | :---: | :--- |",
                f"| `listings` | **{total_listings}대** | 고유 실매물 영구 보존 레코드 |",
                f"| `listing_snapshots` | **{total_snapshots}건** | 시계열 불변 스냅샷 레코드 |",
                f"| `price_events` | **{total_events}건** | 가격 변동 및 상태 전이 이벤트 |",
                f"| `batch_audit_logs` | **{total_batches}회** | 수집 배치 감사 로그 |",
                "",
                "---",
                "",
                "## 3. 당일 실행 배치 상세 내역",
                "",
                "| 배치 식별자 | 관측 시각 (UTC) | 수집 건수 | 배치 감사 비고 |",
                "| :--- | :---: | :---: | :--- |",
            ]

            if daily_batches:
                for b in daily_batches:
                    time_str = b.processed_at.strftime("%H:%M:%S") if b.processed_at else "N/A"
                    notes_preview = (b.notes[:50] + "...") if b.notes and len(b.notes) > 50 else (b.notes or "N/A")
                    content.append(f"| `{b.batch_id}` | {time_str} | {b.record_count}건 | {notes_preview} |")
            else:
                content.append("| *당일 실행된 배치가 없습니다* | - | - | - |")

            content.extend([
                "",
                "---",
                "",
                "## 4. 당일 가격 변동 상세 목록",
                "",
                "| 매물 ID | 이벤트 유형 | 이전 가격 | 변경 가격 | 변동액 (KRW) | 변동률 (%) |",
                "| :---: | :---: | :---: | :---: | :---: | :---: |",
            ])

            if price_drop_events or price_increase_events:
                all_price_changes = sorted(price_drop_events + price_increase_events, key=lambda x: x.event_timestamp, reverse=True)
                for e in all_price_changes:
                    prev_p = f"{e.previous_price_krw:,}원" if e.previous_price_krw else "0원"
                    new_p = f"{e.new_price_krw:,}원" if e.new_price_krw else "0원"
                    delta_p = f"{e.price_delta_krw:,}원"
                    pct = f"{e.price_delta_pct:.2f}%"
                    content.append(f"| `{e.source_listing_id}` | `{e.event_type}` | {prev_p} | {new_p} | **{delta_p}** | {pct} |")
            else:
                content.append("| *당일 가격 변동 이벤트가 없습니다* | - | - | - | - | - |")

            content.append("\n---\n*CHA-FICIAL AI Time-Series Market Watcher Engine*\n")

            full_text = "\n".join(content)

            # 원자적 파일 교체 (Atomic write via temp file)
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(full_text)
            temp_file.replace(report_file)

            print(f"[+] 일별 시장 요약 보고서 원자적 생성 완료: {report_file}")
            return report_file
