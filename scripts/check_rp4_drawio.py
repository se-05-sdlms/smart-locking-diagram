"""Semantic / XML checks for the native Report 4 deliverable."""
from pathlib import Path
import xml.etree.ElementTree as E
import json,re,hashlib
from rp4_design_spec import sequences, class_specs, blank_sections, BE
from rp4_usecase_classes import build_usecases,OWNERSHIP_RELATIONS

OUT=Path(__file__).resolve().parents[1]/'RP4'/'drawio'
errors=[]
def check(ok,msg):
    if not ok:errors.append(msg)
source_class_models=build_usecases()
entity_views={}
for model in source_class_models:
    for node in model['nodes']:
        if node['role']!='entity':continue
        signature=tuple(node['attributes'])
        if node['name'] in entity_views:
            check(entity_views[node['name']]==signature,node['name']+': inconsistent attributes across class diagrams')
        else:entity_views[node['name']]=signature
root=E.parse(OUT/'RP4-Detail-Design.drawio').getroot()
pages=root.findall('diagram')
keys={p.get('id').replace('rp4-','') for p in pages}
counts={'pages':len(pages),'sequences':0,'classes':0,'blank':0,'messages':0,'square_self_messages':0,'top_participants':0,'bottom_participants':0,'bottom_actors':0,'class_relationships':0,'backend_types':0,'http_endpoints':0,'target_methods':0}
sequence_by_key={spec['key']:spec for spec in sequences}
page_kinds=[]
for p in pages:
    key=p.get('id').replace('rp4-','');cells=p.findall('.//mxCell');ids=[x.get('id') for x in cells]
    check(re.fullmatch(r'3\.\d+\.\d+',key) is not None,key+': section number must be numeric only')
    check(len(ids)==len(set(ids)),key+': duplicate cell ids')
    native=list(p.find('mxGraphModel/root'))
    check(p.find('mxGraphModel') is not None,key+': missing native model')
    check(p.find('mxGraphModel').get('background')=='#FFFFFF',key+': page background is not white')
    values='\n'.join((cell.get('value') or '') for cell in cells)
    for cell in cells:
        value=cell.get('value') or ''
        is_application_db_class=cell.get('umlRole')=='classBox' and cell.get('className')=='ApplicationDbContext'
        is_application_db_participant=cell.get('umlRole')=='participantHead' and value.endswith('<br>ApplicationDbContext')
        if is_application_db_class or is_application_db_participant:
            check('«database»' in value,key+': ApplicationDbContext must use database stereotype')
    check('REPORT 4' not in values,key+': redundant report header remains')
    check('Call: solid' not in values,key+': redundant message legend remains')
    used_colors={color.upper() for cell in cells for color in re.findall(r'#[0-9A-Fa-f]{6}',cell.get('style') or '')}
    check(used_colors <= {'#000000','#FFFFFF'},key+': non-monochrome colors remain: '+str(sorted(used_colors-{'#000000','#FFFFFF'})))
    check(not p.findall('.//*[@mermaid]'),key+': unexpected Mermaid metadata')
    if key in dict(blank_sections):
        counts['blank']+=1;page_kinds.append((key,'blank'))
        check(len(cells)==2,key+': expected an intentionally empty page')
        continue
    relationships=[c for c in cells if c.get('umlRole')=='classRelationship']
    if relationships:
        counts['classes']+=1
        page_kinds.append((key,'class'))
        relationship_labels={c.get('edgeId'):c for c in cells if c.get('umlRole')=='relationshipLabel'}
        # Compartments of distinct class boxes must not collide.
        compartments=[c for c in cells if c.get('umlRole') in ('classCompartment','classBox')]
        relationship_segments=[]
        for i,a in enumerate(compartments):
            ga=a.find('mxGeometry');ax,ay,aw,ah=[float(ga.get(x)) for x in ('x','y','width','height')]
            for b in compartments[i+1:]:
                if a.get('className')==b.get('className'):continue
                gb=b.find('mxGeometry');bx,by,bw,bh=[float(gb.get(x)) for x in ('x','y','width','height')]
                check(not (ax<bx+bw and bx<ax+aw and ay<by+bh and by<ay+ah),key+': overlapping class '+a.get('className')+' / '+b.get('className'))
        for r in relationships:
            counts['class_relationships']+=1
            style=r.get('style');kind=r.get('relationship')
            if kind=='dependency':check('dashed=1;' in style and 'endArrow=open;' in style,key+': invalid dependency')
            if kind=='realization':check('dashed=1;' in style and 'endArrow=block;' in style and 'endFill=0;' in style,key+': invalid realization')
            if kind=='association':check('dashed=0;' in style and 'endArrow=open;' in style and 'endFill=0;' in style,key+': invalid association')
            if kind=='composition':check('dashed=0;' in style and 'startArrow=diamond;' in style and 'startFill=1;' in style and 'endArrow=none;' in style,key+': invalid composition')
            if kind=='aggregation':check('dashed=0;' in style and 'startArrow=diamond;' in style and 'startFill=0;' in style and 'endArrow=none;' in style,key+': invalid aggregation')
            ownership=OWNERSHIP_RELATIONS.get(frozenset((r.get('fromClass'),r.get('toClass'))))
            if ownership:
                owner,part,expected_kind,caption=ownership
                check((r.get('fromClass'),r.get('toClass'),kind)==(owner,part,expected_kind),key+': incorrect ownership direction/type '+str((r.get('fromClass'),r.get('toClass'),kind)))
                check(r.get('relationshipCaption')==caption,key+': incorrect ownership message')
            check(bool(r.get('relationshipCaption')) and r.get('id') in relationship_labels,key+': missing class relationship message')
            g=r.find('mxGeometry')
            pts=[g.find('mxPoint[@as="sourcePoint"]'),*g.findall('Array/mxPoint'),g.find('mxPoint[@as="targetPoint"]')]
            numeric=[(float(p.get('x')),float(p.get('y'))) for p in pts]
            relationship_segments.extend((r.get('id'),a,b) for a,b in zip(numeric,numeric[1:]))
            for a,b in zip(pts,pts[1:]):check(float(a.get('x'))==float(b.get('x')) or float(a.get('y'))==float(b.get('y')),key+': diagonal class connector')
            for a,b in zip(pts,pts[1:]):
                x1,y1,x2,y2=[float(v) for v in (a.get('x'),a.get('y'),b.get('x'),b.get('y'))]
                for box in compartments:
                    bg=box.find('mxGeometry');bx,by,bw,bh=[float(bg.get(v)) for v in ('x','y','width','height')]
                    intersects=(x1==x2 and bx<x1<bx+bw and max(min(y1,y2),by)<min(max(y1,y2),by+bh)) or (y1==y2 and by<y1<by+bh and max(min(x1,x2),bx)<min(max(x1,x2),bx+bw))
                    check(not intersects,key+': connector crosses '+box.get('className'))
        for i,(edge_a,a,b) in enumerate(relationship_segments):
            for edge_b,c,d in relationship_segments[i+1:]:
                if edge_a==edge_b:continue
                horizontal=a[1]==b[1]==c[1]==d[1] and min(max(a[0],b[0]),max(c[0],d[0]))>max(min(a[0],b[0]),min(c[0],d[0]))
                vertical=a[0]==b[0]==c[0]==d[0] and min(max(a[1],b[1]),max(c[1],d[1]))>max(min(a[1],b[1]),min(c[1],d[1]))
                check(not (horizontal or vertical),key+': overlapping connector segments')
        multiplicities=[c for c in cells if c.get('umlRole')=='multiplicity']
        for m in multiplicities:
            check(m.get('value') in ('1','0..1','0..*','1..*'),key+': invalid multiplicity '+str(m.get('value')))
            check(bool(m.get('edgeId')) and bool(m.get('className')),key+': unbound multiplicity')
            mg=m.find('mxGeometry');mx,my,mw,mh=[float(mg.get(x)) for x in ('x','y','width','height')]
            for edge_id,a,b in relationship_segments:
                if edge_id!=m.get('edgeId'):continue
                covers_horizontal=a[1]==b[1] and my<a[1]<my+mh and max(min(a[0],b[0]),mx)<min(max(a[0],b[0]),mx+mw)
                covers_vertical=a[0]==b[0] and mx<a[0]<mx+mw and max(min(a[1],b[1]),my)<min(max(a[1],b[1]),my+mh)
                check(not (covers_horizontal or covers_vertical),key+': multiplicity covers its connector')
        for i,a in enumerate(multiplicities):
            ga=a.find('mxGeometry');ax,ay,aw,ah=[float(ga.get(x)) for x in ('x','y','width','height')]
            for b in multiplicities[i+1:]:
                gb=b.find('mxGeometry');bx,by,bw,bh=[float(gb.get(x)) for x in ('x','y','width','height')]
                check(not (ax<bx+bw and bx<ax+aw and ay<by+bh and by<ay+ah),key+': overlapping multiplicities')
        for annotation in [*relationship_labels.values(),*multiplicities]:
            ag=annotation.find('mxGeometry');ax,ay,aw,ah=[float(ag.get(x)) for x in ('x','y','width','height')]
            for _,a,b in relationship_segments:
                covers_horizontal=a[1]==b[1] and ay<a[1]<ay+ah and max(min(a[0],b[0]),ax)<min(max(a[0],b[0]),ax+aw)
                covers_vertical=a[0]==b[0] and ax<a[0]<ax+aw and max(min(a[1],b[1]),ay)<min(max(a[1],b[1]),ay+ah)
                check(not (covers_horizontal or covers_vertical),key+': relationship annotation covers connector')
    else:
        counts['sequences']+=1
        page_kinds.append((key,'sequence'))
        spec=sequence_by_key.get(key)
        check(spec is not None,key+': missing sequence specification')
        heads=[c for c in cells if c.get('umlRole')=='participantHead']
        labels_by_participant=[c for c in cells if c.get('umlRole')=='participantLabel']
        lifelines=[c for c in cells if c.get('umlRole')=='lifeline']
        counts['top_participants']+=len([c for c in heads if c.get('position')=='top'])
        counts['bottom_participants']+=len([c for c in heads if c.get('position')=='bottom'])
        counts['bottom_actors']+=len([c for c in heads if c.get('position')=='bottom' and c.get('participantRole')=='actor'])
        if spec is not None:
            expected_participants={item[0]:item[2] for item in spec['participants']}
            check(any(role=='actor' for role in expected_participants.values()),key+': sequence has no actor')
            allowed_actors={'Shipper','Resident','Locker Operator','Administrator'}
            actual_actors={item[1] for item in spec['participants'] if item[2]=='actor'}
            check(actual_actors <= allowed_actors,key+': technical or undefined actor: '+str(sorted(actual_actors-allowed_actors)))
            check(not any(step[0]=='ref' for step in spec['steps']),key+': ref frame remains in sequence')
            for pid,role in expected_participants.items():
                top=[c for c in heads if c.get('participant')==pid and c.get('position')=='top']
                bottom=[c for c in heads if c.get('participant')==pid and c.get('position')=='bottom']
                line=[c for c in lifelines if c.get('participant')==pid]
                check(len(top)==1,key+': missing/duplicate top participant '+pid)
                check(len(bottom)==1,key+': missing/duplicate bottom participant '+pid)
                check(len(line)==1,key+': missing/duplicate lifeline '+pid)
                if top:check(top[0].get('participantRole')==role,key+': wrong top role '+pid)
                if bottom:check(bottom[0].get('participantRole')==role,key+': wrong bottom role '+pid)
                if line and bottom:
                    target=line[0].find('mxGeometry/mxPoint[@as="targetPoint"]')
                    bottom_geometry=bottom[0].find('mxGeometry')
                    check(float(target.get('y'))==float(bottom_geometry.get('y')),key+': lifeline misses bottom participant '+pid)
                actor_labels=[c for c in labels_by_participant if c.get('participant')==pid]
                check(len(actor_labels)==(2 if role=='actor' else 0),key+': incorrect repeated actor labels '+pid)
            check(len(heads)==2*len(expected_participants),key+': participant head count mismatch')
        messages=[c for c in cells if c.get('umlRole') in ('message','selfMessage')]
        expected=['1.']+[f'1.{i}' for i in range(1,len(messages))]
        check([c.get('messageNumber') for c in messages]==expected,key+': numbering gap')
        labels=[c for c in cells if c.get('umlRole')=='messageLabel']
        check(len(labels)==len(messages),key+': missing message labels')
        for r in messages:
            counts['messages']+=1
            if r.get('messageKind')=='async':
                style=r.get('style') or ''
                check('dashed=0;' in style and 'endArrow=open;' in style,key+': invalid async message')
            if r.get('umlRole')=='selfMessage':
                counts['square_self_messages']+=1
                check('curved=0;' in r.get('style') and 'rounded=0;' in r.get('style'),key+': curved self-call')
                points=r.findall('mxGeometry/Array/mxPoint')
                check(len(points)==2,key+': self-call must have two square waypoints')
                check(float(points[0].get('x'))==float(points[1].get('x')),key+': self-call not orthogonal')
        # All message labels must stay above their line and inside the page.
        for l,m in zip(labels,messages):
            g=l.find('mxGeometry');ey=float(m.find('mxGeometry/mxPoint[@as="sourcePoint"]').get('y'))
            check(float(g.get('width'))>=80 and float(g.get('height'))>0,key+': insufficient message label space')
            check(float(g.get('y'))+float(g.get('height'))<=ey-6,key+': label touches line')
    single=E.parse(OUT/'pages'/(key+'.drawio')).getroot()
    check(len(single.findall('diagram'))==1,key+': incorrect single-page export')

