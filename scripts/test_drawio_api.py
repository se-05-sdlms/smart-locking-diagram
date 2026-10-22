from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://app.diagrams.net/?offline=1')
    page.wait_for_timeout(3000)
    
    try:
        page.locator('button:has-text("Decide later")').click(timeout=3000)
    except:
        pass
    page.wait_for_timeout(2000)
    
    listeners = page.evaluate('''() => {
        let el = document.querySelector('.geDiagramContainer');
        let list = el.mxListenerList || [];
        let res = [];
        for (let item of list) {
            res.push({
                name: item.name,
                fntype: typeof item.f,
                fnstr: item.f ? item.f.toString().substring(0, 100) : ''
            });
        }
        return res;
    }''')
    print('mxListenerList items:', listeners)
    browser.close()
