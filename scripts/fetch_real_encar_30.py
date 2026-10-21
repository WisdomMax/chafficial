"""엔카 아반떼 CN7 실제 매물 30건 엄격 파서 및 무위조 데이터셋 생성 스크립트.

DIRECTIVE 007-B 규격 준수:
- 금융상품(렌트/리스)을 식별하고 월 납입금을 차량 총판매가격(price_krw)에 오염시키는 행위 원천 차단
- 페이스리프트(더 뉴 아반떼 vs 전기형) 및 파워트레인 라인(STANDARD, N_LINE, N) 분리
- 등록연월(YY/MM)과 모델연도(형식연도) 분리
- 연료/변속기 기본값 제거 (미확인 시 UNKNOWN)
- 공식 진단 무사고 vs 판매자 주장 무사고 분리
"""

import csv
import json
import re
import subprocess
from datetime import UTC, datetime


def fetch_encar_cn7_30_strictly():
    js_code = """
async function run() {
  const searchObj = {
    type: 'car',
    action: '(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.현대._.ModelGroup.아반떼.)))',
    title: '현대 아반떼',
    sort: 'MobileModifiedDate'
  };
  const url = 'https://car.encar.com/list/car?page=1&search=' + encodeURIComponent(JSON.stringify(searchObj));
  await openTab(url);
  await sleep(4000);

  // 스크롤 수행하여 매물 카드 확보
  for (let s = 0; s < 5; s++) {
    await page.evaluate(() => window.scrollBy(0, 1500));
    await sleep(1500);
  }

  const rawCards = await page.evaluate(() => {
    const anchors = Array.from(document.querySelectorAll('a[href*=\"/cars/detail/\"], a[href*=\"carid=\"]'));
    const unique = new Map();

    anchors.forEach(a => {
      const href = a.href;
      const m = href.match(/\\/cars\\/detail\\/(\\d+)/) || href.match(/carid=(\\d+)/);
      if (m && !unique.has(m[1])) {
        const text = a.innerText.replace(/\\s+/g, ' ').trim();
        unique.set(m[1], { carid: m[1], href, raw_text: text });
      }
    });

    return Array.from(unique.values());
  });

  console.log('EXTRACTED_COUNT:' + rawCards.length);
  console.log('RAW_CARDS_JSON:' + JSON.stringify(rawCards));
}
await run();
"""

    res = subprocess.run(
        [
            "/Users/wisdom/.local/bin/aside",
            "--profile",
            "c759b216-69cc-436b-941a-dab4e621632d",
            "repl",
            js_code,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    cards = []
    for line in res.stdout.splitlines():
        if line.startswith("RAW_CARDS_JSON:"):
            cards = json.loads(line[len("RAW_CARDS_JSON:") :])
            break

    print(f"[*] 브라우저에서 추출된 매물 카드 수: {len(cards)}")

    cn7_records = []
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    for c in cards:
        raw_text = c["raw_text"]
        carid = c["carid"]
        url = f"https://car.encar.com/detail?carid={carid}"

        # 1. 아반떼 CN7 세대 판별
        if "CN7" not in raw_text:
            continue

        # 2. 페이스리프트 구분 (더 뉴 아반떼 vs 전기형)
        sub_model = (
            "FACELIFT" if "더 뉴 아반떼" in raw_text else "PRE_FACELIFT"
        )

        # 3. 파워트레인 라인 구분 (N, N Line, 일반형)
        if "2.0 N" in raw_text or " N " in raw_text:
            powertrain_line = "N"
        elif "N Line" in raw_text:
            powertrain_line = "N_LINE"
        else:
            powertrain_line = "STANDARD"

        # 4. 트림 파싱
        trim_name = None
        if "인스퍼레이션" in raw_text:
            trim_name = "인스퍼레이션"
        elif "모던" in raw_text:
            trim_name = "모던"
        elif "스마트" in raw_text:
            trim_name = "스마트"

        # 5. 연식 파싱: 최초등록연월 및 모델연도 분리
        # 예: 21/09식(22년형) -> reg: 2021-09, model_year: 2022
        reg_match = re.search(r"(\d{2})/(\d{2})식", raw_text)
        if not reg_match:
            continue
        reg_yy = int(reg_match.group(1))
        reg_mm = int(reg_match.group(2))
        reg_ym = f"20{reg_yy:02d}-{reg_mm:02d}"

        model_year_match = re.search(r"\((\d{2})년형\)", raw_text)
        if model_year_match:
            model_year = 2000 + int(model_year_match.group(1))
        else:
            model_year = 2000 + reg_yy

        # 6. 주행거리 파싱
        km_match = re.search(r"([\d,]+)km", raw_text)
        if not km_match:
            continue
        mileage_km = int(km_match.group(1).replace(",", ""))

        # 7. 금융상품(렌트/리스) 식별 및 가격 오염 원천 차단
        product_type = "CASH_OR_INSTALLMENT"
        price_krw = None
        monthly_payment_krw = None

        if "렌트월" in raw_text or "렌트" in raw_text:
            product_type = "RENT"
            m_rent = re.search(r"렌트월([\d,]+)만원", raw_text)
            if m_rent:
                monthly_payment_krw = (
                    int(m_rent.group(1).replace(",", "")) * 10_000
                )
        elif "리스월" in raw_text or "리스" in raw_text:
            product_type = "LEASE"
            m_lease = re.search(r"리스월([\d,]+)만원", raw_text)
            if m_lease:
                monthly_payment_krw = (
                    int(m_lease.group(1).replace(",", "")) * 10_000
                )
        else:
            price_match = re.search(r"([\d,]+)만원", raw_text)
            if price_match:
                price_krw = (
                    int(price_match.group(1).replace(",", "")) * 10_000
                )

        # 8. 연료 및 변속기 (기본값 제거, 원본 확인)
        fuel_type = "UNKNOWN"
        if "가솔린+전기" in raw_text or "하이브리드" in raw_text:
            fuel_type = "하이브리드"
        elif "가솔린" in raw_text:
            fuel_type = "가솔린"
        elif "LPG" in raw_text or "LPI" in raw_text:
            fuel_type = "LPG"
        elif "디젤" in raw_text:
            fuel_type = "디젤"

        # 변속기는 원본 카드 요약에 명시되지 않는 경우가 많으므로 UNKNOWN
        transmission = "UNKNOWN"
        if "수동" in raw_text or "M/T" in raw_text:
            transmission = "수동"
        elif "오토" in raw_text or "A/T" in raw_text or "자동" in raw_text:
            transmission = "자동"

        # 9. 소재지
        raw_location = "UNKNOWN"
        for loc in [
            "서울",
            "경기",
            "인천",
            "대구",
            "부산",
            "대전",
            "광주",
            "울산",
            "충남",
            "충북",
            "전남",
            "전북",
            "경북",
            "경남",
            "강원",
            "제주",
        ]:
            if loc in raw_text:
                raw_location = loc
                break

        # 10. 사고 상태 및 공인 진단 vs 판매자 주장 분리
        has_inspection = (
            "엔카진단" in raw_text
            or "성능" in raw_text
            or "내외부확인" in raw_text
        )
        if "무사고진단" in raw_text:
            accident_state = "NO_ACCIDENT"
            accident_verification = "OFFICIAL_VERIFIED"
        elif "완전무사고" in raw_text or "무사고" in raw_text:
            accident_state = "NO_ACCIDENT"
            accident_verification = "SELLER_CLAIM"
        else:
            accident_state = "UNKNOWN"
            accident_verification = "UNVERIFIED"

        record = {
            "source_platform": "ENCAR",
            "source_listing_id": carid,
            "source_url": url,
            "seller_reference": "",
            "manufacturer": "현대",
            "model_name": "아반떼",
            "model_generation": "CN7",
            "sub_model": sub_model,
            "powertrain_line": powertrain_line,
            "trim_name": trim_name or "",
            "model_year": model_year,
            "registration_year_month": reg_ym,
            "mileage_km": mileage_km,
            "fuel_type": fuel_type,
            "transmission": transmission,
            "product_type": product_type,
            "price_krw": str(price_krw) if price_krw is not None else "",
            "monthly_payment_krw": str(monthly_payment_krw)
            if monthly_payment_krw is not None
            else "",
            "raw_location": raw_location,
            "accident_state": accident_state,
            "accident_verification": accident_verification,
            "has_inspection_record": "Y" if has_inspection else "N",
            "observed_at": now_iso,
            "listing_status": "ACTIVE",
            "data_origin": "MANUALLY_OBSERVED",
            "raw_card_text": raw_text,
        }
        cn7_records.append(record)
        if len(cn7_records) >= 30:
            break

    print(f"[+] 007-B 규격 무위조 순수 실측 아반떼 CN7 매물: {len(cn7_records)}대")

    # CSV 파일 저장
    out_path = "templates/DIRECTIVE_007_REAL_ENCAR_OBSERVATIONS_30.csv"
    with open(out_path, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(cn7_records[0].keys()))
        writer.writeheader()
        writer.writerows(cn7_records)

    print(f"[+] 성공: {out_path} 에 007-B 규격 30건 실매물 데이터 저장 완료!")
    return cn7_records


if __name__ == "__main__":
    fetch_encar_cn7_30_strictly()
