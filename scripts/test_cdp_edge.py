import sys
from playwright.sync_api import sync_playwright

def test_connection():
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            print("Connected to Edge successfully!")
            contexts = browser.contexts
            print(f"Contexts count: {len(contexts)}")
            for ctx in contexts:
                for page in ctx.pages:
                    print(f" - Page: {page.title()} | URL: {page.url}")
            browser.close()
            return True
    except Exception as e:
        print(f"Cannot connect to Edge: {e}")
        return False

if __name__ == "__main__":
    test_connection()
