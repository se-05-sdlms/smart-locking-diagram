"""Editable single-page feature classes, complete members and source-backed notes."""
from pathlib import Path
import json,subprocess,textwrap,copy,hashlib,html,re,xml.etree.ElementTree as ET
from rp4_class_model import ROOT
from rp4_usecase_classes import build_usecases

def prepare(node):
    n=copy.deepcopy(node)
    # Navigations are represented by association edges, not duplicated as lists of getters/setters.
    n['attributes']=[a for a in n['attributes'] if not (a.startswith('+ ') and ('ICollection<' in a or a.split(': ',1)[-1].rstrip('?') in node.get('entity_types',[])))]
    n['display_operations']=n['operations']
    width=220 if node['role'] in ('entity','DTO') else 300
    chunks=[]
    for field in ('attributes','display_operations'):
        lines=[]
        for item in n[field]:
            # Presentation matches the supplied UML template: parameterName: Type.
            if '(' in item and field=='display_operations':
                from rp4_class_model import split_params,clean
                begin=item.index('(');end=item.rfind('):')
                if end>begin:
                    params=[]
                    for param in split_params(item[begin+1:end]):
                        param=clean(param)
                        if param.startswith('CancellationToken '):continue
                        declaration,sep,default=param.partition(' = ')
                        pair=declaration.rsplit(' ',1)
                        params.append((pair[1]+': '+pair[0] if len(pair)==2 else declaration)+((' = '+default) if sep else ''))
                    item=item[:begin+1]+', '.join(params)+item[end:]
            limit=max(28,int((width-20)/5.4))
            if any(len(word)>limit for word in item.split()):
                item=re.sub(r'<(?=[A-Z])','< ',item)
            lines.extend(textwrap.wrap(item,limit,subsequent_indent='  ',break_long_words=False,break_on_hyphens=False))
        if lines:chunks.append((field,lines,max(32,16+len(lines)*13)))
    n['chunks']=chunks;n['width']=width;n['height']=40+sum(c[2] for c in chunks)
    return n

