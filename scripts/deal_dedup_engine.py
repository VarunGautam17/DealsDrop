#!/usr/bin/env python3
"""
DealsDrop Recency-Aware Product Deduplication & Update Engine
Handles:
1. Parsing shopping genie.txt with accurate message timestamps.
2. Canonical product identity key extraction (Brand + Model + Storage/Size/Capacity).
3. Timestamp-based resolution: Latest deal timestamp wins for any product.
4. Harmonization with existing catalog (updating existing deals, removing duplicates, adding new deals).
5. Image preservation and enrichment.
6. Curated section recalculation with GrabFast prioritization.
"""

import json
import re
import os
import sys
from datetime import datetime
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIG & MAPS ---
CATEGORY_MAP = {
    "phone": {"name": "Mobile Phones", "icon": "📱"},
    "laptop": {"name": "Laptops & Tablets", "icon": "💻"},
    "audio": {"name": "Audio & Soundbars", "icon": "🎧"},
    "home": {"name": "TV & Appliances", "icon": "📺"},
    "life": {"name": "Lifestyle & Fashion", "icon": "👕"},
    "daily": {"name": "Daily Needs & Loots", "icon": "⚡"}
}

STORE_RULES = [
    (r"(?:fkrt\.cc|flipkart\.com)", "Flipkart", "Flipkart BBD", "flipkart"),
    (r"(?:bitli\.in|amazon\.in|amzn\.to)", "Amazon", "Amazon GIF", "amazon"),
    (r"(?:myntr\.it|myntra\.com)", "Myntra", "Myntra BFF", "myntra"),
    (r"(?:ajiio\.in|ajio\.com)", "Ajio", "Ajio All Stars", "ajio")
]

PHONE_KEYWORDS = [
    r"iphone", r"galaxy\s+s\d+", r"s25", r"s24", r"oneplus", r"pixel",
    r"realme", r"redmi", r"xiaomi", r"vivo", r"oppo", r"poco", r"motorola", r"moto\s+",
    r"iqoo", r"smartphone", r"mobile", r"infinix", r"lava", r"5g\s+phone", r"phone"
]

LAPTOP_KEYWORDS = [
    r"laptop", r"macbook", r"thinkpad", r"ideapad", r"vivobook", r"zenbook", r"omnibook",
    r"chromebook", r"ipad", r"tablet", r"tab\s+s", r"tab\s+a", r"surface", r"ryzen", r"intel\s+core",
    r"aspire", r"victus", r"loq", r"gaming\s+laptop", r"rtx\s+3050"
]

AUDIO_KEYWORDS = [
    r"earbuds", r"tws", r"headphone", r"soundbar", r"speaker", r"airpods", r"buds",
    r"wh-1000xm", r"wf-1000xm", r"bluetooth\s+speaker", r"anc", r"earphones", r"neckband",
    r"bullets\s+wireless", r"soundsystem"
]

HOME_KEYWORDS = [
    r"smart\s*tv", r"qled", r"oled", r"inch\s*tv", r"inches\s*tv", r"refrigerator", r"fridge", r"washing\s+machine",
    r"air\s*conditioner", r"\bac\b", r"inverter", r"chimney", r"microwave", r"air\s*fryer",
    r"mixer\s+grinder", r"purifier", r"geyser", r"water\s*heater", r"cooler", r"ceiling\s*fan",
    r"projector", r"monitor", r"vacuum", r"gas\s+stove", r"cooker", r"pressure\s+cooker",
    r"massage\s+gun", r"massager", r"recliner", r"sofa", r"wardrobe", r"bed", r"table",
    r"trimmer", r"toothbrush", r"air\s*purifier"
]

LIFESTYLE_KEYWORDS = [
    r"shirt", r"t-shirt", r"t\s*shirt", r"jeans", r"trouser", r"dress", r"kurta", r"shoes", r"sneakers",
    r"watch", r"analog", r"smartwatch", r"trolley", r"luggage", r"backpack", r"perfume",
    r"deodorant", r"jacket", r"sandal", r"mattress", r"mattres", r"gold", r"ring", r"pendant", r"blazer",
    r"crocs", r"hoddie", r"hoodie", r"wallet", r"suitcase", r"edp", r"bedsheet", r"clothing",
    r"bike", r"scooter", r"cycle", r"toy", r"lego", r"building\s+set", r"card\s+games"
]

