# DealsDrop 🔻🔥 – System Architecture

## 1. Architectural Philosophy
The DealsDrop architecture is engineered around three pillars:
1. **Zero-Latency Static Performance**: Spikes in traffic during flash sales require instantaneous sub-second loading with zero cold starts, easily hosted on Netlify or any CDN edge.
2. **Offline-First Resilience & Separation of Concerns**: Data (`data/deals.json`) is decoupled from presentation (`index.html`, `styles.css`, `app.js`), allowing updates without redeploying code.
3. **Conversion-Centric UX Architecture**: High-speed client-side filtering, reactive personalization, and psychological e-commerce triggers designed to minimize hesitation and drive checkout.

---

## 2. High-Level Architecture Diagram

```
+-------------------------------------------------------------+
|                     DATA INGESTION PIPELINE                 |
|                                                             |
|  [ WhatsApp / Telegram Chat Export (.txt) ]                |
|                             |                               |
|                             v                               |
|                 [ scripts/parse_deals.py ]                  |
|          - Regex Parsing & Link Normalization               |
|          - Category / Store Tagging                         |
|          - Price Extraction & MRP Computation               |
|          - Curated Shelves & Loot Score Engine              |
|          - (Optional) OpenGraph Thumbnail Scraper           |
|                             |                               |
|                             v                               |
|                    [ data/deals.json ]                      |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                 CLIENT-SIDE APPLICATION RUNTIME             |
|                                                             |
|  [ index.html ]                                             |
|    |                                                        |
|    +--> [ styles.css ]                                      |
|    |      - Mobile-First Fluid Typography                   |
|    |      - Store Identity System (Amazon/FK/Myntra/Ajio)   |
|    |      - Urgency Animations & FOMO Visual Cues           |
|    |      - Dark / Light Theme Tokens                       |
|    |                                                        |
|    +--> [ app.js ]                                          |
|           |                                                 |
|           +-- State Management (filters, search, sort, cur) |
|           +-- "AI Deal Matchmaker" Recommendation Engine    |
|           +-- Curated Shelves (Q-Rated, Hot, Lowest, FFF)   |
|           +-- Store & Category Pill Filter Engine           |
|           +-- Dynamic Card Renderer (Price Anchor + Badges) |
|           +-- WhatsApp Viral Share Generator                |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                      DEPLOYMENT TARGET                      |
|                                                             |
|  [ Netlify CDN / Edge ] (via netlify.toml)                  |
|  - Zero server runtime cost                                 |
|  - Continuous Deployment via Git or Netlify CLI             |
|  - Instant Cache Invalidation on Data Refresh               |
+-------------------------------------------------------------+
```

---

## 3. Data Model Schema (`data/deals.json`)

Each deal object contains structured attributes optimized for client-side search and filtering:

```json
{
  "meta": {
    "generated_at": "2026-10-11T13:40:00Z",
    "total_deals": 1427,
    "sale_events": ["Flipkart Big Billion Days", "Amazon Great Indian Festival"],
    "stores": ["Amazon", "Flipkart", "Myntra", "Ajio"]
  },
  "curated": {
    "q_rated": [1211, 394, 514, 392, 687, 1323, 1415, 36, 872, 1284],
    "hot_drops": [365, 233, 1283, 1011, 1170, 1001, 589, 642],
    "lowest_price": [638, 1171, 1217, 1253, 32, 990, 359, 608],
    "fastest_fingers": [449, 539, 431, 1213, 1164, 1190, 395, 490]
  },
  "deals": [
    {
      "id": "deal-0001",
      "title": "Sony WH-1000XM5 Noise Cancelling Headphones",
      "price": 17990,
      "mrp": 34990,
      "discount": 49,
      "category": "audio",
      "category_name": "Audio & Soundbars",
      "store": "Flipkart",
      "store_badge": "BBD Special",
      "url": "https://fkrt.cc/z8tU7HZ",
      "specs": "Wireless Noise Cancellation with AI Noise Reduction",
      "is_starting_at": false,
      "loot_score": 94,
      "urgency_tag": "🔥 Selling Fast",
      "bank_offer": "Extra 10% off on HDFC Cards",
      "image_url": ""
    }
  ]
}
```

