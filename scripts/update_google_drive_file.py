"""Merge new sequence diagrams into an existing user draw.io file,
preserving non-sequence tabs (secarediagram, templet-sequence, UsecaseDiagram, etc.).
"""
import sys, os, re, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RP4_DRAWIO = ROOT / 'RP4' / 'RP4-Detail-Design.drawio'

def update_file(user_file_path):
    user_path = Path(user_file_path)
    if not user_path.exists():
        print(f"File not found: {user_path}")
        return False

    # Load new sequence diagrams from RP4-Detail-Design.drawio
    rp4_tree = ET.parse(RP4_DRAWIO)
    new_pages = rp4_tree.getroot().findall('diagram')
    
    # Map new sequence pages by key
    seq_map = {}
    for p in new_pages:
        pid = p.get('id', '')
        name = p.get('name', '')
        # Check if sequence diagram (id starts with rp4-3. and is not class diagram)
        if pid.startswith('rp4-3.') and 'Class' not in name:
            # Extract section key e.g. '3.1.2', '3.1.2.a', '3.1.3', etc.
            key = pid.replace('rp4-', '')
            seq_map[key] = p
            # Also map by primary section prefix e.g. '3.1.2'
            main_sec = '.'.join(key.split('.')[:3])
            seq_map.setdefault(main_sec, p)

    # Load user's file
    user_tree = ET.parse(user_path)
    user_root = user_tree.getroot()
    user_pages = user_root.findall('diagram')
    
    updated_count = 0
    for p in user_pages:
        name = p.get('name', '').strip()
        # Check if tab name matches a chapter 3 sequence diagram
        # e.g. "3.1.2", "3.1.3", "3.1.4 Process Auto/Manual...", etc.
        m = re.match(r'^(3\.\d+\.\d+)', name)
        if m:
            sec_key = m.group(1)
            # Find matching new sequence
            if sec_key in seq_map and 'Class' not in name:
                new_p = seq_map[sec_key]
                # Replace mxGraphModel of this page
                old_model = p.find('mxGraphModel')
                new_model = new_p.find('mxGraphModel')
                if old_model is not None and new_model is not None:
                    p.remove(old_model)
                    p.append(new_model)
                    updated_count += 1
                    print(f"Updated tab: [{name}] with new sequence for {sec_key}")

    output_path = user_path.parent / (user_path.stem + '_updated' + user_path.suffix)
    user_tree.write(output_path, encoding='utf-8', xml_declaration=True)
    # Also overwrite the original file
    user_tree.write(user_path, encoding='utf-8', xml_declaration=True)
    print(f"\nDone! Successfully updated {updated_count} sequence tabs in {user_path}")
    return True

if __name__ == '__main__':
    if len(sys.argv) > 1:
        update_file(sys.argv[1])
    else:
        print("Usage: python update_google_drive_file.py <path_to_user_drawio_file>")
