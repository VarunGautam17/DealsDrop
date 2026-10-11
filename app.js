/**
 * DealsDrop 🔻🔥 – Production Client Application
 * Clean, Professional, Overflow-Safe E-Commerce Engine
 */

(function () {
  'use strict';

  var PAGE_SIZE = 24;

  var state = {
    deals: [],
    curated: { q_rated: [], hot_drops: [], lowest_price: [], fastest_fingers: [] },
    section: 'all',
    query: '',
    store: 'all',
    category: 'all',
    sort: 'rank',
    shownCount: PAGE_SIZE,
    matchmaker: { category: null, budgetIndex: null, priority: null }
  };

  var CATEGORIES = {
    all: { name: 'All', icon: '🔥' },
    phone: { name: 'Phones', icon: '📱' },
    laptop: { name: 'Laptops & Tablets', icon: '💻' },
    audio: { name: 'Audio & Speakers', icon: '🎧' },
    home: { name: 'TV & Appliances', icon: '📺' },
    life: { name: 'Fashion & Lifestyle', icon: '👕' },
    daily: { name: 'Daily Needs', icon: '⚡' }
  };

  var BUDGET_BANDS = {
    phone: [[0, 15000, 'Under ₹15K'], [15000, 30000, '₹15K–30K'], [30000, 50000, '₹30K–50K'], [50000, 1e9, '₹50K+']],
    laptop: [[0, 40000, 'Under ₹40K'], [40000, 60000, '₹40K–60K'], [60000, 90000, '₹60K–90K'], [90000, 1e9, '₹90K+']],
    audio: [[0, 3000, 'Under ₹3K'], [3000, 10000, '₹3K–10K'], [10000, 1e9, '₹10K+']],
    home: [[0, 10000, 'Under ₹10K'], [10000, 30000, '₹10K–30K'], [30000, 1e9, '₹30K+']],
    life: [[0, 2000, 'Under ₹2K'], [2000, 5000, '₹2K–5K'], [5000, 1e9, '₹5K+']],
    daily: [[0, 500, 'Under ₹500'], [500, 1500, '₹500–1,500'], [1500, 1e9, '₹1,500+']]
  };

  var PRICE_FLOORS = {
    phone: 4000,
    laptop: 8000,
    audio: 300,
    home: 300,
    life: 300,
    daily: 0
  };

  var PRIORITIES = [
    { id: 'val', label: '🔥 Deepest Discount' },
    { id: 'low', label: '💰 Lowest Price Saver' },
    { id: 'top', label: '⭐ Flagship Pick' }
  ];

  var $ = function (id) { return document.getElementById(id); };

  function escapeHTML(str) {
    return String(str || '').replace(/[&<>'"]/g, function (m) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[m];
    });
  }

  function inr(n) {
    return '₹' + Number(n || 0).toLocaleString('en-IN');
  }

  // =========================================================================
  // Data Initialization
  // =========================================================================

  async function loadData() {
    try {
      var resp = await fetch('data/deals.json');
      if (!resp.ok) throw new Error('Fetch failed');
      var data = await resp.json();
      initApp(data);
    } catch (e) {
      if (window.DEALS_DATA) {
        initApp(window.DEALS_DATA);
      } else {
        $('count-status').textContent = 'Unable to load deals.';
      }
    }
  }

  function initApp(data) {
    state.deals = data.deals || [];
    state.curated = data.curated || { q_rated: [], hot_drops: [], lowest_price: [], fastest_fingers: [] };
    $('hero-total-count').textContent = state.deals.length.toLocaleString('en-IN') + ' Deals';

    updateSectionCounts();
    updateStoreCounts();
    renderCategoryStrip();
    renderMatchmaker();
    applyFilters();
    setupEvents();
  }

  function updateSectionCounts() {
    var allCnt = $('sec-cnt-all');
    if (allCnt) allCnt.textContent = state.deals.length;
    var qCnt = $('sec-cnt-q');
    if (qCnt) qCnt.textContent = (state.curated.q_rated || []).length;
    var hCnt = $('sec-cnt-h');
    if (hCnt) hCnt.textContent = (state.curated.hot_drops || []).length;
    var lCnt = $('sec-cnt-l');
    if (lCnt) lCnt.textContent = (state.curated.lowest_price || []).length;
    var fCnt = $('sec-cnt-f');
    if (fCnt) fCnt.textContent = (state.curated.fastest_fingers || []).length;
  }

  function updateStoreCounts() {
    var counts = { all: 0, amazon: 0, flipkart: 0, myntra: 0, ajio: 0 };
    state.deals.forEach(function (d) {
      counts.all++;
      if (counts[d.store_code] !== undefined) counts[d.store_code]++;
    });
    ['all', 'amazon', 'flipkart', 'myntra', 'ajio'].forEach(function (s) {
      var el = $('sc-' + s);
      if (el) el.textContent = counts[s];
    });
  }

  // =========================================================================
  // Category Strip
  // =========================================================================

  function renderCategoryStrip() {
    var container = $('cat-strip');
    if (!container) return;

    var catCounts = {};
    Object.keys(CATEGORIES).forEach(function (k) { catCounts[k] = 0; });

    state.deals.forEach(function (d) {
      if (state.store === 'all' || d.store_code === state.store) {
        catCounts.all++;
        catCounts[d.category] = (catCounts[d.category] || 0) + 1;
      }
    });

    var html = Object.entries(CATEGORIES).map(function (entry) {
      var key = entry[0], info = entry[1];
      var count = catCounts[key] || 0;
      var isActive = state.category === key;

      return (
        '<button type="button" class="cat-pill ' + (isActive ? 'active' : '') + '" data-cat="' + key + '">' +
        info.icon + ' ' + info.name + ' <span class="cnt">(' + count + ')</span>' +
        '</button>'
      );
    }).join('');

    container.innerHTML = html;

    container.querySelectorAll('.cat-pill').forEach(function (btn) {
      btn.onclick = function () {
        state.category = btn.dataset.cat;
        state.shownCount = PAGE_SIZE;
        renderCategoryStrip();
        applyFilters(true);
      };
    });
  }

  // =========================================================================
  // Filter & Search Engine
  // =========================================================================

  // Section Metadata Dictionary
  var SECTION_META = {
    all: {
      title: '🛍️ All Festival Deals',
      desc: 'Browse all verified deals from Flipkart Big Billion Days, Amazon GIF, Myntra & Ajio.',
      tag: 'All Deals'
    },
    q_rated: {
      title: '🎯 Q-Rated Picks',
      desc: 'Hand-picked editor favorites: steep discounts on high-value products actually worth owning.',
      tag: 'Q-Rated'
    },
    hot_drops: {
      title: '🔥 Hot Drops',
      desc: 'Fresh massive price drops that just landed from Flipkart & Amazon festival feeds.',
      tag: 'Hot Drops'
    },
    lowest_price: {
      title: '🔻 Lowest Price Ever',
      desc: 'Deepest price cuts in this festival sale (65% off or more, verified drops).',
      tag: 'Lowest Ever'
    },
    fastest_fingers: {
      title: '⚡ Fastest Fingers First (GrabFast)',
      desc: 'High-demand flash loots and small-ticket steals under ₹3,500 that vanish quickly.',
      tag: 'GrabFast'
    }
  };

  function getMatchingDeals() {
    var query = state.query.trim().toLowerCase();
    var tokens = query.split(/\s+/).filter(Boolean);

    // Filter by Curated Section if active
    var candidatePool = state.deals;
    if (state.section !== 'all') {
      var indices = state.curated[state.section] || [];
      var indexSet = new Set(indices);
      candidatePool = state.deals.filter(function (d, i) {
        return indexSet.has(d.idx !== undefined ? d.idx : i);
      });
    }

    return candidatePool.filter(function (d) {
      // Store filter
      if (state.store !== 'all' && d.store_code !== state.store) return false;

      // Category filter
      if (state.category !== 'all' && d.category !== state.category) return false;

      // Token search
      if (tokens.length > 0) {
        var searchable = (d.title + ' ' + (d.spec || '') + ' ' + d.store + ' ' + d.category_name).toLowerCase();
        for (var i = 0; i < tokens.length; i++) {
          if (searchable.indexOf(tokens[i]) < 0) return false;
        }
      }

      return true;
    });
  }

  function sortDeals(deals) {
    var list = deals.slice();
    if (state.sort === 'pct') {
      list.sort(function (a, b) { return b.discount - a.discount || a.price - b.price; });
    } else if (state.sort === 'low') {
      list.sort(function (a, b) { return (a.price || 1e9) - (b.price || 1e9); });
    } else if (state.sort === 'high') {
      list.sort(function (a, b) { return (b.price || 0) - (a.price || 0); });
    } else {
      // Default 'rank' / loot score
      list.sort(function (a, b) { return b.loot_score - a.loot_score || b.discount - a.discount; });
    }
    return list;
  }

  function applyFilters(scrollToTop) {
    var matches = getMatchingDeals();
    var sorted = sortDeals(matches);
    var visible = sorted.slice(0, state.shownCount);

    // Update Section Banner
    var secBanner = $('section-banner');
    var secTitle = $('sec-banner-title');
    var secDesc = $('sec-banner-desc');
    var secBadge = $('sec-banner-badge');

    if (secBanner && state.section !== 'all') {
      var meta = SECTION_META[state.section] || SECTION_META.all;
      secBanner.hidden = false;
      if (secTitle) secTitle.innerHTML = meta.title;
      if (secDesc) secDesc.textContent = meta.desc;
      if (secBadge) secBadge.textContent = sorted.length + ' Deals';
    } else if (secBanner) {
      secBanner.hidden = true;
    }

    var countStatus = $('count-status');
    if (countStatus) {
      countStatus.innerHTML = sorted.length
        ? 'Showing ' + visible.length + ' of <b>' + sorted.length.toLocaleString('en-IN') + '</b> deals'
        : 'No matching deals';
    }

    var grid = $('deals-container');
    var emptyBox = $('empty-box');
    var moreContainer = $('more-container');
    var moreBadge = $('more-badge');

    if (sorted.length === 0) {
      if (grid) grid.innerHTML = '';
      if (emptyBox) emptyBox.hidden = false;
      if (moreContainer) moreContainer.hidden = true;
      return;
    }

    if (emptyBox) emptyBox.hidden = true;

    // Render cards
    if (grid) {
      grid.innerHTML = visible.map(function (d, i) {
        return renderCardHTML(d, i + 1);
      }).join('');
    }

    // Load more row
    var left = sorted.length - visible.length;
    if (moreContainer) {
      moreContainer.hidden = left <= 0;
      if (moreBadge) {
        moreBadge.textContent = left > 0 ? '(' + Math.min(PAGE_SIZE, left) + ' of ' + left + ' left)' : '';
      }
    }

    if (scrollToTop) {
      var controls = $('filter-controls');
      if (controls) {
        var topY = controls.getBoundingClientRect().top + window.scrollY - 10;
        if (window.scrollY > topY) window.scrollTo({ top: topY, behavior: 'smooth' });
      }
    }
  }

  // =========================================================================
  // Clean Modern Product Card Generator (Zero Overflow)
  // =========================================================================

  function renderCardHTML(deal, rank) {
    var title = escapeHTML(deal.title);
    var url = escapeHTML(deal.url);
    var store = escapeHTML(deal.store);
    var storeCode = deal.store_code || 'amazon';
    var price = deal.price;
    var mrp = deal.mrp;
    var discount = deal.discount;
    var savings = deal.savings;
    var spec = escapeHTML(deal.spec || '');
    var catInfo = CATEGORIES[deal.category] || CATEGORIES.daily;

    // Viral WhatsApp share copy
    var shareText = encodeURIComponent(
      '🔥 *DealsDrop Loot Alert!*\n\n' +
      deal.title + '\n' +
      (price ? '💰 *Deal Price:* ' + inr(price) : '') +
      (discount ? ' (' + discount + '% OFF)' : '') +
      (mrp && mrp > price ? '\n❌ MRP: ' + inr(mrp) : '') +
      '\n\n👉 *Claim here:* ' + deal.url + '\n\nVia DealsDrop 🔻🔥'
    );
    var waUrl = 'https://wa.me/?text=' + shareText;

    // Image container with robust fallback
    var imgHtml = '';
    if (deal.image_url) {
      imgHtml = (
        '<div class="product-img-box">' +
        '<img src="' + escapeHTML(deal.image_url) + '" alt="' + title + '" loading="lazy" ' +
        'onerror="this.parentElement.classList.add(\'fallback\'); this.parentElement.innerHTML=\'' + catInfo.icon + '\';">' +
        '</div>'
      );
    } else {
      imgHtml = '<div class="product-img-box fallback">' + catInfo.icon + '</div>';
    }

    // Status note
    var statusNote = '';
    if (discount >= 65) {
      statusNote = '<b>Matches lowest price ever</b>';
    } else if (savings > 0) {
      statusNote = '<b>' + inr(savings) + ' below</b> regular price';
    } else {
      statusNote = 'Verified festival sale deal';
    }

    // Price section (Handles 0 price gracefully without ANY overflow)
    var priceHtml = '';
    if (price && price > 0) {
      priceHtml = (
        '<div class="price-values-group">' +
        '<span class="main-price-val">' + (deal.is_starting_at ? '<small style="font-size: 13px; font-weight:600; color:var(--text-muted);">From </small>' : '') + inr(price) + '</span>' +
        (mrp && mrp > price ? '<span class="mrp-strike-val">' + inr(mrp) + '</span>' : '') +
        (savings > 0 ? '<span class="savings-badge">Save ' + inr(savings) + '</span>' : '') +
        '</div>'
      );
    } else {
      priceHtml = (
        '<div class="price-values-group">' +
        '<span class="main-price-val" style="font-size: 15px; color: var(--brand-red);">Special Festival Offer</span>' +
        '</div>'
      );
    }

    return (
      '<article class="card-item">' +
      // Header: Store badge & discount pill
      '<div class="card-header-bar">' +
      '<span class="store-tag ' + storeCode + '">' + store + '</span>' +
      (deal.timestamp_display ? '<span class="time-pill" title="Verified at ' + escapeHTML(deal.timestamp_display) + '">🕒 ' + escapeHTML(deal.timestamp_display.replace('/2026', '')) + '</span>' : '') +
      (discount ? '<span class="discount-badge">' + discount + '% OFF</span>' : '') +
      '</div>' +
      // Main: Image + Title + Status
      '<div class="card-main-content">' +
      imgHtml +
      '<div class="card-title-block">' +
      '<h3 class="card-title-text" title="' + title + '">' + title + '</h3>' +
      '<div class="card-status-note">' + statusNote + '</div>' +
      '</div>' +
      '</div>' +
      // Why this deal dropdown
      '<details class="deal-why-dropdown">' +
      '<summary>Why this deal</summary>' +
      '<ul class="deal-why-bullets">' +
      (discount ? '<li>' + discount + '% markdown compared to typical off-sale price</li>' : '') +
      (spec ? '<li>' + spec + '</li>' : '<li>Verified high-intent festival deal from ' + store + '</li>') +
      '<li>Direct merchant listing with festival warranty & return support</li>' +
      '</ul>' +
      '</details>' +
      // Price block
      '<div class="price-block-wrapper">' +
      priceHtml +
      '</div>' +
      // CTAs
      '<div class="card-cta-row">' +
      '<a class="btn-buy-deal" href="' + url + '" target="_blank" rel="sponsored noopener noreferrer">' +
      'Buy on ' + store + ' ↗' +
      '</a>' +
      '<a class="btn-share-deal" href="' + waUrl + '" target="_blank" rel="noopener" aria-label="Share on WhatsApp" title="Share on WhatsApp">' +
      '💬 Share' +
      '</a>' +
      '</div>' +
      '</article>'
    );
  }

  // =========================================================================
  // AI Deal Matchmaker
  // =========================================================================

  function renderMatchmaker() {
    var trigger = $('mm-trigger');
    var panel = $('mm-panel');
    var caret = $('mm-caret');

    if (trigger && panel) {
      trigger.onclick = function () {
        var isHidden = panel.hidden;
        panel.hidden = !isHidden;
        trigger.setAttribute('aria-expanded', String(isHidden));
        if (caret) caret.textContent = isHidden ? '▴' : '▾';
      };
    }

    // Step 1: Categories
    var catBox = $('mm-cat-row');
    if (catBox) {
      catBox.innerHTML = Object.entries(CATEGORIES).filter(function (e) { return e[0] !== 'all'; }).map(function (e) {
        var k = e[0], v = e[1];
        var isSelected = state.matchmaker.category === k;
        return (
          '<button type="button" class="pill-choice" data-cat="' + k + '" aria-pressed="' + isSelected + '">' +
          v.icon + ' ' + v.name +
          '</button>'
        );
      }).join('');

      catBox.querySelectorAll('.pill-choice').forEach(function (btn) {
        btn.onclick = function () {
          state.matchmaker.category = btn.dataset.cat;
          state.matchmaker.budgetIndex = null;
          state.matchmaker.priority = null;
          renderMatchmaker();
        };
      });
    }

    // Step 2: Budgets
    var budgetContainer = $('mm-budget-container');
    var budgetBox = $('mm-budget-row');
    var cat = state.matchmaker.category;
    if (budgetContainer && budgetBox) {
      budgetContainer.hidden = !cat;
      if (cat && BUDGET_BANDS[cat]) {
        budgetBox.innerHTML = BUDGET_BANDS[cat].map(function (b, idx) {
          var isSelected = state.matchmaker.budgetIndex === idx;
          return (
            '<button type="button" class="pill-choice" data-idx="' + idx + '" aria-pressed="' + isSelected + '">' +
            b[2] +
            '</button>'
          );
        }).join('');

        budgetBox.querySelectorAll('.pill-choice').forEach(function (btn) {
          btn.onclick = function () {
            state.matchmaker.budgetIndex = Number(btn.dataset.idx);
            state.matchmaker.priority = null;
            renderMatchmaker();
          };
        });
      }
    }

    // Step 3: Priorities
    var priorityContainer = $('mm-priority-container');
    var priorityBox = $('mm-priority-row');
    var bIdx = state.matchmaker.budgetIndex;
    if (priorityContainer && priorityBox) {
      priorityContainer.hidden = bIdx === null;
      if (bIdx !== null) {
        priorityBox.innerHTML = PRIORITIES.map(function (p) {
          var isSelected = state.matchmaker.priority === p.id;
          return (
            '<button type="button" class="pill-choice" data-p="' + p.id + '" aria-pressed="' + isSelected + '">' +
            p.label +
            '</button>'
          );
        }).join('');

        priorityBox.querySelectorAll('.pill-choice').forEach(function (btn) {
          btn.onclick = function () {
            state.matchmaker.priority = btn.dataset.p;
            renderMatchmaker();
          };
        });
      }
    }

    // Results Box
    var resultContainer = $('mm-result-container');
    var pri = state.matchmaker.priority;
    if (resultContainer) {
      if (cat && bIdx !== null && pri) {
        resultContainer.hidden = false;
        resultContainer.innerHTML = computeMatchResult(cat, bIdx, pri);
      } else {
        resultContainer.hidden = true;
      }
    }
  }

  function computeMatchResult(cat, bIdx, pri) {
    var band = BUDGET_BANDS[cat][bIdx];
    var min = band[0], max = band[1], label = band[2];
    var floor = PRICE_FLOORS[cat] || 0;

    // Filter candidate pool to ONLY specific quality deals with real prices & real titles
    var candidates = state.deals.filter(function (d) {
      return (
        d.category === cat &&
        d.price >= floor &&
        d.price > 0 &&
        d.discount > 0 &&
        !d.title.toLowerCase().startsWith('loot deal at') &&
        !d.title.toLowerCase().startsWith('master link')
      );
    });

    var pool = candidates.filter(function (d) { return d.price >= min && d.price < max; });
    var fallback = false;

    if (pool.length === 0) {
      fallback = true;
      var mid = max > 1e8 ? min * 1.3 : (min + max) / 2;
      pool = candidates.slice().sort(function (a, b) {
        return Math.abs(a.price - mid) - Math.abs(b.price - mid);
      }).slice(0, 4);
    }

    if (pri === 'val') {
      pool.sort(function (a, b) { return b.discount - a.discount || a.price - b.price; });
    } else if (pri === 'low') {
      pool.sort(function (a, b) { return a.price - b.price; });
    } else {
      pool.sort(function (a, b) { return b.price - a.price; });
    }

    var best = pool[0];
    if (!best) return '<p style="color:var(--text-sub);">No specific deals found in this bracket. Try another category or budget band!</p>';

    return (
      '<div>' +
      '<div class="mm-result-header">' +
      (fallback ? '⚠️ Closest Matched Live Deal' : '🏆 Top Recommended Deal in ' + label) +
      '</div>' +
      '<div class="mm-deal-preview">' +
      '<div class="mm-deal-info">' +
      '<b>' + escapeHTML(best.title) + '</b>' +
      '<span>' + inr(best.price) + ' (' + best.discount + '% OFF) on ' + best.store + '</span>' +
      '</div>' +
      '<a class="mm-buy-btn" href="' + escapeHTML(best.url) + '" target="_blank" rel="sponsored noopener noreferrer">' +
      'Claim Deal on ' + best.store + ' ↗' +
      '</a>' +
      '</div>' +
      '</div>'
    );
  }

  // =========================================================================
  // Event Listeners
  // =========================================================================

  function setupEvents() {
    var searchInput = $('search-input');
    var clearBtn = $('search-clear');
    var searchTimer = null;

    if (searchInput) {
      searchInput.oninput = function () {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(function () {
          state.query = searchInput.value;
          state.shownCount = PAGE_SIZE;
          if (clearBtn) clearBtn.style.display = state.query ? 'block' : 'none';
          applyFilters(false);
        }, 120);
      };
    }

    if (clearBtn && searchInput) {
      clearBtn.onclick = function () {
        searchInput.value = '';
        state.query = '';
        clearBtn.style.display = 'none';
        state.shownCount = PAGE_SIZE;
        applyFilters(false);
        searchInput.focus();
      };
    }

    // Section Switcher Tabs on Top (Q-Rated, Hot Drops, Lowest Price, Fastest Fingers)
    document.querySelectorAll('#section-tabs .section-tab-btn').forEach(function (btn) {
      btn.onclick = function () {
        state.section = btn.dataset.section;
        state.shownCount = PAGE_SIZE;
        document.querySelectorAll('#section-tabs .section-tab-btn').forEach(function (b) {
          var isCurrent = b === btn;
          b.classList.toggle('active', isCurrent);
          b.setAttribute('aria-selected', String(isCurrent));
        });
        applyFilters(true);
      };
    });

    // Store pills
    document.querySelectorAll('#store-pills .store-tab-btn').forEach(function (btn) {
      btn.onclick = function () {
        state.store = btn.dataset.store;
        state.shownCount = PAGE_SIZE;
        document.querySelectorAll('#store-pills .store-tab-btn').forEach(function (b) {
          b.classList.toggle('active', b === btn);
        });
        renderCategoryStrip();
        applyFilters(true);
      };
    });

    // Sort select
    var sortSelect = $('sort-select');
    if (sortSelect) {
      sortSelect.onchange = function () {
        state.sort = sortSelect.value;
        state.shownCount = PAGE_SIZE;
        applyFilters(false);
      };
    }

    // Load More button
    var moreBtn = $('btn-more-deals');
    if (moreBtn) {
      moreBtn.onclick = function () {
        state.shownCount += PAGE_SIZE;
        applyFilters(false);
      };
    }

    // Reset all filters button
    var resetBtn = $('btn-reset-filters');
    if (resetBtn) {
      resetBtn.onclick = function () {
        state.query = '';
        if (searchInput) searchInput.value = '';
        if (clearBtn) clearBtn.style.display = 'none';
        state.store = 'all';
        state.category = 'all';
        state.section = 'all';
        state.shownCount = PAGE_SIZE;
        document.querySelectorAll('#section-tabs .section-tab-btn').forEach(function (b) {
          var isAll = b.dataset.section === 'all';
          b.classList.toggle('active', isAll);
          b.setAttribute('aria-selected', String(isAll));
        });
        document.querySelectorAll('#store-pills .store-tab-btn').forEach(function (b) {
          b.classList.toggle('active', b.dataset.store === 'all');
        });
        renderCategoryStrip();
        applyFilters(true);
      };
    }
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadData);
  } else {
    loadData();
  }
})();