---

## 4. Ingestion Engine (`scripts/parse_deals.py`)

The ingestion pipeline handles raw text exports created via WhatsApp (`Chat with DealsDrop.txt`) or Telegram desktop exports:

1. **Message Segmentation**: Regex boundaries split chats across date-time timestamps (`[DD/MM/YY, HH:MM:SS]` or `DD/MM/YY, HH:MM - Sender:`).
2. **Link Extraction & Store Disambiguation**:
   - `fkrt.cc` / `flipkart.com` $\rightarrow$ Flipkart (Big Billion Days)
   - `bitli.in` / `amazon.in` $\rightarrow$ Amazon (Great Indian Festival)
   - `myntr.it` / `myntra.com` $\rightarrow$ Myntra (BFF)
   - `ajiio.in` / `ajio.com` $\rightarrow$ Ajio (All Stars)
3. **Price & Discount Parser**:
   - Matches `₹[0-9,]+`, `Rs\.?\s*[0-9,]+`, `@\s*[0-9,]+`.
   - Normalizes comma separators (`1,499` $\rightarrow$ `1499`).
   - Parses discount percentages (`NN% off` / `Up to NN% Off`).
   - Reverse-calculates estimated MRP when only price + discount are available:
     $$\text{MRP} = \text{round}\left(\frac{\text{Price}}{1 - (\text{Discount} / 100)}\right)$$
4. **Noise Filtering**: Eliminates redundant bot messages, generic admin announcements, and dead links.
5. **Categorization Taxonomy**:
   - `phone`: Mobile Phones & Accessories
   - `laptop`: Laptops, Tablets & PC Gear
   - `audio`: Headphones, TWS Earbuds & Speakers
   - `home`: TV & Large Appliances, Kitchen & Home
   - `life`: Lifestyle, Fashion, Footwear & Luggage
   - `daily`: Daily Needs, Groceries, Fitness & Supplements

---

## 5. UI/UX & Conversion Rate Optimization (CRO) Framework

### 5.1 Cognitive Ease & Scannability
- **Store-Coded Branding**: Every deal card instantly signals its merchant through visual branding (Amazon Warm Amber, Flipkart Electric Blue, Myntra Magenta Glam, Ajio Cyan Neon).
- **Price Anchorage**: Displaying estimated MRP crossed out alongside the bold discounted price reinforces the perceived bargain.
- **Micro-Copy Urgency**: Badges such as `⚡ FLASH LOOT`, `🔻 LOWEST SALE PRICE`, `⏳ ENDS SOON` trigger psychological loss aversion.

### 5.2 The 3-Step Matchmaker Engine
- **Intent**: Users with specific requirements do not browse; they want to be told what to buy.
- **Step 1**: Category selection (Phones, Laptops, Audio, TV/Home, Lifestyle, Daily).
- **Step 2**: Contextual budget brackets tailored specifically to that category (e.g., Laptops have bands up to ₹90K+, whereas Audio has bands up to ₹10K+).
- **Step 3**: Priority (Deepest Discount vs Budget Bang-for-Buck vs Premium Pick).
- **Output**: Returns the single optimal recommendation with an explicit rationale (*"Why this wins"*), followed by 3 runner-ups, eliminating decision paralysis.

---

## 6. Hosting & Deployment Configuration (Netlify)

- **Root Distribution**: Direct deployment from the repository root.
- **Configuration (`netlify.toml`)**:
  - Directs headers with optimal HTTP caching (`Cache-Control: public, max-age=3600`).
  - Gzip and Brotli compression for minimal transfer weight.
  - Zero build step required, enabling instant deploys.
