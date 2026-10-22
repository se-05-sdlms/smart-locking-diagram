from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://app.diagrams.net/?offline=1')
    page.wait_for_timeout(3000)
    
    try:
        page.locator('button:has-text("Decide later")').click(timeout=3000)
    except Exception:
        pass
    page.wait_for_timeout(2000)
    
    cdp = page.context.new_cdp_session(page)
    proto_eval = cdp.send('Runtime.evaluate', {'expression': 'window.App.prototype'})
    proto_id = proto_eval['result']['objectId']
    
    query_res = cdp.send('Runtime.queryObjects', {'prototypeObjectId': proto_id})
    obj_id = query_res['objects']['objectId']
    
    check_eval = cdp.send('Runtime.callFunctionOn', {
        'functionDeclaration': '''function() { 
            let res = [];
            for (let i = 0; i < this.length; i++) {
                let inst = this[i];
                res.push({
                    idx: i,
                    hasPages: !!inst.pages,
                    pagesLength: inst.pages ? inst.pages.length : 0,
                    hasEditor: !!inst.editor,
                    hasSaveFile: typeof inst.saveFile
                });
            }
            return res;
        }''',
        'objectId': obj_id,
        'returnByValue': True
    })
    
    print('queryObjects(App) result:', check_eval['result']['value'])
    browser.close()
