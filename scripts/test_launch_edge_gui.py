import os, time
from playwright.sync_api import sync_playwright

profile_dir = os.path.expanduser(r'~\.drawio_edge_profile')
os.makedirs(profile_dir, exist_ok=True)
print("Profile dir:", profile_dir)

with sync_playwright() as p:
    print("Launching visible Edge browser...")
    context = p.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        channel="msedge",
        headless=False,
        args=["--start-maximized"]
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://app.diagrams.net/#G1CQMDgT2DD_PlF8iHXpRoi-mXsGhgZSAR#%7B%22pageId%22%3A%22HLTxWOecZyikxjDCqCn7%22%7D")
    print("Edge opened to Draw.io! Current URL:", page.url)
    print("Waiting 10 seconds to verify...")
    time.sleep(10)
    context.close()
    print("Closed.")
