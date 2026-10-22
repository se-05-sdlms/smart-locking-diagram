import os, sys, re, time
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(line_buffering=True)

ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / 'RP4' / 'drawio' / 'pages'
PROFILE_DIR = os.path.expanduser(r'~\.drawio_edge_profile')
os.makedirs(PROFILE_DIR, exist_ok=True)

TARGET_URL = "https://app.diagrams.net/#G1CQMDgT2DD_PlF8iHXpRoi-mXsGhgZSAR#%7B%22pageId%22%3A%22HLTxWOecZyikxjDCqCn7%22%7D"

def get_matching_file(tab_name):
    m = re.match(r'^(3\.\d+\.\d+)', tab_name.strip())
    if not m:
        return None
    sec_key = m.group(1)
    
    fpath = PAGES_DIR / f"{sec_key}.drawio"
    if fpath.exists():
        return str(fpath)
    
    matches = list(PAGES_DIR.glob(f"{sec_key}*.drawio"))
    if matches:
        return str(matches[0])
    return None

def main():
    print("=" * 60, flush=True)
    print("KHOI DONG TRINH DUYET DRAW.IO TU DONG", flush=True)
    print("=" * 60, flush=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            channel="msedge",
            headless=False,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(TARGET_URL)
        print("Da mo link Draw.io!", flush=True)

        clicked_auth = False
        doc_opened = False
        start_time = time.time()
        
        while time.time() - start_time < 600:
            # Handle Google Sign In popups
            if len(context.pages) > 1:
                for popup in context.pages[1:]:
                    try:
                        p_url = popup.url
                        p_title = popup.title()
                        if "accounts.google.com" in p_url:
                            popup.bring_to_front()
                            # Check for clickable accounts
                            acc_items = popup.locator('[data-email], [data-identifier], li[role="link"], div[role="link"]:has-text("@")')
                            if acc_items.count() > 0 and acc_items.first.is_visible():
                                print("Tu dong chon tai khoan Google trong popup...", flush=True)
                                acc_items.first.click()
                                time.sleep(2)
                            
                            # Check for Continue / Allow buttons
                            cont_btn = popup.locator('button:has-text("Continue"), button:has-text("Tiếp tục"), button:has-text("Allow"), button:has-text("Cho phép")')
                            if cont_btn.count() > 0 and cont_btn.first.is_visible():
                                print("Tu dong bam nut Tiep tuc/Cho phep trong popup...", flush=True)
                                cont_btn.first.click()
                                time.sleep(2)
                    except Exception as e_pop:
                        pass

            # Check for Authorize button on main page
            if not clicked_auth:
                try:
                    auth_btn = page.locator('button:has-text("Authorize"), button:has-text("Ủy quyền")')
                    if auth_btn.count() > 0 and auth_btn.first.is_visible():
                        print("Tu dong bam nut Authorize...", flush=True)
                        auth_btn.first.click()
                        clicked_auth = True
                        time.sleep(2)
                except Exception as e:
                    pass

            # Check if document tabs are loaded
            try:
                count = page.evaluate('document.querySelectorAll(".geTabScroller .geTab.gePageTab").length')
                if count > 0:
                    doc_opened = True
                    break
            except Exception:
                pass
            time.sleep(1.5)

        if not doc_opened:
            print("Het thoi gian cho mo tai lieu.", flush=True)
            context.close()
            return

        print("TAI LIEU DA MO THANH CONG! Phat hien cac tab ve.", flush=True)
        page.bring_to_front()
        time.sleep(2)

        tabs = page.evaluate('''() => {
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

        print(f"Phat hien tong cong {len(tabs)} tabs trong tai lieu.", flush=True)

        sequence_tabs = []
        for t in tabs:
            txt = t['text']
            if re.match(r'^3\.\d+\.\d+', txt) and 'Class' not in txt:
                target_file = get_matching_file(txt)
                if target_file:
                    sequence_tabs.append((t, target_file))

        print(f"Xac dinh duoc {len(sequence_tabs)} tabs Sequence Diagram can cap nhat.", flush=True)
        print("BAT DAU IMPORT TU DONG VA LUU TRUC TIEP...", flush=True)
        print("=" * 60, flush=True)

        updated_count = 0
        for idx, (t, fpath) in enumerate(sequence_tabs, 1):
            tab_index = t['index']
            tab_name = t['text']
            fname = Path(fpath).name
            print(f"[{idx}/{len(sequence_tabs)}] Dang cap nhat: '{tab_name}' -> {fname}...", flush=True)

            try:
                # 1. Click tab
                page.evaluate(f'document.querySelectorAll(".geTab.gePageTab")[{tab_index}].click()')
                time.sleep(1.2)

                # 2. Clear old diagram
                try:
                    page.locator('.geDiagramContainer').click(timeout=2000)
                    time.sleep(0.3)
                    page.keyboard.press('Control+a')
                    time.sleep(0.3)
                    page.keyboard.press('Delete')
                    time.sleep(0.3)
                except Exception:
                    pass

                # 3. Import new diagram
                with page.expect_file_chooser(timeout=6000) as fc_info:
                    page.locator('a.geItem:has-text("File"), a.geItem:has-text("Tập tin"), a.geItem:has-text("Tệp")').first.click(timeout=2000)
                    time.sleep(0.3)
                    page.locator('tr:has-text("Import from"), tr:has-text("Nhập từ")').first.hover(timeout=2000)
                    time.sleep(0.3)
                    page.locator('tr:has-text("Device..."), tr:has-text("Thiết bị...")').first.click(timeout=2000)

                file_chooser = fc_info.value
                file_chooser.set_files(fpath)
                time.sleep(1.5)

                # 4. Save
                page.keyboard.press('Control+s')
                time.sleep(0.5)

                updated_count += 1
                print(f"   -> THANH CONG ({updated_count}/{len(sequence_tabs)})", flush=True)
            except Exception as ex:
                print(f"   -> LOI o tab '{tab_name}': {ex}", flush=True)
                time.sleep(1)

        print("=" * 60, flush=True)
        print(f"HOAN TAT! Da cap nhat {updated_count}/{len(sequence_tabs)} tabs Sequence Diagram!", flush=True)
        print("Toan bo da duoc luu truc tiep len Google Drive cua Leader.", flush=True)
        print("Trinh duyet se duoc giu nguyen tren man hinh de ban kiem tra.", flush=True)
        print("=" * 60, flush=True)

        while True:
            time.sleep(10)

if __name__ == '__main__':
    main()
