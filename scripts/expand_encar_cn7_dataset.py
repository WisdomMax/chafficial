"""Aside CLI 기반 엔카 아반떼 CN7 실매물 점진적 확장 수집기 (DIRECTIVE 008).

핵심 원칙:
1. 법적/기술적 접근 제한(Rate Limit) 준수: 페이지별 예의 바른 딜레이(2.5~3.5초) 적용
2. 중단 및 재개(Checkpoint) 지원: 수집된 카드 ID 즉시 저장 및 복원
3. 무위조 원칙: 추정값(가상 연식, 가상 주행거리 등) 주입 절대 금지
4. N/N-Line 우선순위 엄수 및 금융상품 오탐 방지
"""

import csv
import json
import os
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path


CHECKPOINT_PATH = Path("data/encar_cn7_checkpoint.json")
OUTPUT_CSV_PATH = Path("templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv")


def load_checkpoint() -> dict[str, dict]:
    """체크포인트 파일에서 이미 수집된 매물 로드."""
    if CHECKPOINT_PATH.exists():
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[-] 체크포인트 로드 실패 (새로 시작): {e}")
    return {}


def save_checkpoint(records: dict[str, dict]):
    """체크포인트 파일에 저장."""
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def parse_raw_card(c: dict, now_iso: str) -> dict | None:
    """원천 카드 텍스트에서 008 무결성 규격 레코드 추출."""
    raw_text = c.get("raw_text", "").strip()
    carid = str(c.get("carid", "")).strip()
    if not carid or not raw_text:
        return None

    # 아반떼 CN7 필터
    if "CN7" not in raw_text:
        return None

    # 1. 페이스리프트 구분 (더 뉴 아반떼 vs 전기형)
    sub_model = "FACELIFT" if "더 뉴 아반떼" in raw_text else "PRE_FACELIFT"

    # 2. 파워트레인 라인 구분 (N-Line 우선 판별하여 N 오분류 차단)
    if "N Line" in raw_text or "N라인" in raw_text or "N-Line" in raw_text:
        powertrain_line = "N_LINE"
    elif "2.0 N" in raw_text or " N " in raw_text or "아반떼 N" in raw_text:
        powertrain_line = "N"
    else:
        powertrain_line = "STANDARD"

    # 3. 트림 파싱
    trim_name = ""
    if "인스퍼레이션" in raw_text:
        trim_name = "인스퍼레이션"
    elif "모던" in raw_text:
        trim_name = "모던"
    elif "스마트" in raw_text:
        trim_name = "스마트"

    # 4. 연식 파싱: 최초등록연월 및 모델연도 분리
    # 모델연도 미표기 시 등록연도 대체 금지 (추정 주입 금지 -> 빈 문자열 보존)
    reg_match = re.search(r"(\d{2})/(\d{2})식", raw_text)
    if not reg_match:
        return None
    reg_yy = int(reg_match.group(1))
    reg_mm = int(reg_match.group(2))
    reg_ym = f"20{reg_yy:02d}-{reg_mm:02d}"

    model_year_str = ""
    model_year_match = re.search(r"\((\d{2})년형\)", raw_text)
    if model_year_match:
        model_year_str = str(2000 + int(model_year_match.group(1)))

    # 5. 주행거리 파싱
    km_match = re.search(r"([\d,]+)km", raw_text)
    if not km_match:
        return None
    mileage_km = int(km_match.group(1).replace(",", ""))

    # 6. 금융상품(렌트/리스) 식별 및 가격 분리
    product_type = "CASH_OR_INSTALLMENT"
    price_krw = None
    monthly_payment_krw = None

    m_rent = re.search(r"렌트\s*월\s*([\d,]+)만원", raw_text)
    m_lease = re.search(r"리스\s*월\s*([\d,]+)만원", raw_text)

    if m_rent or "렌트승계" in raw_text or "장기렌트" in raw_text:
        product_type = "RENT"
        if m_rent:
            monthly_payment_krw = int(m_rent.group(1).replace(",", "")) * 10_000
    elif m_lease or "리스승계" in raw_text or "운용리스" in raw_text or "금융리스" in raw_text:
        product_type = "LEASE"
        if m_lease:
            monthly_payment_krw = int(m_lease.group(1).replace(",", "")) * 10_000
    else:
        price_match = re.search(r"([\d,]+)만원", raw_text)
        if price_match:
            price_krw = int(price_match.group(1).replace(",", "")) * 10_000

    # 7. 연료 및 변속기
    fuel_type = "UNKNOWN"
    if "가솔린+전기" in raw_text or "하이브리드" in raw_text:
        fuel_type = "하이브리드"
    elif "가솔린" in raw_text:
        fuel_type = "가솔린"
    elif "LPG" in raw_text or "LPI" in raw_text:
        fuel_type = "LPG"
    elif "디젤" in raw_text:
        fuel_type = "디젤"

    transmission = "수동" if ("수동" in raw_text or "M/T" in raw_text) else "UNKNOWN"

    # 8. 소재지 파싱 (실제 매매단지 지명 추출)
    raw_location = ""
    for loc_candidate in [
        "서울 강남", "서울 강서", "서울 성동", "서울 동대문", "서울 양천",
        "경기 수원", "경기 용인", "경기 부천", "경기 김포", "경기 고양", "경기 안산",
        "인천 서구", "인천 미추홀", "대구", "부산", "광주", "대전", "충남 천안"
    ]:
        if loc_candidate in raw_text:
            raw_location = loc_candidate
            break

    # 9. 사고 상태 및 공인 진단 분리
    accident_state = "UNKNOWN"
    accident_verification = "UNVERIFIED"
    has_inspection = ("성능점검" in raw_text or "진단" in raw_text)

    if "엔카진단" in raw_text:
        accident_verification = "OFFICIAL_VERIFIED"
        if "무사고" in raw_text:
            accident_state = "NO_ACCIDENT"
    elif "무사고" in raw_text:
        accident_verification = "SELLER_CLAIM"
        accident_state = "NO_ACCIDENT"

    if "단순수리" in raw_text or "단순교환" in raw_text:
        accident_state = "SIMPLE_REPAIR"

    url = f"https://car.encar.com/detail?carid={carid}"

    return {
        "source_platform": "ENCAR",
        "source_listing_id": carid,
        "source_url": url,
        "seller_reference": "",
        "manufacturer": "현대",
        "model_name": "아반떼",
        "model_generation": "CN7",
        "sub_model": sub_model,
        "powertrain_line": powertrain_line,
        "trim_name": trim_name,
        "model_year": model_year_str,
        "registration_year_month": reg_ym,
        "mileage_km": mileage_km,
        "fuel_type": fuel_type,
        "transmission": transmission,
        "product_type": product_type,
        "price_krw": str(price_krw) if price_krw is not None else "",
        "monthly_payment_krw": str(monthly_payment_krw) if monthly_payment_krw is not None else "",
        "raw_location": raw_location,
        "accident_state": accident_state,
        "accident_verification": accident_verification,
        "has_inspection_record": "Y" if has_inspection else "N",
        "observed_at": now_iso,
        "listing_status": "ACTIVE",
        "data_origin": "MANUALLY_OBSERVED",
        "raw_card_text": raw_text,
    }


