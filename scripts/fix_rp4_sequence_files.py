"""Rebuild and synchronize only Report 4 sequence-diagram pages.

Class and intentionally blank pages remain untouched. Sequence pages are
regenerated from the backend-backed design specification, then replaced in
the section files, individual page files, chapter files and both masters.
"""

from __future__ import annotations

import copy
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import rp4_native_drawio as native
from rp4_design_spec import sequences as sequence_specs


ROOT = Path(__file__).resolve().parents[1]
RP4 = ROOT / 'RP4'
DRAWIO = RP4 / 'drawio'


def natural_key(value: str):
    return tuple(int(part) if part.isdigit() else part
                 for part in re.findall(r'\d+|[a-z]+', value))


def diagram_for(canvas):
    diagram = ET.Element('diagram', id='rp4-' + canvas.key,
                         name=canvas.key + ' ' + canvas.title)
    diagram.append(copy.deepcopy(canvas.model))
    return diagram


def write_file(path: Path, canvases):
    root = ET.Element('mxfile', host='app.diagrams.net', type='device',
                      version='24.7.17', compressed='false')
    for canvas in canvases:
        root.append(diagram_for(canvas))
    ET.indent(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def replace_pages(path: Path, canvases):
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
        raise RuntimeError(f'{path}: sequence pages missing from aggregate: {sorted(missing)}')
    ET.indent(root)
    tree.write(path, encoding='utf-8', xml_declaration=True)


def main():
    native.ALL.clear()
    for spec in sequence_specs:
        native.sequence(spec)
    generated = {canvas.key: canvas for canvas in native.ALL
                 if canvas.kind == 'sequence'}
    if len(generated) != 72:
        raise RuntimeError(f'Expected 72 sequence diagrams, got {len(generated)}')

    mapping = json.loads((ROOT / 'scripts' / 'rp4-section-files.json')
                         .read_text(encoding='utf-8'))
    written_sections = 0
    covered = set()
    for entry in mapping:
        section = entry['section']
        members = [canvas for key, canvas in generated.items()
                   if key == section or key.startswith(section + '.')]
        if not members:
            continue
        members.sort(key=lambda canvas: natural_key(canvas.key))
        write_file(RP4 / entry['file'], members)
        covered.update(canvas.key for canvas in members)
        written_sections += 1

    if covered != set(generated):
        raise RuntimeError('Sequence section mapping and generated keys differ: '
                           f'missing={sorted(set(generated)-covered)}')

    for key, canvas in generated.items():
        write_file(DRAWIO / 'pages' / f'{key}.drawio', [canvas])

    replace_pages(DRAWIO / 'RP4-Detail-Design.drawio', generated)
    replace_pages(RP4 / 'RP4-Detail-Design.drawio', generated)
    for chapter in range(1, 10):
        chapter_pages = {key: canvas for key, canvas in generated.items()
                         if key.startswith(f'3.{chapter}.')}
        if chapter_pages:
            replace_pages(DRAWIO / f'RP4-3.{chapter}.drawio', chapter_pages)

    source_map_path = DRAWIO / 'source-map.json'
    source_map = json.loads(source_map_path.read_text(encoding='utf-8'))
    indexed_pages = {page['key']: page for page in source_map['pages']}
    for key, canvas in generated.items():
        page = indexed_pages[key]
        page.update({
            'title': canvas.title,
            'kind': canvas.kind,
            'file': 'pages/' + key + '.drawio',
            'sources': sorted(set(canvas.sources)),
            'messages': canvas.messages,
        })
    source_map_path.write_text(json.dumps(source_map, indent=2, ensure_ascii=False),
                               encoding='utf-8')

    print(json.dumps({
        'sequence_pages': len(generated),
        'section_files': written_sections,
        'page_files': len(generated),
        'chapter_files': 9,
        'master_files': 2,
    }, indent=2))


if __name__ == '__main__':
    main()
