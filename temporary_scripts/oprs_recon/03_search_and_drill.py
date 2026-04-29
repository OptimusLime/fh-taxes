"""OPRS recon v3 — submit search, drill into one parcel's PRC."""
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.goto("https://oprs.co.monmouth.nj.us/oprs/External.aspx?iId=12",
              timeout=30000, wait_until="networkidle")

    inner = page.frames[1]
    print(f"[step 1] form frame: {inner.url}")

    # Select Fair Haven, leave Block 1 / no Lot to get top of list
    inner.select_option("select[name='district']", "1314")
    inner.fill("input[name='block']", "3")
    print("[step 2] form filled: district=1314 block=3")

    # Submit
    inner.locator("input[type='submit']").first.click()
    page.wait_for_load_state("networkidle", timeout=30000)

    # New URL for results
    print(f"[step 3] after submit: {inner.url}")
    page.screenshot(path="/tmp/oprs_results.png", full_page=True)

    # Inspect results — look for parcel link
    links = inner.locator("a").all()
    print(f"[step 4] {len(links)} links on results page")
    for l in links[:20]:
        href = l.get_attribute("href") or ""
        txt = l.inner_text().strip()[:50]
        if href and "prc" in href.lower():
            print(f"   PRC link: text={txt!r} href={href!r}")

    # Capture results table HTML
    body_html = inner.content()
    open("/tmp/oprs_results.html", "w").write(body_html)
    print(f"[step 5] saved /tmp/oprs_results.html ({len(body_html)} bytes)")

    # Pick first parcel link and click it
    prc_links = [l for l in inner.locator("a").all() if "prc" in (l.get_attribute("href") or "").lower()]
    if prc_links:
        first_href = prc_links[0].get_attribute("href")
        print(f"\n[step 6] clicking first PRC link: {first_href}")
        prc_links[0].click()
        page.wait_for_load_state("networkidle", timeout=30000)
        print(f"   PRC page url: {inner.url}")
        page.screenshot(path="/tmp/oprs_prc.png", full_page=True)
        prc_html = inner.content()
        open("/tmp/oprs_prc.html", "w").write(prc_html)
        print(f"   saved /tmp/oprs_prc.html ({len(prc_html)} bytes)")
        # Look for sqft / bedroom / bathroom keywords
        text = inner.inner_text("body")
        for kw in ["SQ FT", "SQFT", "Sq Ft", "BEDROOM", "Bedroom", "BATH", "Bath",
                  "STORIES", "Year Built", "BLDG", "GARAGE", "BASEMENT", "CONDITION"]:
            if kw.lower() in text.lower():
                # Find a snippet around the keyword
                idx = text.lower().find(kw.lower())
                print(f"   FOUND {kw!r}: ...{text[max(0,idx-30):idx+80]}...")

    browser.close()