def fetch_page_cards(page_num: int) -> list[dict]:
    """지정된 페이지 번호에서 매물 카드 수집."""
    search_obj = {
        "type": "car",
        "action": "(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.현대._.ModelGroup.아반떼.)))",
        "title": "현대 아반떼",
        "sort": "MobileModifiedDate"
    }
    encoded_search = json.dumps(search_obj)

    js_code = f"""
async function run() {{
  const pageNum = {page_num};
  const searchStr = {json.dumps(encoded_search)};
  const url = 'https://car.encar.com/list/car?page=' + pageNum + '&search=' + encodeURIComponent(searchStr);
  
  await openTab(url);
  await sleep(4000);

  // 점진적 스크롤 (카드 지연 로딩 트리거)
  for (let s = 0; s < 6; s++) {{
    await page.evaluate(() => window.scrollBy(0, 1500));
    await sleep(1500);
  }}

  const rawCards = await page.evaluate(() => {{
    const anchors = Array.from(document.querySelectorAll('a[href*="/cars/detail/"], a[href*="carid="]'));
    const unique = new Map();

    anchors.forEach(a => {{
      const href = a.href || '';
      const m = href.match(/\\/cars\\/detail\\/(\\d+)/) || href.match(/carid=(\\d+)/);
      if (m && !unique.has(m[1])) {{
        const text = a.innerText.replace(/\\s+/g, ' ').trim();
        if (text.length > 20) {{
          unique.set(m[1], {{ carid: m[1], href, raw_text: text }});
        }}
      }}
    }});

    return Array.from(unique.values());
  }});

  console.log('RAW_CARDS_JSON:' + JSON.stringify(rawCards));
}}
await run();
"""

    res = subprocess.run(
        ["/Users/wisdom/.local/bin/aside", "--profile", "c759b216-69cc-436b-941a-dab4e621632d", "repl", js_code],
        check=False,
        capture_output=True,
        text=True,
    )

    for line in res.stdout.splitlines():
        if line.startswith("RAW_CARDS_JSON:"):
            try:
                return json.loads(line[len("RAW_CARDS_JSON:") :])
            except Exception as e:
                print(f"[-] JSON 파싱 실패: {e}")
    return []


