#!/usr/bin/env python3
"""
DealsDrop .txt Chat Parser & Ingestion Pipeline
Parses exported WhatsApp / Telegram chat files into clean, structured deals.json.

Usage:
    python scripts/parse_deals.py --input DealsDrop.txt
    python scripts/parse_deals.py --input DealsDrop.txt --fetch-images
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    r"iphone", r"galaxy", r"s25", r"s24", r"oneplus", r"pixel", r"realme", r"redmi", 
    r"xiaomi", r"vivo", r"oppo", r"poco", r"motorola", r"moto\s+g", r"iqoo", r"smartphone",
    r"mobile", r"infinix", r"lava", r"5g\s+phone"
]

LAPTOP_KEYWORDS = [
    r"laptop", r"macbook", r"thinkpad", r"ideapad", r"vivobook", r"zenbook", r"omnibook",
    r"chromebook", r"ipad", r"tablet", r"tab\s+s", r"surface", r"ryzen", r"intel\s+core",
    r"aspire", r"victus", r"loq", r"gaming\s+laptop"
]

AUDIO_KEYWORDS = [
    r"earbuds", r"tws", r"headphone", r"soundbar", r"speaker", r"airpods", r"buds",
    r"wh-1000xm", r"wf-1000xm", r"bluetooth\s+speaker", r"anc", r"earphones", r"neckband"
]

HOME_KEYWORDS = [
    r"smart\s*tv", r"qled", r"oled", r"inch\s*tv", r"refrigerator", r"fridge", r"washing\s+machine",
    r"air\s*conditioner", r"\bac\b", r"inverter", r"chimney", r"microwave", r"air\s*fryer",
    r"mixer\s+grinder", r"purifier", r"geyser", r"water\s*heater", r"cooler", r"ceiling\s*fan",
    r"projector", r"monitor", r"vacuum"
]

LIFESTYLE_KEYWORDS = [
    r"shirt", r"t-shirt", r"jeans", r"trouser", r"dress", r"kurta", r"shoes", r"sneakers",
    r"watch", r"analog", r"smartwatch", r"trolley", r"luggage", r"backpack", r"perfume",
    r"deodorant", r"jacket", r"sandal", r"mattress", r"gold", r"ring", r"pendant", r"blazer"
]

def determine_category(text, store):
    text_lower = text.lower()
    
    # Keyword checks
    for kw in PHONE_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", text_lower):
            return "phone"
    for kw in LAPTOP_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", text_lower):
            return "laptop"
    for kw in AUDIO_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", text_lower):
            return "audio"
    for kw in HOME_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", text_lower):
            return "home"
    for kw in LIFESTYLE_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", text_lower):
            return "life"

    if store in ("Myntra", "Ajio"):
        return "life"

    return "daily"

def clean_title(title):
    t = re.sub(r"^(?:🔥|⚡|🔻|👉|💥|✨|\*|\s)+", "", title)
    t = re.sub(r"(?:🔥|⚡|🔻|👉|💥|✨|\*|\s)+$", "", t)
    t = re.sub(r"^\d+%\s*(?:off|OFF)\s*(?:on\s*)?[-:]?\s*", "", t, flags=re.I)
    t = re.sub(r"\[.*?coupon.*?\]", "", t, flags=re.I)
    t = re.sub(r"\(.*?coupon.*?\)", "", t, flags=re.I)
    t = re.sub(r"\s+at\s+₹?\s*[\d,]+(?:\s+only)?$", "", t, flags=re.I)
    t = re.sub(r"\s+@\s*₹?\s*[\d,]+.*$", "", t, flags=re.I)
    t = re.sub(r"\s+-\s+Starting\s+@?.*$", "", t, flags=re.I)
    return t.strip()

def parse_chat_messages(raw_text):
    """Splits chat into individual messages across timestamp boundaries."""
    # Pattern for WhatsApp: [10/10/26, 12:45:00 PM] or 10/10/26, 12:45 - 
    split_pattern = r"(?:\r?\n)(?=(?:\[\d{1,2}[/-]\d{1,2}[/-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s+[APMapm]{2})?\]|\d{1,2}[/-]\d{1,2}[/-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s+[APMapm]{2})?\s*-\s*))"
    chunks = re.split(split_pattern, raw_text)
    return chunks

def extract_deals_from_message(msg):
    deals = []
    # Find links
    link_pattern = r"(https?://[^\s]+|(?:fkrt\.cc|bitli\.in|myntr\.it|ajiio\.in)/[^\s]+)"
    links = re.findall(link_pattern, msg)
    if not links:
        return []

    lines = [line.strip() for line in msg.split("\n") if line.strip()]
    if not lines:
        return []

    # Store detection
    primary_link = links[0]
    store = "Amazon"
    store_code = "amazon"
    store_badge = "Amazon GIF"
    for pattern, s_name, s_badge, s_code in STORE_RULES:
        if re.search(pattern, primary_link, re.I):
            store = s_name
            store_badge = s_badge
            store_code = s_code
            break

    # Price extraction
    price = 0
    price_match = re.search(r"(?:₹|Rs\.?|@\s*)\s*([\d,]{2,8})", msg, re.I)
    if price_match:
        price = int(price_match.group(1).replace(",", ""))

    # Discount extraction
    discount = 0
    disc_match = re.search(r"(\d{1,2})\s*%\s*(?:off|OFF|discount)", msg)
    if disc_match:
        discount = int(disc_match.group(1))

    # Starting at flag
    is_starting = bool(re.search(r"(?:starting\s*@|starts\s*@|under\s*₹?|from\s*₹?)", msg, re.I))

    # Spec extraction
    spec = ""
    spec_match = re.search(r"(?:📦|👉|⚡)\s*([^\n]+)", msg)
    if spec_match:
        spec = spec_match.group(1).strip()

    # Product Title extraction
    title = lines[0]
    # Clean header prefix (e.g. "[10/10/26, 1:20 PM] DealsDrop: ")
    title = re.sub(r"^.*?-\s*[^:]+:\s*", "", title)
    title = re.sub(r"^\[.*?\]\s*[^:]+:\s*", "", title)
    title = clean_title(title)

    if not title or len(title) < 3 or title.lower() in ("master link", "buy here", "loots", "loot"):
        # Look for second line
        if len(lines) > 1:
            title = clean_title(lines[1])

    if not title or len(title) < 3:
        title = f"Sale Deal at ₹{price}" if price else "Festive Loot Deal"

    cat = determine_category(f"{title} {spec}", store)

    return [{
        "title": title,
        "price": price,
        "discount": discount,
        "category": cat,
        "category_name": CATEGORY_MAP[cat]["name"],
        "category_icon": CATEGORY_MAP[cat]["icon"],
        "store": store,
        "store_code": store_code,
        "store_badge": store_badge,
        "url": primary_link if primary_link.startswith("http") else f"https://{primary_link}",
        "spec": spec,
        "is_starting_at": is_starting
    }]

def fetch_single_image(deal):
    """Attempts to fetch real product image by unquoting tracking links and resolving Amazon/Flipkart/Myntra CDN assets."""
    url = deal.get("url", "")
    if not url:
        return ""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9"
    }

    try:
        # Step 1: Follow initial shortlink to find tracking bridge or final URL
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            final_url = resp.geturl()
            html = resp.read(200000).decode("utf-8", errors="ignore")

        # Step 2: If redirected to tracking bridge (EarnKaro/linkredirect), extract real target from dl parameter
        target_url = final_url
        if "linkredirect.in" in final_url or "earnkaro" in final_url or "ckassets" in final_url:
            parsed = urllib.parse.urlparse(final_url)
            qs = urllib.parse.parse_qs(parsed.query)
            if "dl" in qs:
                target_url = qs["dl"][0]
                # Fetch target destination directly
                req2 = urllib.request.Request(target_url, headers=headers)
                with urllib.request.urlopen(req2, timeout=6) as resp2:
                    final_url = resp2.geturl()
                    html = resp2.read(300000).decode("utf-8", errors="ignore")

        # Step 3: Check for Amazon hiRes / large product image
        if "amazon" in final_url or "amzn" in final_url:
            hi_res = re.findall(r'"hiRes"\s*:\s*"([^"]+)"', html)
            if hi_res:
                return hi_res[0]
            landing = re.findall(r'"landingImage"[^:]*:\s*\[?[\'"]([^\'"]+)[\'"]', html)
            if landing:
                return landing[0]
            large = re.findall(r'"large"\s*:\s*"([^"]+)"', html)
            if large:
                return large[0]
            direct_amazon = re.findall(r'https://m\.media-amazon\.com/images/I/[A-Za-z0-9_\-\.%]+\.(?:jpg|png)', html)
            if direct_amazon:
                return direct_amazon[0]

        # Step 4: Check for Flipkart product image on rukminim CDN
        if "flipkart" in final_url:
            fk_imgs = re.findall(r'https://rukminim[12]?\.flixcart\.com/image/(?:800/1070|612/612|416/416)/[^\s"\'\?]+', html)
            if fk_imgs:
                return fk_imgs[0]
            any_fk = re.findall(r'https://rukminim[12]?\.flixcart\.com/image/[^\s"\'\?]+', html)
            if any_fk:
                return any_fk[0]

        # Step 5: Check for Myntra assets
        if "myntra" in final_url:
            myntra_imgs = re.findall(r'https://assets\.myntassets\.com/[^\s"\'\?]+', html)
            if myntra_imgs:
                return myntra_imgs[0]

        # Step 6: Standard OpenGraph fallback (ignore generic affiliate bridge banners)
        og_match = re.search(r'<meta[^>]+property=[\'"]og:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]', html, re.I)
        if not og_match:
            og_match = re.search(r'<meta[^>]+content=[\'"]([^\'"]+)[\'"][^>]+property=[\'"]og:image[\'"]', html, re.I)
        if og_match:
            img = og_match.group(1)
            if not any(bad in img.lower() for bad in ("ckassets", "default", "logo", "store-live")):
                return img

    except Exception:
        pass
    return ""

def main():
    parser = argparse.ArgumentParser(description="DealsDrop Chat Ingestion Pipeline")
    parser.add_argument("--input", default="DealsDrop.txt", help="Path to input .txt chat export file")
    parser.add_argument("--fetch-images", action="store_true", help="Attempt to scrape product thumbnails from links")
    parser.add_argument("--max-workers", type=int, default=8, help="Number of concurrent workers for image fetching")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        # If input doesn't exist, check data/raw_deals.json as fallback
        if os.path.exists("data/raw_deals.json"):
            print(f"Warning: '{args.input}' not found. Re-building from 'data/raw_deals.json'...")
            os.system(f"{sys.executable} scripts/build_data.py")
            return
        else:
            print(f"Error: Neither '{args.input}' nor 'data/raw_deals.json' found.")
            sys.exit(1)

    print(f"Reading {args.input}...")
    with open(args.input, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    messages = parse_chat_messages(content)
    print(f"Found {len(messages)} raw messages. Extracting deals...")

    extracted = []
    seen_links = set()

    for msg in messages:
        deals = extract_deals_from_message(msg)
        for d in deals:
            url = d["url"]
            if url not in seen_links:
                seen_links.add(url)
                extracted.append(d)

    print(f"Extracted {len(extracted)} unique deals.")

    # Calculate MRP, savings, scores, and tags
    processed_deals = []
    for idx, d in enumerate(extracted):
        price = d["price"]
        discount = d["discount"]
        mrp = 0
        savings = 0
        if price > 0 and 0 < discount < 95:
            mrp = int(round(price / (1.0 - (discount / 100.0))))
            if mrp > price:
                savings = mrp - price

        loot_score = 65
        if discount >= 70:
            loot_score = 98
        elif discount >= 50:
            loot_score = 88
        elif discount >= 30:
            loot_score = 78

        if discount >= 75:
            urgency = "⚡ 75%+ MEGA CRASH"
        elif discount >= 65:
            urgency = "🔥 ASSURED LOOT"
        elif price > 0 and price <= 499:
            urgency = "⚡ UNDER ₹499 STEAL"
        elif discount >= 45:
            urgency = "🔻 BBD / GIF SPECIAL"
        elif any(b in d["title"].lower() for b in ("sony", "apple", "samsung", "oneplus")):
            urgency = "🏆 FLAGSHIP STEAL"
        else:
            urgency = "⏳ LIMITED TIME DEAL"

        d["id"] = f"dd-{idx+1:04d}"
        d["idx"] = idx
        d["mrp"] = mrp
        d["savings"] = savings
        d["loot_score"] = loot_score
        d["urgency_tag"] = urgency
        d["image_url"] = ""
        processed_deals.append(d)

    # Optional image fetching
    if args.fetch_images:
        print(f"Fetching images for {len(processed_deals)} deals with {args.max_workers} threads...")
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            future_to_deal = {executor.submit(fetch_single_image, deal): deal for deal in processed_deals[:100]}
            for future in as_completed(future_to_deal):
                deal = future_to_deal[future]
                img = future.result()
                if img:
                    deal["image_url"] = img

    # Compute curated selections
    q_rated = [d["idx"] for d in processed_deals if d["loot_score"] >= 90][:12]
    hot_drops = [d["idx"] for d in processed_deals if d["discount"] >= 60][:10]
    lowest_price = [d["idx"] for d in processed_deals if d["discount"] >= 65][:10]
    fastest_fingers = [d["idx"] for d in processed_deals if 0 < d["price"] <= 1500 and d["discount"] >= 50][:10]

    final_payload = {
        "meta": {
            "generated_at": "2026-10-11T13:40:00Z",
            "total_deals": len(processed_deals),
            "sale_events": ["Flipkart Big Billion Days", "Amazon Great Indian Festival"],
            "stores": ["Amazon", "Flipkart", "Myntra", "Ajio"]
        },
        "curated": {
            "q_rated": q_rated,
            "hot_drops": hot_drops,
            "lowest_price": lowest_price,
            "fastest_fingers": fastest_fingers
        },
        "deals": processed_deals
    }

    os.makedirs("data", exist_ok=True)
    with open("data/deals.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    with open("data/deals_data.js", "w", encoding="utf-8") as f:
        f.write("window.DEALS_DATA = " + json.dumps(final_payload, ensure_ascii=False) + ";\n")

    print(f"Pipeline complete! Wrote {len(processed_deals)} deals to data/deals.json and data/deals_data.js")

if __name__ == "__main__":
    main()
