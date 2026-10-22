"""Automated Draw.io tab updater via Playwright CDP connection to Microsoft Edge.
Connects to Edge running with --remote-debugging-port=9222,
finds the open Draw.io tab, iterates through all sequence tabs,
clears old diagram and imports the new verified drawio file.
"""
import os, sys, re, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / 'RP4' / 'drawio' / 'pages'

def get_matching_file(tab_name):
    """Find the corresponding .drawio file for a given tab name.
    Matches '3.1.2 ...' -> '3.1.2.drawio'
    """
    m = re.match(r'^(3\.\d+\.\d+)', tab_name.strip())
    if not m:
        return None
    sec_key = m.group(1)
    
    # Check if exact file exists
    fpath = PAGES_DIR / f"{sec_key}.drawio"
    if fpath.exists():
        return str(fpath)
    
    # Check if sub-variant exists e.g. 3.1.2.a.drawio
    matches = list(PAGES_DIR.glob(f"{sec_key}*.drawio"))
    if matches:
        return str(matches[0])
    return None

def run_auto_import(port=9222):
    print(f"Connecting to Microsoft Edge at http://localhost:{port}...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(f"http://localhost:{port}")
        except Exception as e:
            print(f"Error: Could not connect to Edge on port {port}.")
            print(f"Please restart Edge with: msedge.exe --remote-debugging-port={port}")
            return False

        drawio_page = None
        for ctx in browser.contexts:
            for page in ctx.pages:
                url = page.url
                title = page.title()
                if "diagrams.net" in url or "draw.io" in url or "Smart Delivery Locker" in title:
                    drawio_page = page
                    break
            if drawio_page:
                break

        if not drawio_page:
            print("Error: Could not find any open Draw.io tab in Edge!")
            print("Please ensure the diagram is open in Edge.")
            browser.close()
            return False

        print(f"Found Draw.io tab: '{drawio_page.title()}'")
        drawio_page.bring_to_front()
        time.sleep(1)

        # Inspect all tabs in geTabScroller
        tabs = drawio_page.evaluate('''() => {
            let scroller = document.querySelector('.geTabScroller');
            if (!scroller) return [];
            let res = [];
            let children = scroller.querySelectorAll('.geTab.gePageTab');
            for (let i = 0; i < children.length; i++) {
                let el = children[i];
                res.push({
                    index: i,
                    text: el.innerText.trim(),
                    title: el.getAttribute('title') || ''
                });
            }
            return res;
        }''')

        print(f"Total tabs in file: {len(tabs)}")
        
        sequence_tabs = []
        for t in tabs:
            txt = t['text']
            # Match section 3 sequence diagrams, exclude Class Diagrams
            if re.match(r'^3\.\d+\.\d+', txt) and 'Class' not in txt:
                target_file = get_matching_file(txt)
                if target_file:
                    sequence_tabs.append((t, target_file))

        print(f"Found {len(sequence_tabs)} Sequence Diagram tabs to update.")
        
        updated_count = 0
        for idx, (t, fpath) in enumerate(sequence_tabs, 1):
            tab_index = t['index']
            tab_name = t['text']
            fname = Path(fpath).name
            print(f"[{idx}/{len(sequence_tabs)}] Updating tab: '{tab_name}' with {fname}...")
            
            try:
                # 1. Click the tab
                drawio_page.evaluate(f'document.querySelectorAll(".geTab.gePageTab")[{tab_index}].click()')
                time.sleep(1)
                
                # 2. Select canvas, select all, delete old diagram
                drawio_page.locator('.geDiagramContainer').click()
                time.sleep(0.3)
                drawio_page.keyboard.press('Control+a')
                time.sleep(0.3)
                drawio_page.keyboard.press('Delete')
                time.sleep(0.3)
                
                # 3. Import new diagram file
                with drawio_page.expect_file_chooser(timeout=5000) as fc_info:
                    # Click File menu
                    drawio_page.locator('a.geItem:has-text("File"), a.geItem:has-text("Tập tin"), a.geItem:has-text("Tệp")').first.click(timeout=2000)
                    time.sleep(0.3)
                    # Hover Import from
                    drawio_page.locator('tr:has-text("Import from"), tr:has-text("Nhập từ")').first.hover(timeout=2000)
                    time.sleep(0.3)
                    # Click Device...
                    drawio_page.locator('tr:has-text("Device..."), tr:has-text("Thiết bị...")').first.click(timeout=2000)
                
                file_chooser = fc_info.value
                file_chooser.set_files(fpath)
                time.sleep(1.5)
                
                # 4. Trigger auto-save
                drawio_page.keyboard.press('Control+s')
                time.sleep(0.5)
                
                updated_count += 1
                print(f"  -> SUCCESS ({updated_count}/{len(sequence_tabs)})")
            except Exception as ex:
                print(f"  -> ERROR on tab '{tab_name}': {ex}")
                time.sleep(1)

        print(f"\n==========================================")
        print(f"COMPLETED: Updated {updated_count}/{len(sequence_tabs)} Sequence Diagram tabs directly in Draw.io!")
        print(f"All changes are saved to Google Drive.")
        print(f"==========================================")
        browser.close()
        return True

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9222
    run_auto_import(port)
