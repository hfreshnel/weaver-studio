"""Log a demo user into the local stack and save the browser state.

Usage: .venv/bin/python seed/login.py demo.cliente [path-to-open]
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://localhost:3000"
PASSWORD = "DemoMetrique2026!"


UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/131.0.0.0 Mobile Safari/537.36")


def reroute(ctx):
    # The app treats headless Chrome as its prerenderer (no Keycloak); look like a regular mobile browser.
    ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => false})")
    # The SPA calls http://localhost/api (WAF); locally the backend is exposed on :8000.
    ctx.route("http://localhost/api/**", lambda r: r.continue_(url=r.request.url.replace("http://localhost/api", "http://localhost:8000/api", 1)))


def login(p, user):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True,
                              has_touch=True, locale="fr-FR", color_scheme="light", user_agent=UA)
    reroute(ctx)
    page = ctx.new_page()
    page.goto(BASE + "/", wait_until="networkidle")
    page.locator("button:has-text('Connexion'):visible, a:has-text('Connexion'):visible").first.click()
    page.wait_for_url("**/realms/**", timeout=20000)
    page.locator("input[name=username]").fill(user)
    page.locator("input[name=password]").fill(PASSWORD)
    page.locator("input[name=password]").press("Enter")
    page.wait_for_url(BASE + "/**", timeout=20000)
    page.wait_for_load_state("networkidle")
    return browser, ctx, page


if __name__ == "__main__":
    user = sys.argv[1]
    with sync_playwright() as p:
        browser, ctx, page = login(p, user)
        if len(sys.argv) > 2:
            page.goto(BASE + sys.argv[2], wait_until="networkidle")
        page.wait_for_timeout(1500)
        out = ROOT / "out" / f"login_{user}.png"
        page.screenshot(path=str(out))
        ctx.storage_state(path=str(ROOT / "seed" / f"state_{user}.json"))
        print(page.url, out)
        browser.close()
