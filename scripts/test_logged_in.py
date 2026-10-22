import os, time
from playwright.sync_api import sync_playwright

profile = os.path.expanduser(r'~\.drawio_edge_profile')
url = 'https://app.diagrams.net/#G1CQMDgT2DD_PlF8iHXpRoi-mXsGhgZSAR#%7B%22pageId%22%3A%22HLTxWOecZyikxjDCqCn7%22%7D'

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=profile,
        channel='msedge',
        headless=False,
        args=['--start-maximized']
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(url)
    print('Opened Draw.io! Waiting 15s to check if tabs load...')
    
    loaded = False
    for i in range(15):
        time.sleep(1)
        try:
            tab_count = page.evaluate('document.querySelectorAll(".geTabScroller .geTab.gePageTab").length')
            if tab_count > 0:
                print(f'SUCCESS! Detected {tab_count} tabs loaded!')
                loaded = True
                break
        except Exception:
            pass
    if not loaded:
        print('Current page title:', page.title())
        print('Current page URL:', page.url)
    ctx.close()