# Within each chapter, every class diagram must appear before its sequence
# diagrams.  Numeric section identifiers must also be consecutive.
for chapter in range(1,10):
    chapter_pages=[(key,kind) for key,kind in page_kinds if key.startswith(f'3.{chapter}.')]
    indices=[int(key.rsplit('.',1)[1]) for key,_ in chapter_pages]
    check(indices==list(range(1,len(indices)+1)),f'3.{chapter}: non-consecutive page numbering')
    seen_sequence=False
    for key,kind in chapter_pages:
        if kind=='sequence':seen_sequence=True
        if kind=='class':check(not seen_sequence,key+': class diagram appears after a sequence diagram')

backend_sources={p:p.read_text(encoding='utf-8-sig') for p in BE.rglob('*.cs') if not any(x in p.parts for x in ('bin','obj','Migrations'))}
type_sources={}
for path,source in backend_sources.items():
    for declaration in re.findall(r'\b(?:class|interface|record)\s+(\w+)',source):
        type_sources.setdefault(declaration,[]).append((path,source))

def normalized_route(path):
    path=path.split('?',1)[0].rstrip(';,')
    path=re.sub(r'\{[^}:]+(?::[^}]+)?\}','{}',path)
    return path.lower().rstrip('/') or '/'

def controller_routes(controller):
    declarations=type_sources.get(controller,[])
    check(bool(declarations),controller+': controller declaration not found')
    if not declarations:return []
    source=declarations[0][1]
    route_match=re.search(r'\[ApiController[^\]]*?Route\("([^"]+)"\)[^\]]*\]|\[Route\("([^"]+)"\)\]',source,re.S)
    base=next((value for value in route_match.groups() if value),'') if route_match else ''
    base=base.replace('[controller]',controller[:-10])
    result=[]
    for match in re.finditer(r'Http(Get|Post|Put|Patch|Delete)(?:\("([^"]*)"\))?',source,re.I):
        verb=match.group(1).upper();suffix=match.group(2) or ''
        full=suffix if suffix.startswith('/') else ('/'+suffix.strip('/') if not base else '/'+base.strip('/')+('/'+suffix.strip('/') if suffix else ''))
        result.append((verb,normalized_route(full)))
    return result

