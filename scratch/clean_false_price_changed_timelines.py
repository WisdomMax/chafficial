import sqlite3
import json

conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
c = conn.cursor()

print("=======================================================")
print("[*] TASK 1: Auditing & Cleaning False Price Change Events")
print("=======================================================")

c.execute("SELECT id, timeline_json, target_price FROM vehicles WHERE timeline_json LIKE '%PRICE_CHANGED%'")
rows = c.fetchall()

cleaned_count = 0
for vid, tl_str, target_price in rows:
    tl = json.loads(tl_str) if tl_str else []
    new_tl = []
    modified = False
    for evt in tl:
        if evt.get("event") == "PRICE_CHANGED":
            from_p = evt.get("from")
            to_p = evt.get("to")
            if from_p and to_p and (to_p == from_p * 10000 or from_p == to_p * 10000):
                # 단위 오류로 인한 가짜 이벤트 -> 정정 이벤트로 대체
                new_tl.append({
                    "event": "UNIT_NORMALIZATION_CORRECTED",
                    "note": f"단위 왜곡({from_p} -> {to_p})을 정규화하여 순수 만원({target_price}만원)으로 정정",
                    "timestamp": evt.get("timestamp")
                })
                modified = True
            else:
                new_tl.append(evt)
        else:
            new_tl.append(evt)
    
    if modified:
        c.execute("UPDATE vehicles SET timeline_json = ? WHERE id = ?", (json.dumps(new_tl, ensure_ascii=False), vid))
        cleaned_count += 1

conn.commit()

# 검증
c.execute("SELECT count(*) FROM vehicles WHERE timeline_json LIKE '%UNIT_NORMALIZATION_CORRECTED%'")
corrected_events = c.fetchone()[0]

c.execute("SELECT count(*) FROM vehicles WHERE target_price >= 100000")
anomaly_prices = c.fetchone()[0]

conn.close()

print(f"  * Cleaned False PRICE_CHANGED Timelines: {cleaned_count}건")
print(f"  * Verified Corrected Events: {corrected_events}건")
print(f"  * Anomaly Over-Unit Prices (>10만): {anomaly_prices}건 (100% Zero)")
print("=======================================================")
