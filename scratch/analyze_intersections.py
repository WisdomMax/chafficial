import json

# 1. 장한평 1,764대 로드
with open("data/carmanager_raw/janghanpyeong_full_collection.json", "r", encoding="utf-8") as f:
    jhp_data = json.load(f)
jhp_cars = jhp_data["cars"]
print(f"Total Janghanpyeong Market Cars: {len(jhp_cars)}")

# 단지별 분포 분석
danjis = {}
shops = {}
dealers = {}
for c in jhp_cars:
    d = c.get("danji", "Unknown")
    s = c.get("shop", "Unknown")
    dl = c.get("dealer", "Unknown")
    danjis[d] = danjis.get(d, 0) + 1
    shops[s] = shops.get(s, 0) + 1
    dealers[dl] = dealers.get(dl, 0) + 1

print("\n--- DANJI DISTRIBUTION (장안모터프라자 포함 여부 실측) ---")
for d, cnt in sorted(danjis.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  - {d}: {cnt}대")

print("\n--- TOP 10 SHOPS IN JANGHANPYEONG ---")
for s, cnt in sorted(shops.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  - {s}: {cnt}대")

# 2. 우리 상사 74대 로드
with open("data/carmanager_raw/myshop_parsed_cars.json", "r", encoding="utf-8") as f:
    myshop_cars = json.load(f)
print(f"\nTotal MyShop Parsed Sample: {len(myshop_cars)}")

# 3. 내 개인 13대 로드
with open("scratch/carmanager_inspect/my_13_cleaned_cars.json", "r", encoding="utf-8") as f:
    my_13 = json.load(f)
print(f"Total My Personal Cars: {len(my_13)}")

# 교집합 대조 (plate_tail 또는 plate 기준)
jhp_plate_tails = {c["plate_tail"]: c for c in jhp_cars if c["plate_tail"]}
myshop_plate_tails = {c["plate"][-4:]: c for c in myshop_cars if len(c["plate"]) >= 4}
my13_plate_tails = {c["plate"][-4:]: c for c in my_13 if len(c["plate"]) >= 4}

print(f"\n--- INTERSECTION AUDIT ---")
common_my13_in_myshop = [pt for pt in my13_plate_tails if pt in myshop_plate_tails]
print(f"1. 개인 13대 중 상사 74대(파싱 표본)에 존재하는 차량: {len(common_my13_in_myshop)}대 -> {common_my13_in_myshop}")

common_myshop_in_jhp = [pt for pt in myshop_plate_tails if pt in jhp_plate_tails]
print(f"2. 상사 74대 중 장한평 1,764대 시장에 광고 등록된 차량: {len(common_myshop_in_jhp)}대 -> {common_myshop_in_jhp}")

common_my13_in_jhp = [pt for pt in my13_plate_tails if pt in jhp_plate_tails]
print(f"3. 개인 13대 중 장한평 1,764대 시장에 광고 등록된 차량: {len(common_my13_in_jhp)}대 -> {common_my13_in_jhp}")
