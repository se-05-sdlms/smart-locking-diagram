"""Index the actual deliverables and render evidence outside RP4."""
from pathlib import Path
import json,shutil,os
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'RP4'/'drawio'
QA=ROOT/'docs'/'RP4-drawio'/'qa-all-latest'
doc=ROOT/'docs'/'RP4-drawio';doc.mkdir(parents=True,exist_ok=True)
data=json.loads((OUT/'source-map.json').read_text(encoding='utf8'))
sections=json.loads((ROOT/'scripts'/'rp4-section-files.json').read_text(encoding='utf8'))
classes=[p for p in data['pages'] if p['kind']=='class']
sequences=[p for p in data['pages'] if p['kind']=='sequence']
blanks=[p for p in data['pages'] if p['kind']=='blank']
lines=['# RP4 — Native draw.io diagrams','',
       'Class diagrams are split by named use case, using the supplied JLAS XML form. Each contains only the relevant current backend declarations, DTOs and entity fields. No narrative notes or legends are embedded. Sequence files retain their numbered messages and square self-calls.','',
       f"Backend: `{data['backend']}`, branch `{data['branch']}`, commit `{data['commit']}`.",'',
       f"{len(classes)} use-case class pages; {len(sequences)} sequence pages; {len(blanks)} empty page for the unimplemented OCR flow.",'',
       'Open a `.drawio` file through File → Open From → Device in diagrams.net, or import it through File → Import From → Device. All diagrams consist of editable native mxGraph shapes and connectors.','',
       'Within each chapter, class diagrams are numbered first and sequence diagrams follow. The aggregate file is RP4/RP4-Detail-Design.drawio; individual named files are in the RP4 chapter folders.','',
       'Dependency: dashed line / open arrow. Realization: dashed line / hollow triangle. Association: solid line / open arrow, with multiplicities. Composition uses a filled owner diamond; aggregation uses a hollow owner diamond. Constructor injection is not represented as composition. Signatures and types are extracted from C#; CancellationToken is omitted for display. Member scope is explicit in scripts/rp4_usecase_classes.py.','',
       'XML validation checks source hashes, signatures, class scope, numbering, native shapes, square self-calls, overlaps and connectors passing through classes. Native rendering uses mxGraph and draw.io shape definitions; render-check.json records page loading and text clipping. This verifies diagram rendering, not runtime business behavior or hardware.','',
       'Old drafts and original Markdown are preserved outside RP4 in backups. Backend and report documents were not edited.','',
       '## Class diagram files','', '| Section | Use case | File |','|---|---|---|']
for page in classes:
    entry=next(e for e in sections if e['section']==page['key'])
    target=Path(os.path.relpath(ROOT/'RP4'/entry['file'],doc)).as_posix()
    lines.append(f"| {page['key']} | {page['title']} | [draw.io]({target}) |")
(doc/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
shutil.copy2(QA/'render-check.json',OUT/'render-check.json')
for start in range(0,len(classes),9):
    canvas=Image.new('RGB',(1800,1500),'white');draw=ImageDraw.Draw(canvas)
    for k,p in enumerate(classes[start:start+9]):
        im=Image.open(QA/(p['key']+'.png')).convert('RGB');im.thumbnail((575,460))
        x=(k%3)*600+12;y=(k//3)*500+28
        canvas.paste(im,(x+(575-im.width)//2,y));draw.text((x,y-22),p['key']+' '+p['title'],fill='black')
    canvas.save(QA/f'class-contact-{start//9+1}.jpg',quality=92)
print('Use-case index, render ledger and contact sheets written.')
