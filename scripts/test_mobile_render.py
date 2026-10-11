import os
import time
import http.server
import socketserver
import threading
from playwright.sync_api import sync_playwright

PORT = 8999

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, must-revalidate')
        super().end_headers()

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(1)

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge')
    # Emulate Samsung Galaxy / standard Android viewport (360x800)
    context = browser.new_context(
        viewport={'width': 360, 'height': 800},
        user_agent='Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True
    )
    page = context.new_page()
    page.goto(f'http://localhost:{PORT}/index.html')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)

    # Check horizontal overflow
    scroll_w = page.evaluate("() => document.documentElement.scrollWidth")
    inner_w = page.evaluate("() => window.innerWidth")
    body_scroll_w = page.evaluate("() => document.body.scrollWidth")
    print(f"Viewport width: {inner_w}, document.scrollWidth: {scroll_w}, body.scrollWidth: {body_scroll_w}")

    # Check if elements overflow
    overflowing = page.evaluate("""() => {
        const elements = document.querySelectorAll('*');
        const bad = [];
        for (const el of elements) {
            const rect = el.getBoundingClientRect();
            if (rect.right > window.innerWidth + 1) {
                bad.push({tag: el.tagName, class: el.className, id: el.id, right: rect.right, width: rect.width});
            }
        }
        return bad.slice(0, 10);
    }""")
    print("Overflowing elements count:", len(overflowing))
    for item in overflowing:
        print("  ->", item)

    page.screenshot(path="C:/Users/varun/.gemini/antigravity/brain/6e34fcee-51c4-40e9-b0e6-db9597fc07f4/diag_mobile_top.png")

    # Scroll down 400px
    page.evaluate("window.scrollTo(0, 400)")
    page.wait_for_timeout(500)
    page.screenshot(path="C:/Users/varun/.gemini/antigravity/brain/6e34fcee-51c4-40e9-b0e6-db9597fc07f4/diag_mobile_scrolled.png")

    # Scroll down 1200px
    page.evaluate("window.scrollTo(0, 1200)")
    page.wait_for_timeout(500)
    page.screenshot(path="C:/Users/varun/.gemini/antigravity/brain/6e34fcee-51c4-40e9-b0e6-db9597fc07f4/diag_mobile_scrolled_more.png")

    # Test clicking floating top button
    page.click("#btn-floating-top")
    page.wait_for_timeout(800)
    page.screenshot(path="C:/Users/varun/.gemini/antigravity/brain/6e34fcee-51c4-40e9-b0e6-db9597fc07f4/diag_mobile_returned_top.png")

    # Toggle Dark Mode
    page.click("#theme-toggle")
    page.wait_for_timeout(400)
    page.screenshot(path="C:/Users/varun/.gemini/antigravity/brain/6e34fcee-51c4-40e9-b0e6-db9597fc07f4/diag_mobile_dark_top.png")

    # Scroll down in Dark Mode
    page.evaluate("window.scrollTo(0, 600)")
    page.wait_for_timeout(500)
    page.screenshot(path="C:/Users/varun/.gemini/antigravity/brain/6e34fcee-51c4-40e9-b0e6-db9597fc07f4/diag_mobile_dark_scrolled.png")

    browser.close()

print("Diagnostic run complete!")
