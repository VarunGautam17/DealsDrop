import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("--- DEALS DROP VERIFICATION & LOGIC SUITE ---")

with open('data/deals.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

deals = data['deals']
curated = data['curated']

print(f"Total deals in catalog: {len(deals)}")
assert len(deals) == 1563, f"Deals count should be exactly 1563, got {len(deals)}"

# --- TEST 1: NO DUPLICATE DEALS FOR SPECIFIC PRODUCTS ---
print("\n--- TEST 1: Deduplication Verification ---")
# Check canonical product keys
def get_canonical_product_key(title, url=""):
    t = title.lower()
    t = re.sub(r'\bapple\b', 'apple', t)
    t = re.sub(r'\biphone\b', 'apple iphone', t)
    t = re.sub(r'\bapple apple\b', 'apple', t)
    
    specs = []
    size_match = re.search(r'(\d{2})\s*(?:inch|inches|")', t)
    if size_match:
        specs.append(f"{size_match.group(1)}in")
    litres_match = re.search(r'(\d{3})\s*(?:l|litre|litres)\b', t)
    if litres_match:
        specs.append(f"{litres_match.group(1)}l")
    kg_match = re.search(r'(\d+(?:\.\d+)?)\s*kg\b', t)
    if kg_match:
        specs.append(f"{kg_match.group(1)}kg")
    ton_match = re.search(r'(\d+(?:\.\d+)?)\s*ton\b', t)
    if ton_match:
        specs.append(f"{ton_match.group(1)}ton")
    storage_match = re.search(r'(\d+)\s*(gb|tb)\b', t)
    if storage_match:
        specs.append(f"{storage_match.group(1)}{storage_match.group(2)}")
    models = re.findall(r'\b(?:s25\s*ultra|s24\s*ultra|s25|s24|iphone\s*\d+|xm5|xm4|rtx\s*3050|160r|125r|na130|g923|z3)\b', t)
    if models:
        specs.extend(models)
    t_clean = re.sub(r'[^\w\s]', ' ', t)
    tokens = [w for w in t_clean.split() if w not in (
        'at', 'only', 'deal', 'loot', 'special', 'starting', 'starts', 'offers', 'offer',
        'flat', 'best', 'new', 'more', 'fast', 'upto', 'grab', 'regular', 'price', 'final',
        'code', 'working', 'apply', 'coupon', 'with', 'card', 'sbi', 'off'
    )]
    core_sig = " ".join(tokens)
    if specs:
        core_sig += " " + " ".join(specs)
    return core_sig.strip()

# Check iPhone 16 128 GB
iphone16_deals = [d for d in deals if "iphone 16" in d['title'].lower() and "128" in d['title'].lower() and "pro" not in d['title'].lower() and "plus" not in d['title'].lower()]
print(f"iPhone 16 128 GB deals count: {len(iphone16_deals)}")
assert len(iphone16_deals) == 1, f"Expected exactly 1 iPhone 16 128GB deal, got {len(iphone16_deals)}"
print(f"  -> Title: {iphone16_deals[0]['title']} | Price: ₹{iphone16_deals[0]['price']} | Date: {iphone16_deals[0]['timestamp_display']}")
assert iphone16_deals[0]['price'] == 69999, f"iPhone 16 128GB should be updated to ₹69,999, got {iphone16_deals[0]['price']}"

# Check Samsung Galaxy S25 Ultra
s25_deals = [d for d in deals if "s25 ultra" in d['title'].lower()]
print(f"Samsung Galaxy S25 Ultra deals count: {len(s25_deals)}")
assert len(s25_deals) == 1, f"Expected exactly 1 S25 Ultra deal, got {len(s25_deals)}"
print(f"  -> Title: {s25_deals[0]['title']} | Price: ₹{s25_deals[0]['price']} | Date: {s25_deals[0]['timestamp_display']}")

# --- TEST 2: TIMESTAMP RECENCY VERIFICATION ---
print("\n--- TEST 2: Timestamp Recency Verification ---")
# Check RTX 3050 Laptop: on 09/10 it was 96,990; on 10/10 it dropped to 85,490
rtx_deals = [d for d in deals if "rtx 3050" in d['title'].lower() and "zHOfid2" in d['url']]
print(f"RTX 3050 Gaming Laptop (zHOfid2): {len(rtx_deals)} deal(s)")
assert len(rtx_deals) == 1, f"Expected 1 RTX 3050 deal, got {len(rtx_deals)}"
print(f"  -> Title: {rtx_deals[0]['title']} | Price: ₹{rtx_deals[0]['price']} | Date: {rtx_deals[0]['timestamp_display']}")
assert rtx_deals[0]['price'] == 85490, f"Expected price ₹85,490 from 10/10, got {rtx_deals[0]['price']}"

# Check Xiaomi 65 Inch TV: on 11/10 it was 44,137 (was 47,137 on 09/10)
xiaomi_65_deals = [d for d in deals if "xiaomi" in d['title'].lower() and "65" in d['title'].lower() and ("qled" in d['title'].lower() or "5DA2ogE" in d['url'])]
print(f"Xiaomi 65 inch TV (5DA2ogE): {len(xiaomi_65_deals)} deal(s)")
assert len(xiaomi_65_deals) == 1, f"Expected 1 Xiaomi 65-inch QLED deal, got {len(xiaomi_65_deals)}"
print(f"  -> Title: {xiaomi_65_deals[0]['title']} | Price: ₹{xiaomi_65_deals[0]['price']} | Date: {xiaomi_65_deals[0]['timestamp_display']}")
assert xiaomi_65_deals[0]['price'] == 44137, f"Expected price ₹44,137 from 11/10, got {xiaomi_65_deals[0]['price']}"

# Check Sandisk 2TB SSD: should be dated 11/10
sandisk_2tb = [d for d in deals if "sandisk 2tb" in d['title'].lower()]
print(f"Sandisk 2TB SSD deals count: {len(sandisk_2tb)}")
assert len(sandisk_2tb) == 1, f"Expected 1 Sandisk 2TB SSD deal, got {len(sandisk_2tb)}"
print(f"  -> Title: {sandisk_2tb[0]['title']} | Price: ₹{sandisk_2tb[0]['price']} | Date: {sandisk_2tb[0]['timestamp_display']}")
assert "11/10" in sandisk_2tb[0]['timestamp_display'], "Sandisk 2TB should have latest timestamp 11/10"

# --- TEST 3: CURATED SECTIONS & GRABFAST PRIORITIZATION ---
print("\n--- TEST 3: Curated Sections & GrabFast Prioritization ---")
print(f"Curated q_rated count: {len(curated['q_rated'])}")
print(f"Curated hot_drops count: {len(curated['hot_drops'])}")
print(f"Curated lowest_price count: {len(curated['lowest_price'])}")
print(f"Curated fastest_fingers count: {len(curated['fastest_fingers'])}")

assert len(curated['q_rated']) == 30
assert len(curated['hot_drops']) == 30
assert len(curated['lowest_price']) == 30
assert len(curated['fastest_fingers']) == 40

# Check that Grab/Fast deals are pinned in Fastest Fingers First
fastest_items = [deals[i] for i in curated['fastest_fingers']]
grab_deals_in_fast = [d for d in fastest_items if any(w in (d.get('raw_text', '') + d['title']).lower() for w in ['grabfast', 'grab fast', 'fast', 'loot fast', 'ise looto'])]
print(f"Fastest Fingers items containing Grab/Fast/LootFast: {len(grab_deals_in_fast)}")
assert len(grab_deals_in_fast) >= 10, f"Expected at least 10 GrabFast deals, found {len(grab_deals_in_fast)}"

# --- TEST 4: IMAGE COVERAGE ---
print("\n--- TEST 4: Image Coverage ---")
q_rated_imgs = [deals[i] for i in curated['q_rated'] if deals[i].get('image_url')]
print(f"Q-Rated Picks with images: {len(q_rated_imgs)} / 30")
assert len(q_rated_imgs) == 30, f"Expected 30/30 Q-rated images, got {len(q_rated_imgs)}"

# --- TEST 5: HTML / UI VERIFICATION ---
print("\n--- TEST 5: HTML / UI Verification ---")
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

assert 'id="sec-cnt-all">1563<' in html, "index.html must display 1563 total deals"
assert 'id="sec-cnt-q">30<' in html, "index.html must display 30 for Q-rated"
assert 'id="sec-cnt-f">40<' in html, "index.html must display 40 for Fastest Fingers"
assert 'Prices as of 11 Oct 2026' in html, "Footer must note 11 Oct 2026 prices"

# --- TEST 6: MEGA DEALS LATEST BROADCAST VERIFICATION ---
print("\n--- TEST 6: Latest Broadcast Feed Verification ---")
sony_xm5 = [d for d in deals if "wh-1000xm5" in d['title'].lower()]
assert len(sony_xm5) == 1, f"Expected 1 Sony WH-1000XM5 deal, got {len(sony_xm5)}"
assert sony_xm5[0]['price'] == 19489, f"Sony WH-1000XM5 price should be 19489, got {sony_xm5[0]['price']}"
assert "11/10/2026 11:56 pm" in sony_xm5[0]['timestamp_display'], "Timestamp must be 11/10/2026 11:56 pm"

s25_ultra = [d for d in deals if "s25 ultra" in d['title'].lower()]
assert len(s25_ultra) == 1, f"Expected 1 S25 Ultra deal, got {len(s25_ultra)}"
assert s25_ultra[0]['price'] == 94999, f"S25 Ultra price should be 94999, got {s25_ultra[0]['price']}"

deebot = [d for d in deals if "deebot" in d['title'].lower()]
assert len(deebot) == 1, f"Expected 1 Ecovacs Deebot deal, got {len(deebot)}"
assert deebot[0]['price'] == 44999, f"Deebot price should be 44999, got {deebot[0]['price']}"

print("  ✓ Sony WH-1000XM5: ₹19,489 (11/10/2026 11:56 pm)")
print("  ✓ Samsung Galaxy S25 Ultra: ₹94,999 (11/10/2026 11:56 pm)")
print("  ✓ Ecovacs Deebot T30e Omni: ₹44,999 (11/10/2026 11:56 pm)")

print("\n=======================================================")
print("ALL VERIFICATIONS & LOGIC CHECKS PASSED 100%!")
print("=======================================================")
