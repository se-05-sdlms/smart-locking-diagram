from playwright.sync_api import sync_playwright
import os

test_file = r'D:\diagram_capstone\smart-locking-diagram\RP4\drawio\pages\3.1.6.drawio'
print('Test file exists:', os.path.exists(test_file))

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
    
    # Let's test triggering File -> Import from -> Device
    # Or using expect_file_chooser
    try:
        with page.expect_file_chooser(timeout=5000) as fc_info:
            # Click File menu -> Import from -> Device
            # Let's see if we can trigger the action via menu or key
            # In draw.io, menu item 'Import from' -> 'Device...'
            page.locator('a.geItem:has-text("File")').click(timeout=2000)
            page.wait_for_timeout(500)
            # Find Import from
            page.locator('tr:has-text("Import from")').hover(timeout=2000)
            page.wait_for_timeout(500)
            page.locator('tr:has-text("Device...")').click(timeout=2000)
        
        file_chooser = fc_info.value
        file_chooser.set_files(test_file)
        print('Successfully selected file via file chooser!')
        page.wait_for_timeout(3000)
        
        # Check if cells were imported
        cell_count = page.evaluate('document.querySelectorAll(".geDiagramContainer svg g").length')
        print('SVG elements after import:', cell_count)
    except Exception as e:
        print('Error:', type(e), e)
    
    browser.close()
