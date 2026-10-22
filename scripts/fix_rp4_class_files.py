"""Rebuild and synchronize only Report 4 class-diagram pages.

Sequence and intentionally blank pages are read from their existing files and
left byte-for-byte unchanged. Class pages are regenerated from the current
backend-backed use-case model, then copied into the individual, chapter and
master draw.io containers.
"""

from __future__ import annotations

import copy
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import rp4_native_drawio as native
from rp4_complete_classes import build


ROOT = Path(__file__).resolve().parents[1]
RP4 = ROOT / 'RP4'
DRAWIO = RP4 / 'drawio'


def diagram_for(canvas):
    diagram = ET.Element('diagram', id='rp4-' + canvas.key,
                         name=canvas.key + ' ' + canvas.title)
    diagram.append(copy.deepcopy(canvas.model))
    return diagram


def write_single(path, canvas):
    root = ET.Element('mxfile', host='app.diagrams.net', type='device',
                      version='24.7.17', compressed='false')
    root.append(diagram_for(canvas))
    ET.indent(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def replace_pages(path, canvases):
    tree = ET.parse(path)
    root = tree.getroot()
    replacements = {'rp4-' + key: diagram_for(canvas)
                    for key, canvas in canvases.items()}
    replaced = set()
    for index, page in enumerate(list(root.findall('diagram'))):
        page_id = page.get('id')
        if page_id in replacements:
            root.remove(page)
            root.insert(index, replacements[page_id])
            replaced.add(page_id)
    missing = set(replacements) - replaced
    if missing:
        raise RuntimeError(f'{path}: class pages missing from aggregate: {sorted(missing)}')
    ET.indent(root)
    tree.write(path, encoding='utf-8', xml_declaration=True)


def main():
    native.ALL.clear()
    build({'Canvas': native.Canvas, 'label': native.label})
    classes = {canvas.key: canvas for canvas in native.ALL if canvas.kind == 'class'}
    if len(classes) != 41:
        raise RuntimeError(f'Expected 41 class diagrams, got {len(classes)}')

    mapping = json.loads((ROOT / 'scripts' / 'rp4-section-files.json').read_text(encoding='utf-8'))
    target_by_key = {entry['section']: RP4 / entry['file'] for entry in mapping
                     if entry['section'] in classes}
    if set(target_by_key) != set(classes):
        raise RuntimeError('Class mapping and generated class keys differ')

    for key, canvas in classes.items():
        write_single(target_by_key[key], canvas)
        write_single(DRAWIO / 'pages' / f'{key}.drawio', canvas)

    replace_pages(DRAWIO / 'RP4-Detail-Design.drawio', classes)
    replace_pages(RP4 / 'RP4-Detail-Design.drawio', classes)
    for chapter in range(1, 10):
        chapter_classes = {key: canvas for key, canvas in classes.items()
                           if key.startswith(f'3.{chapter}.')}
        if chapter_classes:
            replace_pages(DRAWIO / f'RP4-3.{chapter}.drawio', chapter_classes)

    print(json.dumps({
        'class_pages': len(classes),
        'individual_files': len(target_by_key),
        'page_files': len(classes),
        'chapter_files': 9,
        'master_files': 2,
    }, indent=2))


if __name__ == '__main__':
    main()