url_pattern = re.compile(r'(https?://[^\s]+|(?:fkrt\.cc|bitli\.in|myntr\.it|ajiio\.in)/[^\s]+)')

def determine_category(text, store):
    text_lower = text.lower()
    for kw in AUDIO_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", text_lower):
            return "audio"
    for kw in LAPTOP_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", text_lower):
            return "laptop"
    for kw in PHONE_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", text_lower):
            return "phone"
    for kw in HOME_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", text_lower):
            return "home"
    for kw in LIFESTYLE_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", text_lower):
            return "life"
    if store in ("Myntra", "Ajio"):
        return "life"
    return "daily"

def get_store_info(url):
    for pattern, s_name, s_badge, s_code in STORE_RULES:
        if re.search(pattern, url, re.I):
            return s_name, s_badge, s_code
    return "Amazon", "Amazon GIF", "amazon"

def clean_title(title):
    t = re.sub(r"^(?:▪️|•|»|🥇|🔥|⚡|🔻|👉|💥|✨|\*|\s)+", "", title)
    t = re.sub(r"(?:▪️|•|»|🥇|🔥|⚡|🔻|👉|💥|✨|\*|\s)+$", "", t)
    t = re.sub(r"^loot(?:\s*deal)?(?:\s*fast)?(?:\s*:\s*)?", "", t, flags=re.I)
    t = re.sub(r"^\d+%\s*(?:off|OFF)\s*(?:on\s*)?[-:]?\s*", "", t, flags=re.I)
    t = re.sub(r"\[.*?coupon.*?\]", "", t, flags=re.I)
    t = re.sub(r"\(.*?coupon.*?\)", "", t, flags=re.I)
    t = re.sub(r"\s+at\s+₹?\s*[\d,]+(?:\s+only)?(?:\s*\(final\))?.*$", "", t, flags=re.I)
    t = re.sub(r"\s+@\s*₹?\s*[\d,]+.*$", "", t, flags=re.I)
    t = re.sub(r"\s+-\s+Starting\s+@?.*$", "", t, flags=re.I)
    t = re.sub(r"\s*\|\s*regular:?.*$", "", t, flags=re.I)
    return t.strip()

def extract_price(text):
    text_clean = re.sub(r"\b\d+\s*GB\b", "", text, flags=re.I)
    text_clean = re.sub(r"\b\d+\s*TB\b", "", text, flags=re.I)
    m = re.search(r"(?:at\s*₹?|@\s*₹?|₹|Rs\.?)\s*([\d,]{2,8})", text_clean, re.I)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except:
            pass
    m2 = re.search(r"\b(\d{3,6})\b", text_clean)
    if m2:
        try:
            v = int(m2.group(1))
            if 100 <= v <= 300000:
                return v
        except:
            pass
    return 0

def extract_discount(text):
    m = re.search(r"(\d{1,2})\s*%\s*(?:off|OFF|discount)", text)
    if m:
        return int(m.group(1))
    return 0

def extract_mrp(text, price):
    m = re.search(r"(?:regular(?:\s*price)?|reg(?:\s*price)?|mrp)\s*[:\-]?\s*₹?\s*(\d+)(k)?", text, re.I)
    if m:
        val = int(m.group(1))
        if m.group(2):
            val *= 1000
        if val > price:
            return val
    return 0

NOISE_WORDS = {
    'at', 'only', 'deal', 'loot', 'special', 'starting', 'starts', 'offers', 'offer',
    'flat', 'best', 'new', 'more', 'fast', 'upto', 'grab', 'regular', 'price', 'final',
    'code', 'working', 'apply', 'coupon', 'with', 'card', 'sbi', 'off',
    '5g', '4g', 'lte', 'ai', 'smartphone', 'smartphones', 'mobile', 'phone', 'phones',
    'unisex', 'men', 'mens', 'women', 'womens', 'original', 'originals', 'edition', 'series',
    'ram', 'ddr5', 'ddr4', 'rom', 'wifi', 'wi-fi', 'bluetooth'
}

