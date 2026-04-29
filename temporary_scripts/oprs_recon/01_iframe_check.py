"""OPRS Property Record Card recon — single Fair Haven parcel.
Goal: see whether sqft/bedrooms/bathrooms appear as parseable HTML.
"""
from playwright.sync_api import sync_playwright
import sys, time

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 900})
    page = ctx.new_page()

    # Entry: assessment & sales lookup
    url = "https://oprs.co.monmouth.nj.us/oprs/External.aspx?iId=12"
    print(f"[1] GET {url}")
    page.goto(url, timeout=30000, wait_until="networkidle")
    print(f"    title={page.title()!r}")

    # Look for municipality dropdown
    selects = page.locator("select").all()
    print(f"[2] found {len(selects)} <select> elements")
    for i, s in enumerate(selects):
        try:
            name = s.get_attribute("name") or "?"
            opts = s.locator("option").all()
            sample = [o.inner_text()[:40] for o in opts[:5]]
            print(f"    select[{i}] name={name!r} opts={len(opts)} sample={sample}")
        except Exception as e:
            print(f"    select[{i}] err {e}")

    # Take a screenshot for visual confirmation
    page.screenshot(path="/tmp/oprs_landing.png", full_page=True)
    print(f"[3] screenshot saved /tmp/oprs_landing.png")

    # Find any link/button text on page
    body_text = page.inner_text("body")[:1500]
    print(f"[4] body text excerpt:\n{body_text}")

    browser.close()
