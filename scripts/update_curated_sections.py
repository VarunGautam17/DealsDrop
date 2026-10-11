import json

with open("data/deals.json", "r", encoding="utf-8") as f:
    data = json.load(f)

deals = data["deals"]

# 1. Q-Rated Picks (Editor's high-value, top products worth owning)
q_rated = []
priority_brands = ["sony", "apple", "samsung", "oneplus", "bose", "philips", "hp", "asus", "lg", "dell"]
for idx, d in enumerate(deals):
    title_l = d["title"].lower()
    if any(b in title_l for b in priority_brands) and d["price"] > 1000 and d["discount"] >= 20:
        q_rated.append(idx)
    elif d["loot_score"] >= 95 and d["price"] > 1000:
        q_rated.append(idx)

q_rated = sorted(list(set(q_rated)), key=lambda i: deals[i]["discount"], reverse=True)[:30]

# 2. Hot Drops (Big markdowns that just landed, discount >= 50%)
hot_drops = []
for idx, d in enumerate(deals):
    if d["discount"] >= 50 and d["price"] > 0:
        hot_drops.append(idx)
hot_drops = sorted(list(set(hot_drops)), key=lambda i: deals[i]["discount"], reverse=True)[:30]

# 3. Lowest Price Ever (Deepest cuts, discount >= 65%)
lowest_price = []
for idx, d in enumerate(deals):
    if d["discount"] >= 65 and d["price"] > 0:
        lowest_price.append(idx)
lowest_price = sorted(list(set(lowest_price)), key=lambda i: deals[i]["discount"], reverse=True)[:30]

# 4. Fastest Fingers First (GrabFast deals FIRST, then small-ticket loots under 3500)
explicit_grabfast = []
small_tickets = []

for idx, d in enumerate(deals):
    title_l = d["title"].lower()
    spec_l = (d.get("spec") or "").lower()
    # Explicit Grabfast / Fast / Grab in title or spec
    if any(k in title_l for k in ["grabfast", "grab fast", "grab", "fast :", "loot fast"]):
        explicit_grabfast.append(idx)
    elif 0 < d["price"] <= 3500 and d["discount"] >= 50:
        small_tickets.append(idx)

# Deduplicate
explicit_grabfast = list(set(explicit_grabfast))
small_tickets = [i for i in list(set(small_tickets)) if i not in explicit_grabfast]

# Sort small tickets by discount
small_tickets.sort(key=lambda i: deals[i]["discount"], reverse=True)

# Combine: all explicit Grabfast deals first, then small-ticket loots
fastest_fingers = explicit_grabfast + small_tickets[: (40 - len(explicit_grabfast))]

print(f"Updated Curated Counts:")
print(f"  Q-Rated: {len(q_rated)}")
print(f"  Hot Drops: {len(hot_drops)}")
print(f"  Lowest Price Ever: {len(lowest_price)}")
print(f"  Fastest Fingers First (Total: {len(fastest_fingers)}, Explicit GrabFast: {len(explicit_grabfast)})")

data["curated"] = {
    "q_rated": q_rated,
    "hot_drops": hot_drops,
    "lowest_price": lowest_price,
    "fastest_fingers": fastest_fingers
}

with open("data/deals.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

with open("data/deals_data.js", "w", encoding="utf-8") as f:
    f.write("window.DEALS_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")

print("Saved data/deals.json and data/deals_data.js successfully!")