# --- PRODUCT IDENTITY CANONICAL KEY GENERATOR ---
def get_canonical_product_key(title, url=""):
    """
    Generates a canonical signature for a product so that variations of the same product
    (e.g., 'Apple iPhone 16 128 GB' and 'iPhone 16 128 GB') map to the exact same key,
    while distinct models or sizes (e.g. 55 inch TV vs 65 inch TV) stay separate.
    """
    t = title.lower()
    
    # 1. Normalize brand prefixes
    t = re.sub(r'\bapple\b', 'apple', t)
    t = re.sub(r'\biphone\b', 'apple iphone', t)
    t = re.sub(r'\bapple apple\b', 'apple', t)
    
    # Strip RAM e.g. 12gb + or (12gb + 256gb)
    t = re.sub(r'\b\d+\s*gb\s*\+\s*', '', t)
    t = re.sub(r'\(\s*\d+\s*gb\s*[\+/]\s*(\d+\s*gb)\s*\)', r'\1', t)
    
    # Specific known flagship models
    if 's25 ultra' in t:
        return 'samsung galaxy s25 ultra'
    if 'iphone 16' in t and '128' in t and 'pro' not in t and 'plus' not in t:
        return 'apple iphone 16 128gb'
    if 'zenbook 14' in t:
        return 'asus zenbook 14'
    if 'g923' in t:
        return 'logitech g923 racing wheel'
    if 'xm5' in t and ('sony' in t or 'headphone' in t):
        return 'sony wh 1000xm5'
    if 'bullets wireless z3' in t or ('oneplus' in t and 'z3' in t):
        return 'oneplus bullets wireless z3'
    if 'air jordan 1 low' in t:
        return 'nike air jordan 1 low white'
    if 'everett brown watch' in t or ('fossil' in t and 'everett' in t):
        return 'fossil everett brown watch'
    if 'sandisk 2tb' in t:
        return 'sandisk 2tb portable ssd'
    if 'samsung 2tb' in t:
        return 'samsung 2tb portable ssd'
    if 'samsung 1tb' in t and 'ssd' in t:
        return 'samsung 1tb portable ssd'
    if 'native m1' in t:
        return 'native m1 water purifier'
    if 'xiaomi' in t and ('65' in t or '164 cm' in t):
        return 'xiaomi 65in 4k qled tv'
        
    # 2. Extract key product specs to preserve distinct models
    specs = []
    
    # Screen size
    size_match = re.search(r'(\d{2})\s*(?:inch|inches|")', t)
    if size_match:
        specs.append(f"{size_match.group(1)}in")
        
    # Capacity / Litres
    litres_match = re.search(r'(\d{3})\s*(?:l|litre|litres)\b', t)
    if litres_match:
        specs.append(f"{litres_match.group(1)}l")
        
    # Weight / Kg (washing machines, whey)
    kg_match = re.search(r'(\d+(?:\.\d+)?)\s*kg\b', t)
    if kg_match:
        specs.append(f"{kg_match.group(1)}kg")
        
    # Tonnage (ACs)
    ton_match = re.search(r'(\d+(?:\.\d+)?)\s*ton\b', t)
    if ton_match:
        specs.append(f"{ton_match.group(1)}ton")
        
    # Storage (128GB, 256GB, 1TB, 2TB)
    storage_match = re.search(r'(\d+)\s*(gb|tb)\b', t)
    if storage_match:
        specs.append(f"{storage_match.group(1)}{storage_match.group(2)}")
        
    # Model numbers like 160R, 125R, NA130, RTX 3050
    models = re.findall(r'\b(?:rtx\s*3050|160r|125r|na130)\b', t)
    if models:
        specs.extend(models)
        
    # Clean text
    t_clean = re.sub(r'[^\w\s]', ' ', t)
    tokens = [w for w in t_clean.split() if w not in NOISE_WORDS]
    
    core_sig = " ".join(tokens)
    if specs:
        core_sig += " " + " ".join(specs)
        
    return core_sig.strip()

def is_promo_slogan(text):
    t = text.lower().strip()
    slogans = [
        "lowest price", "lowest ever", "price drop", "best choice", "huge discount",
        "triple discount", "limited time", "order fast", "grab fast", "flash sale",
        "super loot", "gold loot", "last stock", "ise looto", "loot", "big saving",
        "top phone suggestions"
    ]
    return any(t.startswith(s) or t == s for s in slogans)

