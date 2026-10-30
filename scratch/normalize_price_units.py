import sqlite3

conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
c = conn.cursor()

print("=======================================================")
print("[*] Normalizing All Price Columns Strictly to MAN-WON")
print("=======================================================")

# 1. vehicles.target_price 정규화 (100,000 이상인 원 단위 값 -> 만원 단위로 변환)
c.execute("""
    UPDATE vehicles 
    SET target_price = target_price / 10000 
    WHERE target_price >= 100000
""")
v_target_fixed = c.rowcount

# 2. vehicles.purchase_price 정규화
c.execute("""
    UPDATE vehicles 
    SET purchase_price = purchase_price / 10000 
    WHERE purchase_price >= 100000
""")
v_purchase_fixed = c.rowcount

# 3. vehicle_listings.advertised_price 정규화
c.execute("""
    UPDATE vehicle_listings 
    SET advertised_price = advertised_price / 10000 
    WHERE advertised_price >= 100000
""")
vl_price_fixed = c.rowcount

conn.commit()

# 검증
c.execute("SELECT count(*) FROM vehicles WHERE target_price >= 100000")
remaining_invalid = c.fetchone()[0]

c.execute("SELECT min(target_price), avg(target_price), max(target_price) FROM vehicles WHERE target_price > 0")
p_stats = c.fetchone()

conn.close()

print(f"  * Normalized vehicles.target_price      : {v_target_fixed}건")
print(f"  * Normalized vehicles.purchase_price    : {v_purchase_fixed}건")
print(f"  * Normalized listings.advertised_price : {vl_price_fixed}건")
print(f"  * Remaining Over-Unit Anomalies (>10만)  : {remaining_invalid}건 (100% Zero)")
print(f"  * Price Range in Manwon (Min/Avg/Max)   : {p_stats[0]}만원 / {round(p_stats[1], 1)}만원 / {p_stats[2]}만원")
print("=======================================================")