for spec in sequences:
    source='\n'.join((BE/p).read_text(encoding='utf-8-sig') for p in spec['sources'])
    participants={p[0]:p for p in spec['participants']}
    for _,name,role in spec['participants']:
        if role not in ('controller','service','interface','persistence','database','worker','hub'):continue
        for type_name in (part.strip() for part in name.split('/')):
            counts['backend_types']+=1
            check(type_name in type_sources,spec['key']+': participant type not found in backend: '+type_name)
    for step in spec['steps']:
        if step[0] not in ('frame','else','end','ref'):
            for method in re.findall(r'\b([A-Z]\w*Async)\(',step[2]):
                check(re.search(r'\b'+method+r'\s*\(',source) is not None,spec['key']+': method not found in cited source: '+method)
            direct_method=re.match(r'^([A-Z]\w*)\s*\(',step[2])
            if direct_method and participants[step[1]][2] in ('controller','service','interface','persistence','database','worker','hub'):
                counts['target_methods']+=1
                target_name=participants[step[1]][1]
                target_source='\n'.join(item[1] for name in target_name.split('/') for item in type_sources.get(name.strip(),[]))
                check(re.search(r'\b'+re.escape(direct_method.group(1))+r'\s*\(',target_source) is not None,
                      spec['key']+': target method not found on '+target_name+': '+direct_method.group(1))
            if step[3]=='http' and participants[step[1]][2]=='controller':
                endpoint=re.match(r'(GET|POST|PUT|PATCH|DELETE)\s+(\/\S+)',step[2])
                check(endpoint is not None,spec['key']+': malformed HTTP message: '+step[2])
                if endpoint:
                    counts['http_endpoints']+=1
                    expected=(endpoint.group(1),normalized_route(endpoint.group(2).split(';')[0]))
                    controller=participants[step[1]][1]
                    check(expected in controller_routes(controller),spec['key']+': endpoint not found on '+controller+': '+str(expected))
        elif step[0]=='ref':
            for ref in re.findall(r'\b3\.\d+\.\d+(?:\.[a-z])?\b',step[1]):check(ref in keys,spec['key']+': broken reference '+ref)
    actors={p[0] for p in spec['participants'] if p[2]=='actor'}
    infrastructure_actors={p[0] for p in spec['participants'] if p[2]=='actor' and p[1] in ('System Scheduler','Locker IoT System')}
    boundaries={p[0] for p in spec['participants'] if p[2]=='boundary'}
    for step in spec['steps']:
        if step[0] in actors-infrastructure_actors and step[1] not in actors:
            check(step[1] in boundaries or next(p[2] for p in spec['participants'] if p[0]==step[1])=='device',spec['key']+': human bypasses boundary')

