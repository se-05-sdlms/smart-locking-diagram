"""Replace each original RP4 Markdown diagram with its native draw.io bundle."""
from pathlib import Path
from datetime import datetime
import copy, hashlib, json, shutil
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
RP4=(ROOT/'RP4').resolve()
master=ET.parse(RP4/'drawio'/'RP4-Detail-Design.drawio').getroot()
originals=sorted(p for p in RP4.glob('3.*/*.md'))
assert originals, 'No original section diagrams found'
mapping=[]
used=set()
for old in originals:
    key=old.name.split(' ',1)[0]
    pages=[p for p in master.findall('diagram') if p.get('id','')=='rp4-'+key or p.get('id','').startswith('rp4-'+key+'.')]
    assert pages, f'No native pages for {old}'
    dest=old.with_suffix('.drawio')
    assert dest.resolve().is_relative_to(RP4)
    document=ET.Element('mxfile',host='app.diagrams.net',type='device',compressed='false')
    for page in pages:
        document.append(copy.deepcopy(page));used.add(page.get('id'))
    ET.indent(document)
    xml=ET.tostring(document,encoding='utf-8',xml_declaration=True)
    if dest.exists():assert dest.read_bytes()==xml, f'Different existing destination: {dest}'
    else:dest.write_bytes(xml)
    assert len(ET.parse(dest).getroot().findall('diagram'))==len(pages)
    mapping.append({'section':key,'file':dest.relative_to(RP4).as_posix(),'pages':len(pages)})
assert used=={p.get('id') for p in master.findall('diagram')}, 'Unmapped master pages'

# Every old file is backed up and hash checked before any Markdown is removed.
markdown=sorted(RP4.rglob('*.md'))
backup=ROOT/'backups'/('RP4-markdown-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True,exist_ok=False)
for old in markdown:
    target=backup/old.relative_to(RP4)
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(old,target)
    assert hashlib.sha256(old.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest()
for old in markdown:
    assert old.resolve().is_relative_to(RP4) and old.suffix=='.md'
    old.unlink()
(ROOT/'scripts'/'rp4-section-files.json').write_text(json.dumps(mapping,indent=2,ensure_ascii=False),encoding='utf8')
assert not list(RP4.rglob('*.md'))
print(json.dumps({'replaced_diagram_files':len(mapping),'native_pages':len(used),'markdown_remaining_in_RP4':0,'backup':str(backup)},indent=2,ensure_ascii=False))