def parse_shopping_genie_file(filepath):
    """Parses all timestamped messages and returns a list of deal objects with datetime."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    msg_pattern = re.compile(r'\[(\d{1,2}/\d{1,2}),\s*(\d{1,2}:\d{2}(?:\s*[\u202f\s]?[ap]m)?)\]\s*([^:]+):\s*', re.I)
    matches = list(msg_pattern.finditer(text))

    deals = []
    for i in range(len(matches)):
        start_pos = matches[i].start()
        end_pos = matches[i+1].start() if i+1 < len(matches) else len(text)
        
        date_str = matches[i].group(1)
        time_str = matches[i].group(2).replace('\u202f', ' ').strip().lower()
        day, month = map(int, date_str.split('/'))
        dt = datetime.strptime(f"2026-{month:02d}-{day:02d} {time_str}", "%Y-%m-%d %I:%M %p")
        
        body = text[matches[i].end():end_pos].strip()
        lines = [l.strip() for l in body.split("\n") if l.strip()]
        links = url_pattern.findall(body)
        
        if not links:
            continue
            
        if len(links) == 1:
            u = links[0]
            store, s_badge, s_code = get_store_info(u)
            price = extract_price(body)
            discount = extract_discount(body)
            mrp = extract_mrp(body, price)
            
            # Spec
            spec_match = re.search(r"(?:-|\u2022|\*)\s*([^\n]+off[^\n]+(?:card|sbi|bank|coupon)[^\n]*)", body, re.I)
            spec = spec_match.group(1).strip() if spec_match else ""
            
            # Title
            title = ""
            for l in lines:
                if url_pattern.search(l):
                    continue
                if l.startswith("-") or l.startswith("•") or l.lower().startswith("apply") or l.lower().startswith("coupon"):
                    continue
                if "cashback coupon" in l.lower() or l.lower().startswith("flat") or l.lower().startswith("code :"):
                    continue
                cl = clean_title(l)
                if len(cl) >= 3 and not is_promo_slogan(cl):
                    title = cl
                    break
            if not title:
                for l in lines:
                    if not url_pattern.search(l):
                        cl = clean_title(l)
                        if len(cl) >= 3:
                            title = cl
                            break
            if not title:
                title = f"Sale Deal at ₹{price}" if price else "Festive Deal"
                
            cat = determine_category(f"{title} {body}", store)
            
            deals.append({
                "source": "chat",
                "dt": dt,
                "date_str": date_str,
                "time_str": time_str,
                "timestamp_display": f"{date_str}/2026 {time_str}",
                "title": title,
                "price": price,
                "discount": discount,
                "mrp": mrp,
                "spec": spec,
                "category": cat,
                "store": store,
                "store_code": s_code,
                "store_badge": s_badge,
                "url": u if u.startswith("http") else f"https://{u}",
                "raw_text": body,
                "is_starting_at": bool(re.search(r"(?:starting\s*@|starts\s*@|under\s*₹?|from\s*₹?)", body, re.I))
            })
        else:
            # Multi-link
            link_line_indices = []
            for idx, line in enumerate(lines):
                found = url_pattern.findall(line)
                if found:
                    link_line_indices.append((idx, found[0], line))
                    
            main_header = lines[0] if lines else ""
            overall_disc = extract_discount(body)
            
            for l_idx, (line_num, link_url, line_str) in enumerate(link_line_indices):
                if "collect" in line_str.lower() and "coupon" in line_str.lower():
                    continue
                if "more :" in line_str.lower() and l_idx == len(link_line_indices) - 1:
                    continue
                    
                prev_line_num = link_line_indices[l_idx-1][0] if l_idx > 0 else -1
                next_line_num = link_line_indices[l_idx+1][0] if l_idx+1 < len(link_line_indices) else len(lines)
                chunk_lines = lines[prev_line_num+1 : next_line_num]
                chunk_text = " \n ".join(chunk_lines)
                
                store, s_badge, s_code = get_store_info(link_url)
                price = extract_price(chunk_text)
                if price == 0 and extract_price(line_str) > 0:
                    price = extract_price(line_str)
                    
                disc = extract_discount(chunk_text) or overall_disc
                mrp = extract_mrp(chunk_text, price)
                
                title = ""
                for cl in chunk_lines:
                    if url_pattern.search(cl) and not re.search(r'[a-zA-Z]{3,}', cl.replace("https://", "").replace("http://", "")):
                        continue
                    cleaned = clean_title(cl)
                    cleaned = re.sub(r":\s*https?://.*$", "", cleaned)
                    cleaned = re.sub(r"\s+https?://.*$", "", cleaned)
                    if len(cleaned) >= 2 and not cleaned.lower().startswith("loot"):
                        title = cleaned
                        break
                
                if not title and re.search(r'[a-zA-Z]{3,}', line_str.replace("https://", "")):
                    title = clean_title(re.sub(r":\s*https?://.*$", "", line_str))
                    
                if "being human" in main_header.lower() and not "being human" in title.lower():
                    title = f"Being Human {title}"
                elif "levis" in main_header.lower() and not "levis" in title.lower():
                    title = f"Levis {title}"
                elif "ac deals" in main_header.lower():
                    if not "ac" in title.lower():
                        title = f"{title} 1.5 Ton 3 Star AC"
                elif "pigeon" in main_header.lower():
                    title = f"Pigeon Product at ₹{price}" if price else "Pigeon Products"
                elif "washing machine" in main_header.lower() and not "washing machine" in title.lower():
                    title = f"Washing Machine at ₹{price}"
                elif "mixer grinder" in main_header.lower() and not "mixer grinder" in title.lower():
                    title = f"{clean_title(main_header)} at ₹{price}"
                elif "mattres" in main_header.lower() and not "mattress" in title.lower():
                    title = f"Mattress at ₹{price}"
                elif "top phone suggestions" in main_header.lower():
                    title = f"Top Phone Suggestions {title}"
                    
                if not title:
                    title = clean_title(main_header)
                    if price:
                        title += f" at ₹{price}"
                        
                cat = determine_category(f"{title} {chunk_text} {main_header}", store)
                
                deals.append({
                    "source": "chat",
                    "dt": dt,
                    "date_str": date_str,
                    "time_str": time_str,
                    "timestamp_display": f"{date_str}/2026 {time_str}",
                    "title": title,
                    "price": price,
                    "discount": disc,
                    "mrp": mrp,
                    "spec": "",
                    "category": cat,
                    "store": store,
                    "store_code": s_code,
                    "store_badge": s_badge,
                    "url": link_url if link_url.startswith("http") else f"https://{link_url}",
                    "raw_text": chunk_text,
                    "is_starting_at": False
                })
    return deals

def parse_mega_deals_file(filepath):
    """Parses data/mega_deals.txt lines with 11 Oct 23:56 timestamp."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    dt = datetime(2026, 10, 11, 23, 56, 0)
    date_str = "11/10"
    time_str = "11:56 pm"
    timestamp_display = "11/10/2026 11:56 pm"
    
    url_pat = re.compile(r'(https?://[^\s]+|(?:fkrt\.cc|bitli\.in|myntr\.it|ajiio\.in)/[^\s]+)')
    deals = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        u_match = url_pat.search(line)
        if not u_match:
            continue
        url = u_match.group(1)
        
        prefix = re.sub(r'🔗\s*$', '', line[:u_match.start()].strip()).strip()
        emoji_m = re.match(r'^([^\w\s])\s*', prefix)
        emoji = emoji_m.group(1) if emoji_m else "🔥"
        content = prefix[emoji_m.end():] if emoji_m else prefix
        
        split_m = re.search(r'\s+[–\-—]\s*₹\s*([\d,]+)', content)
        if not split_m:
            continue
            
        title = content[:split_m.start()].strip()
        price = int(split_m.group(1).replace(",", ""))
        
        disc_m = re.search(r'\((\d+)%\s*OFF\)', content[split_m.end():], re.I)
        disc = int(disc_m.group(1)) if disc_m else 0
        
        store, s_badge, s_code = get_store_info(url)
        cat = determine_category(f"{title} {emoji}", store)
        mrp = extract_mrp("", price)
        if not mrp and disc > 0:
            mrp = int(round(price / (1.0 - (disc / 100.0))))
            
        deals.append({
            "source": "mega_deals",
            "dt": dt,
            "date_str": date_str,
            "time_str": time_str,
            "timestamp_display": timestamp_display,
            "title": title,
            "price": price,
            "discount": disc,
            "mrp": mrp,
            "spec": "",
            "category": cat,
            "store": store,
            "store_code": s_code,
            "store_badge": s_badge,
            "url": url if url.startswith("http") else f"https://{url}",
            "raw_text": line,
            "is_starting_at": False
        })
    return deals

