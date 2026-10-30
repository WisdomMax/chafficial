import sqlite3

conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
c = conn.cursor()

print("[*] Reconciling Sangsa and Market Vehicle Ownership...")

# 타 상사 명의인데 listing_ownership_type = 'OWNED'로 잘못 잡혀 있던 매물 9대를 MARKET_JANGHANPYEONG으로 정정
c.execute("""
    UPDATE vehicles 
    SET listing_ownership_type = 'MARKET_JANGHANPYEONG', ownership_type = 'EXTERNAL'
    WHERE id IN (
        SELECT v.id FROM vehicles v
        JOIN vehicle_listings vl ON v.id = vl.vehicle_id
        WHERE v.listing_ownership_type = 'OWNED'
          AND (vl.raw_seller_name IN ('(주)조은오토', '(주)픽카소', '(주)한길유씨에스(세트)', '(주)달모터스', '(주)자동차친구')
               OR (v.ownership_type = 'MARKET_OBSERVED' AND vl.raw_seller_name IS NULL))
    )
""")
updated_count = c.rowcount
print(f"[+] Reclassified {updated_count} market cars from OWNED to MARKET_JANGHANPYEONG")

conn.commit()

# 정정 후 재집계
c.execute("""
    SELECT count(*) FROM vehicles v
    WHERE v.listing_ownership_type = 'OWNED'
""")
new_owned_total = c.fetchone()[0]

c.execute("""
    SELECT count(*) FROM vehicles v
    JOIN vehicle_listings vl ON v.id = vl.vehicle_id
    WHERE vl.raw_seller_name LIKE '%더쿨모터스%'
""")
thecool_in_db = c.fetchone()[0]

c.execute("""
    SELECT count(*) FROM vehicles v
    WHERE v.listing_ownership_type = 'MARKET_JANGHANPYEONG'
""")
market_total = c.fetchone()[0]

conn.close()

print(f"  * The Cool Motors Genuine Cars in DB: {thecool_in_db}대")
print(f"  * Total Pure OWNED/INTERNAL in DB   : {new_owned_total}대")
print(f"  * Total Market JHP Cars in DB       : {market_total}대")