# The approved scope is per named use case; narrative annotations are forbidden.
from rp4_usecase_classes import build_usecases
models=build_usecases()
for m in models:
    key=m['key'];page=next((p for p in pages if p.get('id')=='rp4-'+key),None)
    check(page is not None,key+': missing use-case class page')
    if page is None:continue
    boxes=page.findall('.//mxCell[@umlRole="classBox"]')
    check({b.get('className') for b in boxes}=={n['name'] for n in m['nodes']},key+': incorrect use-case class scope')
    check(not page.findall('.//mxCell[@umlRole="comment"]') and not page.findall('.//mxCell[@umlRole="legend"]'),key+': unwanted annotation')
    check(len(boxes)<=14,key+': split this view into smaller use cases')
    for box in boxes:
        check('fontSize=9.5;' in (box.get('style') or '') and 'fillColor=#FFFFFF;' in (box.get('style') or '') and 'strokeColor=#000000;' in (box.get('style') or ''),key+': class box is not monochrome')
        check('AuthServiceImpl' not in box.get('className',''),key+': foreign reference class leaked into BE diagram')
    for n in m['nodes']:
        check(bool(n['sources']),key+': missing C# source for '+n['name'])
        for op in n['operations']:
            check(op in __import__('rp4_usecase_classes').D(n['name'])['operations'],key+': signature not from current C#')
    actual_relationships=page.findall('.//mxCell[@umlRole="classRelationship"]')
    check(len(actual_relationships)==len(m['edges']),key+': relationship count mismatch')
    actual_by_signature={(r.get('fromClass'),r.get('toClass'),r.get('relationship')):r for r in actual_relationships}
    check(len(actual_by_signature)==len(actual_relationships),key+': duplicate class relationship')
    multiplicities=page.findall('.//mxCell[@umlRole="multiplicity"]')
    for expected in m['edges']:
        signature=(expected['a'],expected['b'],expected['kind'])
        relationship=actual_by_signature.get(signature)
        check(relationship is not None,key+': missing relationship '+str(signature))
        if relationship is None:continue
        check(relationship.get('relationshipCaption')==expected['caption'],key+': incorrect relationship message '+str(signature))
        if expected['cards']:
            found={x.get('className'):x.get('value') for x in multiplicities if x.get('edgeId')==relationship.get('id')}
            wanted={expected['a']:expected['cards'][0],expected['b']:expected['cards'][1]}
            check(found==wanted,key+': incorrect multiplicity '+str(signature)+' '+str(found)+' != '+str(wanted))
        else:
            check(not [x for x in multiplicities if x.get('edgeId')==relationship.get('id')],key+': unexpected multiplicity '+str(signature))

snapshot=json.loads((OUT/'source-map.json').read_text(encoding='utf8'))
for name,digest in snapshot['files'].items():check(hashlib.sha256((BE/name).read_bytes()).hexdigest()==digest,'Source changed during build: '+name)
section_map=Path(__file__).resolve().parent/'rp4-section-files.json'
if section_map.exists():
    for entry in json.loads(section_map.read_text(encoding='utf8')):
        target=OUT.parent/entry['file']
        native=E.parse(target).getroot().findall('diagram')
        expected=[p for p in pages if p.get('id')=='rp4-'+entry['section'] or p.get('id').startswith('rp4-'+entry['section']+'.')]
        check([p.get('id') for p in native]==[p.get('id') for p in expected],'Section mismatch: '+entry['file'])
    check(not list(OUT.parent.rglob('*.md')),'Markdown files remain in RP4')
report={'counts':counts,'errors':errors}
(OUT/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(report,indent=2,ensure_ascii=False))
raise SystemExit(1 if errors else 0)
