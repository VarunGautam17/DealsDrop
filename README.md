# DealsDrop 🔻🔥 – Curated Affiliate Deals Platform

> **The right deal, right now.** A lightning-fast, high-converting deal personalization platform for Flipkart Big Billion Days, Amazon Great Indian Festival, Myntra, and Ajio.

[![Netlify Status](https://api.netlify.com/api/v1/badges/dealsdrop/deploy-status)](https://app.netlify.com)
[![Platform](https://img.shields.io/badge/Platform-Web%20%7C%20PWA-red.svg)]()
[![License](https://img.shields.io/badge/License-Proprietary-blue.svg)]()

---

## 🌟 Features

- **🎯 AI Deal Matchmaker ("What do you need?")**: An interactive 3-step personal shopper that matches user category, budget, and priority with the single best live deal and provides 3 runner-ups with a clear "Why this wins" explanation.
- **⚡ Psychological CRO Design**:
  - High-impact store badges: **Amazon GIF**, **Flipkart BBD**, **Myntra BFF**, and **Ajio**.
  - Visible price anchoring: Strikethrough estimated MRP, bold sale price, and "Save ₹X" callouts.
  - Urgency triggers: `🔥 ASSURED LOOT`, `⚡ 65%+ PRICE CRASH`, `⏳ ENDS SOON`.
  - Prominent high-contrast "Buy Now" CTA that opens the affiliate link directly in app/browser.
- **📲 Viral 1-Click WhatsApp Sharing**: Pre-formatted share messages that include deal name, discount, price, and affiliate link so users easily share deals with friends and family.
- **🏷️ Multi-Store & Category Filtering**: Instant filtering by Store (Amazon, Flipkart, Myntra, Ajio), Category, Price bracket (Under ₹499, Under ₹999), and Discount tiers (70%+ off, 50%+ off).
- **🚀 Curated Shelves**:
  - **Q-Rated Picks 🎯**: Hand-picked high-value products worth owning.
  - **Hot Drops 🔥**: Freshly landed deep discounts.
  - **Lowest Price Ever 🔻**: Massive cuts of 65% off or more.
  - **Fastest Fingers First ⚡**: Small-ticket loots under ₹3,500 that sell out rapidly.
- **📥 WhatsApp/Telegram .txt Ingestion**: Built-in Python parser (`scripts/parse_deals.py`) that digests raw chat export `.txt` files directly and outputs structured deal data in seconds.
- **⚡ Sub-Second Static Speed**: Hosted on **Netlify** with zero backend infrastructure costs, zero database latency, and sub-second load times.

---

## 📁 Project Structure

```
DealsDrop/
├── data/
│   ├── deals.json            # Structured dataset of 1,563+ verified deals
│   └── deals_data.js         # Direct JS fallback bundle for offline/zero-CORS usage
├── scripts/
│   ├── deal_dedup_engine.py  # Recency-aware product deduplication & update engine
│   ├── parse_deals.py        # Python parser for WhatsApp/Telegram .txt chat exports
│   ├── update_curated_sections.py # Section optimizer (Q-Rated, Hot Drops, Lowest Price, GrabFast)
│   └── verify_app.py         # Full automated verification test suite
├── index.html                # Main semantic application page
├── styles.css                # Production styling, store themes, animations
├── app.js                    # Reactive state, Matchmaker, search, and filter logic
├── netlify.toml              # Netlify CDN deployment and caching rules
├── README.md                 # Project guide and documentation
├── PROBLEM_STATEMENT.md      # Business context and affiliate conversion strategy
├── IMPLEMENTATION_PLAN.md    # Technical execution blueprint
└── ARCHITECTURE.md           # System design, data schemas, and pipeline
```

---

## 🚀 Quick Start (Local Development)

Because DealsDrop is built as a high-performance static web application, you can run it locally with any simple HTTP server:

### Option 1: Python HTTP Server (Recommended)
```bash
python -m http.server 3000
```
Then open [http://localhost:3000](http://localhost:3000) in your browser.

### Option 2: Node.js (npx serve)
```bash
npx serve .
```

---

## 🔄 Refreshing Deals from WhatsApp / Telegram (.txt)

Whenever you export a new chat file from WhatsApp or Telegram (e.g., `DealsDrop.txt`):

1. Place the export file into the project directory (e.g., as `DealsDrop.txt`).
2. Run the ingestion parser:
   ```bash
   python scripts/parse_deals.py --input DealsDrop.txt
   ```
3. To optionally fetch thumbnail preview images from deal links:
   ```bash
   python scripts/parse_deals.py --input DealsDrop.txt --fetch-images
   ```
4. The script updates `data/deals.json` and `data/deals_data.js` automatically. Commit and push to Git—Netlify will instantly deploy the updated deals!

---

## 🌐 Deploying to Netlify

### Automatic Git Deploy
1. Push this repository to GitHub/GitLab/Bitbucket.
2. In your Netlify dashboard, click **Add new site** $\rightarrow$ **Import an existing project**.
3. Select your repository.
4. Leave build settings as default (Build command: empty, Publish directory: `.`).
5. Click **Deploy Site**.

### Manual CLI Deploy
```bash
npm install -g netlify-cli
netlify deploy --prod --dir=.
```

---

## 🛡️ Brand & Privacy Guidelines
- **No Private Group Links**: The private WhatsApp group link is intentionally withheld to prevent member phone number exposure.
- **Public Community Links**:
  - [DealsDrop WhatsApp Channel](https://whatsapp.com/channel/0029VbCAAl6F1YlVp8hg3l3u)
  - [DealsDrop Telegram Channel](https://t.me/HotDeals31)