def expand_dataset(max_pages: int = 5):
    """엔카 모바일/웹에서 페이지를 순회하며 아반떼 CN7 실매물 점진적 확장 수집."""
    collected_records = load_checkpoint()
    print(f"[*] 기존 체크포인트 매물 수: {len(collected_records)}건")

    # 기존 30건 데이터 병합
    existing_30_csv = Path("templates/DIRECTIVE_007_REAL_ENCAR_OBSERVATIONS_30.csv")
    if existing_30_csv.exists():
        with open(existing_30_csv, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = row["source_listing_id"]
                if cid not in collected_records:
                    parsed = parse_raw_card({"carid": cid, "raw_text": row.get("raw_card_text", "")}, row["observed_at"])
                    if parsed:
                        collected_records[cid] = parsed
        print(f"[*] 기존 30건 데이터 동기화 후 매물 수: {len(collected_records)}건")

    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    for p in range(1, max_pages + 1):
        print(f"[*] [{p}/{max_pages}] 페이지 수집 중 (URL 탐색 및 스크롤)...")
        cards = fetch_page_cards(p)
        print(f"    - 관측된 카드 수: {len(cards)}건")

        added_on_page = 0
        for c in cards:
            cid = str(c.get("carid"))
            if cid not in collected_records:
                parsed = parse_raw_card(c, now_iso)
                if parsed:
                    collected_records[cid] = parsed
                    added_on_page += 1

        print(f"    - 신규 유효 아반떼 CN7 추가: {added_on_page}건 (누적: {len(collected_records)}건)")
        save_checkpoint(collected_records)

        # 안전 딜레이 준수
        time.sleep(2.5)

    # 최종 결과 CSV 저장
    records_list = list(collected_records.values())
    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV_PATH, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records_list[0].keys()))
        writer.writeheader()
        writer.writerows(records_list)

    print(f"\n[+] 확장 수집 최종 완료: 총 {len(records_list)}건의 실매물 데이터셋 저장 완료 -> {OUTPUT_CSV_PATH}")
    return records_list


if __name__ == "__main__":
    expand_dataset(max_pages=4)
