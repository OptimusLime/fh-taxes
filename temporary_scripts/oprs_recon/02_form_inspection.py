"""OPRS recon v2 — handle iframe, find FH parcel, fetch PRC."""
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.goto("https://oprs.co.monmouth.nj.us/oprs/External.aspx?iId=12",
              timeout=30000, wait_until="networkidle")

    # Inventory frames
    frames = page.frames
    print(f"[frames] {len(frames)} total")
    for i, f in enumerate(frames):
        print(f"  [{i}] url={f.url!r} name={f.name!r}")

    # Pick the inner frame (not the top-level page)
    inner = next((f for f in frames if f != page.main_frame), None)
    if inner is None:
        # Maybe the form is in main_frame after all but selects loaded async
        page.wait_for_timeout(2000)
        sel_count = page.locator("select").count()
        print(f"[main only] {sel_count} selects after extra wait")
    else:
        print(f"\n[inner frame] using url={inner.url}")
        sel = inner.locator("select").all()
        print(f"  selects: {len(sel)}")
        for i, s in enumerate(sel):
            name = s.get_attribute("name") or s.get_attribute("id") or "?"
            opts = s.locator("option").all()
            sample = [(o.get_attribute("value"), o.inner_text().strip()[:30]) for o in opts[:8]]
            print(f"  [{i}] {name} ({len(opts)} opts) sample={sample}")

        # Look for FAIR HAVEN in district select
        for s in sel:
            opts = s.locator("option").all()
            for o in opts:
                txt = o.inner_text().strip().upper()
                if "FAIR HAVEN" in txt:
                    print(f"\n  >>> FAIR HAVEN found in select {s.get_attribute('name')!r}: "
                          f"value={o.get_attribute('value')!r} text={txt!r}")
                    break

        # Inputs on the form
        inputs = inner.locator("input[type='text']").all()
        print(f"\n  text inputs ({len(inputs)}):")
        for inp in inputs:
            print(f"    name={inp.get_attribute('name')!r} id={inp.get_attribute('id')!r}")

    page.screenshot(path="/tmp/oprs_v2.png", full_page=True)
    browser.close()