def build(api):
    Canvas,label=api['Canvas'],api['label']
    PAPER=MUTED=INK=ACCENT=None
    PAPER='#FFFFFF';MUTED=INK='#000000'
    template=ET.parse(r'D:\Zalo Received Files\JLAS_Authentication_Class_Diagram.drawio').getroot()
    sample=next(cell for cell in template.findall('.//mxCell') if cell.get('id')=='AuthServiceImpl')
    template_style=sample.get('style')
    models=build_usecases();graphs=[]
    for m in models:
        entities=[n['name'] for n in m['nodes'] if n['role']=='entity']
        for n in m['nodes']:n['entity_types']=entities
        m['nodes']=[prepare(n) for n in m['nodes']]
        graph={'id':m['key'],'layoutOptions':{
            'elk.algorithm':'layered','elk.direction':'RIGHT','elk.edgeRouting':'ORTHOGONAL',
            'elk.spacing.nodeNode':'48','elk.layered.spacing.nodeNodeBetweenLayers':'80',
            'elk.layered.spacing.edgeNodeBetweenLayers':'40','elk.spacing.edgeNode':'24','elk.spacing.edgeEdge':'16',
            'elk.layered.nodePlacement.strategy':'NETWORK_SIMPLEX','elk.layered.mergeEdges':'false',
            'elk.layered.considerModelOrder.strategy':'NODES_AND_EDGES','elk.padding':'[top=24,left=24,bottom=24,right=24]'},
            'children':[{'id':n['name'],'width':n['width'],'height':n['height']} for n in m['nodes']],
            'edges':[]}
        for i,e in enumerate(m['edges']):
            a,b=(e['b'],e['a']) if e['kind']=='realization' else (e['a'],e['b'])
            graph['edges'].append({'id':str(i),'sources':[a],'targets':[b]})
        graphs.append(graph)
    work=ROOT/'docs'/'RP4-drawio'/'layout';work.mkdir(parents=True,exist_ok=True)
    (work/'graphs.json').write_text(json.dumps(graphs),encoding='utf8')
    from rp4_class_layout import layout
    routed=[layout(m) for m in models]
    (work/'routed.json').write_text(json.dumps(routed),encoding='utf8')
    ledger=[]
    for m,g in zip(models,routed):
        c=Canvas(m['key'],m['title'],'class')
        c.model.set('background',PAPER)
        positions={n['id']:n for n in g['children']}
        width=max(1200,g['width']+64);dy=24
        # Keep equal page margins after draw.io import.  The layout already
        # contains routing gutters, so only a uniform translation is needed.
        content_left=min(n['x'] for n in positions.values())
        dx=48-content_left
        # One native HTML vertex per class, exactly like the supplied example.
        ROLE_COLORS = {
            'controller': (PAPER, INK),
            'interface': (PAPER, INK),
            'service': (PAPER, INK),
            'control': (PAPER, INK),
            'persistence': (PAPER, INK),
            'entity': (PAPER, INK),
            'request': (PAPER, INK),
            'response': (PAPER, INK),
            'DTO': (PAPER, INK),
        }
        groups={}
        occupied_annotations=[]
        for n in m['nodes']:
            pos=positions[n['name']];x=dx+pos['x'];y=dy+pos['y'];w=n['width'];h=n['height']
            role=n['role']
            if role=='DTO':role='request' if n['name'].endswith('Request') else 'response' if n['name'].endswith(('Response','Result')) else 'DTO'
            fill, stroke = ROLE_COLORS.get(role, ('#FFFFFF', '#000000'))
            node_style = template_style.replace('fillColor=#FFFFFF', f'fillColor={fill}').replace('strokeColor=#000000', f'strokeColor={stroke}').replace('align=left', 'align=center')
            display_role='database' if n['name']=='ApplicationDbContext' else role
            header=f'<div style="display:block;width:100%;text-align:center;padding:5px 0 6px;margin:0;height:29px;box-sizing:border-box"><b style="font-size:9.5px">«{display_role}»</b><br><b style="font-size:11px">{html.escape(n["name"])}</b></div>'
            sections=[]
            for field,lines,height in n['chunks']:
                body='<br>'.join(html.escape(line) for line in lines)
                sections.append(f'<div style="height:{height}px;box-sizing:border-box;padding:8px 8px 4px;margin:0;line-height:13px;font-size:9.5px;font-family:Arial,sans-serif;font-weight:bold;white-space:normal;text-align:left">{body}</div>')
            parent=c.vertex(header+'<div style="height:11px"></div>'+''.join(sections),x,y,w,h,node_style,umlRole='classBox',className=n['name'])
            groups[n['name']]=(parent,x,y,w,h)

        # ELK occasionally sends the DbContext-to-Parcel edge through the
        # LockerAccessEvent box in the confirm-pickup view.  Keep the same
        # source-backed relationship and route it through the free gutter
        # immediately above that box.
        if m['key']=='3.4.4' and 'LockerAccessEvent' in positions:
            obstacle=positions['LockerAccessEvent']
            detour_y=obstacle['y']-24
            for routed_edge in g['edges']:
                relation=m['edges'][int(routed_edge['id'])]
                if relation['a']=='ApplicationDbContext' and relation['b']=='Parcel':
                    section=routed_edge['sections'][0]
                    start=section['startPoint'];end=section['endPoint']
                    section['bendPoints']=[
                        {'x':start['x'],'y':detour_y},
                        {'x':end['x'],'y':detour_y},
                    ]
        class_rects=[(x,y,w,h) for _,x,y,w,h in groups.values()]
        connector_segments=[]
        for routed_edge in g['edges']:
            section=routed_edge['sections'][0]
            routed_points=[section['startPoint'],*section.get('bendPoints',[]),section['endPoint']]
            routed_points=[(point['x']+dx,point['y']+dy) for point in routed_points]
            connector_segments.extend(zip(routed_points,routed_points[1:]))
        def collides(rect,others):
            x,y,w,h=rect
            return any(x<ox+ow and ox<x+w and y<oy+oh and oy<y+h for ox,oy,ow,oh in others)
        def covers_connector(rect):
            x,y,w,h=rect
            for a,b in connector_segments:
                horizontal=a[1]==b[1] and y<a[1]<y+h and max(min(a[0],b[0]),x)<min(max(a[0],b[0]),x+w)
                vertical=a[0]==b[0] and x<a[0]<x+w and max(min(a[1],b[1]),y)<min(max(a[1],b[1]),y+h)
                if horizontal or vertical:return True
            return False
        def relationship_label_box(points,caption):
            width=max(54,min(120,12+len(caption)*5.2));height=18
            segments=[]
            for index,(p,q) in enumerate(zip(points,points[1:])):
                length=abs(q[0]-p[0])+abs(q[1]-p[1])
                segments.append((length,index,p,q))
            for _,__,p,q in sorted(segments,reverse=True):
                horizontal=p[1]==q[1]
                for fraction in (0.5,0.35,0.65,0.2,0.8):
                    cx=p[0]+(q[0]-p[0])*fraction;cy=p[1]+(q[1]-p[1])*fraction
                    offsets=(-22,6,-44,28,-66,50) if horizontal else (8,-width-8,1,-width-1,24,-width-24,48,-width-48)
                    for offset in offsets:
                        x=cx-width/2 if horizontal else p[0]+offset
                        y=p[1]+offset if horizontal else cy-height/2
                        rect=(x,y,width,height)
                        if x>=4 and y>=4 and not collides(rect,class_rects) and not collides(rect,occupied_annotations) and not covers_connector(rect):
                            return rect
            p,q=max(zip(points,points[1:]),key=lambda pair:abs(pair[1][0]-pair[0][0])+abs(pair[1][1]-pair[0][1]))
            return ((p[0]+q[0]-width)/2,(p[1]+q[1]-height)/2,width,height)
        # Edges strictly formatted according to 6 UML 2.5 relationship types and template ports.
        for routed_edge in g['edges']:
            i=int(routed_edge['id']);e=m['edges'][i]
            section=routed_edge['sections'][0]
            raw=[section['startPoint'],*section.get('bendPoints',[]),section['endPoint']]
            pts=[(p['x']+dx,p['y']+dy) for p in raw]
            kind=e['kind']
            caption=e.get('caption') or {
                'dependency':'«uses»','realization':'«implements»',
                'association':'relates to','composition':'contains',
                'aggregation':'aggregates','inheritance':'inherits'
            }.get(kind,'relates to')
            exitX=routed_edge.get('exitX',0.5)
            exitY=routed_edge.get('exitY',0.5)
            entryX=routed_edge.get('entryX',0.5)
            entryY=routed_edge.get('entryY',0.5)

            if kind=='realization':
                edge_style='edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;dashed=1;dashPattern=6 4;strokeWidth=1.2;strokeColor=#000000;startArrow=none;endArrow=block;endSize=12;endFill=0;fontColor=#000000;fontSize=10;fontStyle=1;labelBackgroundColor=#FFFFFF;'
            elif kind=='dependency':
                edge_style='edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;dashed=1;dashPattern=6 4;strokeWidth=1.2;strokeColor=#000000;startArrow=none;endArrow=open;endSize=8;endFill=0;fontColor=#000000;fontSize=10;fontStyle=1;labelBackgroundColor=#FFFFFF;'
            elif kind=='composition':
                edge_style='edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;dashed=0;strokeWidth=1.2;strokeColor=#000000;startArrow=diamond;startFill=1;startSize=12;endArrow=none;fontColor=#000000;fontSize=10;fontStyle=1;labelBackgroundColor=#FFFFFF;'
            elif kind=='aggregation':
                edge_style='edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;dashed=0;strokeWidth=1.2;strokeColor=#000000;startArrow=diamond;startFill=0;startSize=12;endArrow=none;fontColor=#000000;fontSize=10;fontStyle=1;labelBackgroundColor=#FFFFFF;'
            elif kind=='inheritance':
                edge_style='edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;dashed=0;strokeWidth=1.2;strokeColor=#000000;startArrow=none;endArrow=block;endSize=12;endFill=0;fontColor=#000000;fontSize=10;fontStyle=1;labelBackgroundColor=#FFFFFF;'
            else: # association
                edge_style='edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;dashed=0;strokeWidth=1.2;strokeColor=#000000;startArrow=none;endArrow=open;endSize=8;endFill=0;fontColor=#000000;fontSize=10;fontStyle=1;labelBackgroundColor=#FFFFFF;'

            edge_style+=f'jumpStyle=arc;jumpSize=8;exitX={exitX};exitY={exitY};exitPerimeter=0;entryX={entryX};entryY={entryY};entryPerimeter=0;'

            cell=c.edge(pts,value='',dashed=kind in ('dependency','realization'),end='block' if kind=='realization' else 'none' if kind in ('composition','aggregation') else 'open',
                        fill=0 if kind=='realization' else 1,umlRole='classRelationship',relationship=kind,fromClass=e['a'],toClass=e['b'],relationshipCaption=caption)
            a,ax,ay,aw,ah=groups[e['a']];b,bx,by,bw,bh=groups[e['b']]
            cell.set('source',a.get('id'));cell.set('target',b.get('id'))
            cell.set('style',edge_style)
            lx,ly,lw,lh=relationship_label_box(pts,caption)
            occupied_annotations.append((lx,ly,lw,lh))
            c.vertex(label(caption),lx,ly,lw,lh,f'text;fillColor={PAPER};strokeColor=none;fontSize=10;fontStyle=1;fontColor=#000000;align=center;verticalAlign=middle;spacing=0;',umlRole='relationshipLabel',edgeId=cell.get('id'))
            if e['cards']:
                endpoints=((pts[0],routed_edge.get('sourceSide','right'),e['a']),
                           (pts[-1],routed_edge.get('targetSide','left'),e['b']))
                for (p,side,class_name),card in zip(endpoints,e['cards']):
                    candidates=[]
                    if side in ('right','left'):
                        base_x=p[0]+8 if side=='right' else p[0]-44
                        direction=1 if side=='right' else -1
                        for ring in range(20):
                            outward=40*(ring//2)
                            candidates.append((base_x+direction*outward,p[1]-24-22*ring))
                            candidates.append((base_x+direction*outward,p[1]+6+22*ring))
                    else:
                        base_y=p[1]+6 if side=='bottom' else p[1]-24
                        direction=1 if side=='bottom' else -1
                        for ring in range(20):
                            outward=22*(ring//2)
                            candidates.append((p[0]+8+40*ring,base_y+direction*outward))
                            candidates.append((p[0]-44-40*ring,base_y+direction*outward))
                    xx,yy=candidates[-1]
                    for candidate_x,candidate_y in candidates:
                        rect=(candidate_x,candidate_y,36,18)
                        if not collides(rect,class_rects) and not collides(rect,occupied_annotations) and not covers_connector(rect):
                            xx,yy=candidate_x,candidate_y
                            break
                    occupied_annotations.append((xx,yy,36,18))
                    c.vertex(label(card),xx,yy,36,18,f'text;fillColor={PAPER};strokeColor=none;fontSize=10;fontStyle=1;fontColor=#000000;align=center;verticalAlign=middle;spacing=0;',umlRole='multiplicity',className=class_name,edgeId=cell.get('id'))
        for n in m['nodes']:
            parent,x,y,w,h=groups[n['name']]
            offset=40
            for section in range(len(n['chunks'])):
                cell=c.vertex('',0,offset,w,1,'line;strokeWidth=1.2;fillColor=none;strokeColor=#000000;rounded=0;',umlRole='classSeparator',className=n['name'])
                cell.set('parent',parent.get('id'));offset+=n['chunks'][section][2]
            c.sources.extend(n['sources'])
        c.finish()
        for n in m['nodes']:n.pop('source',None)
        ledger.append(m)
    (ROOT/'docs'/'RP4-drawio'/'complete-class-models.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding='utf8')
    return ledger
