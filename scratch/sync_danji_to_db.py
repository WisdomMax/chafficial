import json
import sqlite3

def sync_danji_to_listings():
    conn = sqlite3.connect('data/chamart/chamart_platform_demo.db')
    c = conn.cursor()
    
    with open('data/carmanager_raw/janghanpyeong_full_collection.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    cars = data.get('cars', [])
    print(f"Loaded {len(cars)} cars from collection.")
    
    updated_count = 0
    for car in cars:
        encarno = car.get('encarno')
        danji = car.get('danji')
        shop = car.get('shop')
        dealer = car.get('dealer')
        phone = car.get('phone')
        
        # listing_id가 encarno이거나 listing_url에 encarno가 포함된 경우 매칭
        c.execute("""
            UPDATE vehicle_listings
            SET raw_seller_location = ?,
                raw_seller_name = coalesce(raw_seller_name, ?),
                observation_notes = coalesce(observation_notes, '') || ' [danji:' || ? || ', dealer:' || ? || ']'
            WHERE platform = 'CARMANAGER' 
              AND (listing_id = ? OR listing_url LIKE '%' || ? || '%')
        """, (danji, shop, danji, dealer or '', encarno, encarno))
        
        if c.rowcount > 0:
            updated_count += c.rowcount
            
    conn.commit()
    print(f"Updated {updated_count} vehicle_listings with danji info.")
    
    # 확인 쿼리
    c.execute("""
        SELECT raw_seller_location, count(*) 
        FROM vehicle_listings 
        WHERE platform = 'CARMANAGER' 
        GROUP BY raw_seller_location
    """)
    print("--- Updated raw_seller_location distribution in DB ---")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]}건")
        
    conn.close()

if __name__ == '__main__':
    sync_danji_to_listings()