def run_dedup_and_update():
    chat_file = "shopping genie.txt"
    mega_file = "data/mega_deals.txt"
    deals_file = "data/deals.json"
    
    print(f"Loading chat export: {chat_file}...")
    chat_deals_1 = parse_shopping_genie_file(chat_file)
    print(f"Loading mega deals broadcast: {mega_file}...")
    chat_deals_2 = parse_mega_deals_file(mega_file)
    
    chat_deals = chat_deals_1 + chat_deals_2
    print(f"Total extracted deals from feeds: {len(chat_deals)} ({len(chat_deals_1)} from chat, {len(chat_deals_2)} from mega deals).")
    
    print(f"Loading existing catalog: {deals_file}...")
    with open(deals_file, 'r', encoding='utf-8') as f:
        existing_data = json.load(f)
    existing_deals = existing_data.get('deals', [])
    print(f"Loaded {len(existing_deals)} existing catalog deals.")
    
    # Existing deals base timestamp: assume 2026-10-09 12:00:00 (older snapshot 8-10 Oct)
    # If existing deal index is higher, it's later in the older export
    base_old_dt = datetime(2026, 10, 8, 12, 0, 0)
    for idx, d in enumerate(existing_deals):
        d["dt"] = base_old_dt # Older than new chat updates
        d["source"] = "catalog"
        if not d.get("timestamp_display"):
            d["timestamp_display"] = "09/10/2026 12:00 pm"
            
    # Step 1: Dedup inside chat_deals by exact URL and canonical key using timestamp recency
    print("\n--- Resolving Recency within New Chat Deals ---")
    chat_by_url = defaultdict(list)
    for d in chat_deals:
        clean_u = d["url"].replace("https://", "").replace("http://", "").strip("/").split("?")[0]
        chat_by_url[clean_u].append(d)
        
    url_deduped_chat = []
    for u, items in chat_by_url.items():
        if len(items) > 1:
            items.sort(key=lambda x: x["dt"])
            latest = items[-1]
            earlier = items[0]
            print(f"  [URL Recency Match in Chat] '{u}':")
            print(f"    Earlier on {earlier['dt']}: ₹{earlier['price']} ({earlier['title']})")
            print(f"    -> VALID RECENT on {latest['dt']}: ₹{latest['price']} ({latest['title']})")
            url_deduped_chat.append(latest)
        else:
            url_deduped_chat.append(items[0])
            
    chat_by_key = defaultdict(list)
    for d in url_deduped_chat:
        key = get_canonical_product_key(d["title"], d["url"])
        chat_by_key[key].append(d)
        
    resolved_chat_deals = []
    for key, items in chat_by_key.items():
        if len(items) > 1:
            items.sort(key=lambda x: x["dt"])
            latest = items[-1]
            earlier = items[0]
            print(f"  [Canonical Recency Match in Chat] Product '{key}':")
            print(f"    Earlier on {earlier['dt']}: ₹{earlier['price']} ({earlier['title']})")
            print(f"    -> VALID RECENT on {latest['dt']}: ₹{latest['price']} ({latest['title']})")
            resolved_chat_deals.append(latest)
        else:
            resolved_chat_deals.append(items[0])
            
    print(f"Resolved to {len(resolved_chat_deals)} unique chat deals.")
    
    # Step 2: Merge with existing catalog deals
    print("\n--- Merging with Existing Catalog & Removing Duplicates ---")
    catalog_by_key = defaultdict(list)
    catalog_by_url = {}
    
    for d in existing_deals:
        key = get_canonical_product_key(d["title"], d["url"])
        clean_u = d["url"].replace("https://", "").replace("http://", "").strip("/").split("?")[0]
        catalog_by_key[key].append(d)
        catalog_by_url[clean_u] = d

    updated_count = 0
    added_count = 0
    used_catalog_urls = set()
    used_catalog_keys = set()
    merged_list = []
    
    # First: add/update with resolved chat deals (which are more recent 9-11 Oct)
    for cd in resolved_chat_deals:
        key = get_canonical_product_key(cd["title"], cd["url"])
        clean_u = cd["url"].replace("https://", "").replace("http://", "").strip("/").split("?")[0]
        
        # Check if matches existing by URL or key
        existing_match = None
        if clean_u in catalog_by_url:
            existing_match = catalog_by_url[clean_u]
        elif key in catalog_by_key and len(catalog_by_key[key]) > 0:
            existing_match = catalog_by_key[key][0]
            
        if existing_match:
            img = existing_match.get("image_url", "")
            if img:
                cd["image_url"] = img
            if cd["price"] == 0 and existing_match.get("price", 0) > 0:
                cd["price"] = existing_match["price"]
                cd["discount"] = existing_match.get("discount", cd["discount"])
                
            cd["id"] = existing_match["id"]
            updated_count += 1
            print(f"  [Updated Deal] '{cd['title']}': Price was ₹{existing_match['price']}, now ₹{cd['price']} (dated {cd['timestamp_display']})")
        else:
            cd["id"] = ""
            added_count += 1
            print(f"  [New Deal Added] '{cd['title']}' @ ₹{cd['price']} on {cd['store']} (dated {cd['timestamp_display']})")

        merged_list.append(cd)
        used_catalog_urls.add(clean_u)
        used_catalog_keys.add(key)

    # Second: process remaining catalog deals (ensuring zero internal duplicates)
    for d in existing_deals:
        key = get_canonical_product_key(d["title"], d["url"])
        clean_u = d["url"].replace("https://", "").replace("http://", "").strip("/").split("?")[0]
        
        if clean_u in used_catalog_urls or key in used_catalog_keys:
            continue
            
        used_catalog_urls.add(clean_u)
        used_catalog_keys.add(key)
        merged_list.append(d)
            
    # Guarantee image preservation across all merged items
    for d in merged_list:
        if not d.get("image_url"):
            u = d["url"].replace("https://", "").replace("http://", "").strip("/").split("?")[0]
            key = get_canonical_product_key(d["title"], d["url"])
            if u in catalog_by_url and catalog_by_url[u].get("image_url"):
                d["image_url"] = catalog_by_url[u]["image_url"]
            elif key in catalog_by_key:
                for old in catalog_by_key[key]:
                    if old.get("image_url"):
                        d["image_url"] = old["image_url"]
                        break

    final_deals = merged_list
    print(f"\nFinal catalog size: {len(final_deals)} deals (Updated: {updated_count}, New added: {added_count})")
    
    # Step 3: Clean up and calculate metrics (MRP, savings, loot score, urgency tags)
    for idx, d in enumerate(final_deals):
        d["id"] = f"dd-{idx+1:04d}"
        d["idx"] = idx
        
        price = d.get("price", 0)
        disc = d.get("discount", 0)
        mrp = d.get("mrp", 0)
        
        # Calculate MRP if missing but discount and price available
        if mrp <= price:
            if price > 0 and 0 < disc < 95:
                mrp = int(round(price / (1.0 - (disc / 100.0))))
            else:
                mrp = 0
                
        d["mrp"] = mrp
        d["savings"] = max(0, mrp - price) if mrp > price else 0
        
        # Loot score calculation
        loot_score = 65
        if disc >= 70:
            loot_score = 98
        elif disc >= 50:
            loot_score = 88
        elif disc >= 30:
            loot_score = 78
        if 0 < price < 500:
            loot_score = min(100, loot_score + 8)
        d["loot_score"] = loot_score
        
        # Urgency tag
        title_low = d["title"].lower()
        raw_low = d.get("raw_text", "").lower()
        if "grabfast" in raw_low or "grab fast" in raw_low or "fast" in raw_low:
            urgency = "⚡ FASTEST FINGERS"
        elif disc >= 75:
            urgency = "⚡ 75%+ MEGA CRASH"
        elif disc >= 65:
            urgency = "🔥 ASSURED LOOT"
        elif 0 < price <= 499:
            urgency = "⚡ UNDER ₹499 STEAL"
        elif disc >= 45:
            urgency = "🔻 BBD / GIF SPECIAL"
        elif any(b in title_low for b in ("sony", "apple", "samsung", "oneplus")):
            urgency = "🏆 FLAGSHIP STEAL"
        else:
            urgency = "⏳ LIMITED TIME DEAL"
        d["urgency_tag"] = urgency
        
        # Category metadata
        cat = d.get("category", "daily")
        if cat not in CATEGORY_MAP:
            cat = "daily"
        d["category"] = cat
        d["category_name"] = CATEGORY_MAP[cat]["name"]
        d["category_icon"] = CATEGORY_MAP[cat]["icon"]
        
        # Store metadata
        store = d.get("store", "Amazon")
        for pat, s_name, s_badge, s_code in STORE_RULES:
            if s_name.lower() in store.lower():
                d["store"] = s_name
                d["store_badge"] = s_badge
                d["store_code"] = s_code
                break

    # Step 4: Recompute curated collections
    print("\n--- Computing Curated Sections ---")
    
    # 1. Fastest Fingers First: All deals containing GrabFast, Fast, Grab pinned first, then high-discount under 1500
    fastest_priority = []
    for d in final_deals:
        r_text = d.get("raw_text", "").lower()
        t_text = d["title"].lower()
        if any(w in r_text or w in t_text for w in ["grabfast", "grab fast", "fast", "loot fast", "ise looto"]):
            fastest_priority.append(d["idx"])
            
    print(f"Total deals with Grab/Fast/LootFast: {len(fastest_priority)}")
    # Add other quick deals
    other_fast = [d["idx"] for d in final_deals if d["idx"] not in fastest_priority and 0 < d["price"] <= 1500 and d["discount"] >= 50]
    fastest_fingers = (fastest_priority + other_fast)[:40]
    
    # 2. Q-Rated Picks: Handpicked top flagship items with real prices and strong discounts
    q_candidates = [d for d in final_deals if d["price"] >= 2000 and (d["discount"] >= 30 or any(b in d["title"].lower() for b in ["apple", "samsung", "sony", "asus", "lg", "dell"]))]
    q_candidates.sort(key=lambda x: (x["loot_score"], x["discount"]), reverse=True)
    q_rated = [d["idx"] for d in q_candidates[:30]]
    
    # 3. Hot Drops: Highest discounts across products
    hot_candidates = sorted(final_deals, key=lambda x: (x["discount"], x["loot_score"]), reverse=True)
    hot_drops = [d["idx"] for d in hot_candidates if d["discount"] >= 50][:30]
    
    # 4. Lowest Price Ever: High discount verified lowest price
    low_candidates = [d for d in final_deals if d["discount"] >= 60 or "lowest price" in d.get("raw_text", "").lower()]
    low_candidates.sort(key=lambda x: (x["discount"], -x["price"]), reverse=True)
    lowest_price = [d["idx"] for d in low_candidates[:30]]
    
    print(f"Curated sizes: Q-Rated: {len(q_rated)}, Hot Drops: {len(hot_drops)}, Lowest Price: {len(lowest_price)}, Fastest Fingers: {len(fastest_fingers)}")
    
    # Clean datetime objects for JSON serialization
    for d in final_deals:
        if "dt" in d:
            d["timestamp"] = d["dt"].isoformat() if isinstance(d["dt"], datetime) else str(d["dt"])
            del d["dt"]
            
    payload = {
        "meta": {
            "generated_at": datetime.now().isoformat() + "Z",
            "last_updated_timestamp": "11/10/2026 5:10 pm",
            "total_deals": len(final_deals),
            "sale_events": ["Flipkart Big Billion Days", "Amazon Great Indian Festival"],
            "stores": ["Amazon", "Flipkart", "Myntra", "Ajio"]
        },
        "curated": {
            "q_rated": q_rated,
            "hot_drops": hot_drops,
            "lowest_price": lowest_price,
            "fastest_fingers": fastest_fingers
        },
        "deals": final_deals
    }
    
    # Save files
    with open("data/deals.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("Saved data/deals.json successfully.")
    
    with open("data/deals_data.js", "w", encoding="utf-8") as f:
        f.write("window.DEALS_DATA = " + json.dumps(payload, ensure_ascii=False) + ";\n")
    print("Saved data/deals_data.js successfully.")
    
    return payload

if __name__ == "__main__":
    run_dedup_and_update()
