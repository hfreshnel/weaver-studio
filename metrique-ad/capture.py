"""Mobile screenshots of MÉTRIQUE pages with Playwright (390x844 @3x).

Usage:
  .venv/bin/python capture.py public [--base https://metriqueservices.org]
  .venv/bin/python capture.py demo --base http://localhost --client-state state_client.json
"""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "assets/screens"
VIEWPORT = {"width": 390, "height": 844}


def context(p, state=None):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=3, is_mobile=True, has_touch=True,
                              locale="fr-FR", color_scheme="light", storage_state=state)
    return browser, ctx


def shot(page, name, full=False):
    page.wait_for_timeout(1200)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
    print("saved", name)


def public(base):
    with sync_playwright() as p:
        browser, ctx = context(p)
        page = ctx.new_page()
        page.goto(base + "/", wait_until="networkidle")
        shot(page, "home_hero")
        shot(page, "home_full", full=True)
        box = page.get_by_role("searchbox").or_(page.locator("input[type=search], input[type=text]")).first
        box.fill("Plomberie")
        shot(page, "home_search_filled")
        page.goto(base + "/services?q=Plomberie", wait_until="networkidle")
        shot(page, "services_plomberie", full=True)
        browser.close()


def demo(base, state, service_id, order_id):
    with sync_playwright() as p:
        browser, ctx = context(p, state)
        page = ctx.new_page()
        page.goto(base + "/services?q=Plomberie", wait_until="networkidle")
        shot(page, "demo_results", full=True)
        page.goto(f"{base}/services/{service_id}", wait_until="networkidle")
        shot(page, "demo_service", full=True)
        if order_id:
            page.goto(f"{base}/orders/{order_id}", wait_until="networkidle")
            shot(page, "demo_order", full=True)
        page.goto(base + "/messages", wait_until="networkidle")
        shot(page, "demo_messages", full=True)
        browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["public", "demo"])
    ap.add_argument("--base", default="https://metriqueservices.org")
    ap.add_argument("--client-state")
    ap.add_argument("--service-id")
    ap.add_argument("--order-id")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.mode == "public":
        public(a.base)
    else:
        demo(a.base, a.client_state, a.service_id, a.order_id)
