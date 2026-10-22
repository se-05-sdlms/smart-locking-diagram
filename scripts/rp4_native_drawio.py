"""Build editable RP4 UML directly as mxGraph XML. No Mermaid conversion."""
from pathlib import Path
import xml.etree.ElementTree as E
import html, json, re, textwrap, hashlib, subprocess
from rp4_design_spec import sequences, class_specs, blank_sections

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'RP4' / 'drawio'
BE = Path(r'D:\code_capstone\smart-locking-be')
PAPER, INK, MUTED, ACCENT, LINK = '#FFFFFF', '#000000', '#000000', '#000000', '#000000'
ALL = []

def label(s):
    return html.escape(s).replace('\n', '<br>')

class Canvas:
    def __init__(self, key, title, kind, sources=()):
        self.key, self.title, self.kind, self.sources = key, title, kind, list(sources)
        self.model = E.Element('mxGraphModel', grid='1', gridSize='8', guides='1', tooltips='1', connect='1', arrows='1', fold='1', page='0', pageScale='1', background=PAPER, math='0', shadow='0')
        self.root = E.SubElement(self.model, 'root')
        E.SubElement(self.root, 'mxCell', id='0')
        E.SubElement(self.root, 'mxCell', id='1', parent='0')
        self.n = 1
        self.w = self.h = 0
        self.messages = []
    def vertex(self, value, x,y,w,h, style='', **metadata):
        self.n += 1
        cell = E.SubElement(self.root, 'mxCell', id=f'c{self.n}', value=value, vertex='1', parent='1', style=f'html=1;whiteSpace=wrap;fontFamily=Arial;fontSize=14;fontColor={INK};shadow=0;'+style, **metadata)
        E.SubElement(cell,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h), **{'as':'geometry'})
        self.w=max(self.w,x+w);self.h=max(self.h,y+h)
        return cell
    def text(self, value,x,y,w,h,size=14,align='left', **meta):
        return self.vertex(label(value),x,y,w,h,f'text;strokeColor=none;fillColor=none;align={align};verticalAlign=middle;fontSize={size};spacing=0;'+('fontFamily=Georgia;' if size==28 else ''),**meta)
    def edge(self, points, value='', dashed=False, end='block', color=MUTED, start='none', fill=1, **meta):
        self.n+=1
        cell=E.SubElement(self.root,'mxCell',id=f'c{self.n}',value=label(value),edge='1',parent='1',style=f'edgeStyle=none;rounded=0;curved=0;html=1;strokeWidth=1.4;strokeColor={color};startArrow={start};endArrow={end};endFill={fill};startFill=1;endSize=10;dashed={int(dashed)};dashPattern=6 4;fontFamily=Arial;fontSize=13;fontColor={INK};labelBackgroundColor={PAPER};',**meta)
        g=E.SubElement(cell,'mxGeometry',relative='1', **{'as':'geometry'})
        E.SubElement(g,'mxPoint',x=str(points[0][0]),y=str(points[0][1]), **{'as':'sourcePoint'})
        E.SubElement(g,'mxPoint',x=str(points[-1][0]),y=str(points[-1][1]), **{'as':'targetPoint'})
        if len(points)>2:
            a=E.SubElement(g,'Array', **{'as':'points'})
            for x,y in points[1:-1]:E.SubElement(a,'mxPoint',x=str(x),y=str(y))
        for x,y in points:self.w=max(self.w,x+24);self.h=max(self.h,y+24)
        return cell
    def header(self, width, subtitle):
        # The file and draw.io page names carry the section/title. Keep the
        # canvas itself limited to the UML content requested for the report.
        return None
    def footer(self, y, width, lines):
        # Relationship/message notation is expressed by the diagram itself;
        # no repeated legend is needed inside every page.
        return None
    def finish(self):
        if self.kind=='blank' and self.n==1:
            # Preserve the standard sequence-page footprint while keeping
            # sections without backend implementation genuinely empty.
            self.w, self.h = 1688, 1276
        self.model.set('pageWidth',str(int(self.w+48)))
        self.model.set('pageHeight',str(int(self.h+32)))
        ALL.append(self)

def sequence(s):
    p=s['participants'];n=len(p)
    base_width=max(1520, 160+(n-1)*320+280)
    last=p[-1][0]
    right_gutter=400 if any(len(step)==4 and step[0]==last and step[1]==last for step in s['steps']) else 0
    width=base_width+right_gutter
    xs={item[0]:160+i*(base_width-320)/(n-1) for i,item in enumerate(p)}
    c=Canvas(s['key'],s['title'],'sequence',s['sources'])
    c.header(width,s['pre'])
    y=148; events=[]; frames=[]; stack=[]
    for item in s['steps']:
        if item[0]=='frame':
            stack.append([item[1],item[2],y,len(stack)]);y+=72
        elif item[0]=='else':
            events.append(('divider',y,item[1]));y+=64
        elif item[0]=='end':
            name,guard,top,depth=stack.pop();frames.append((name,guard,top,y,depth));y+=24
        elif item[0]=='ref':events.append(('ref',y,item[1]));y+=72
        else:
            a,b,msg,kind=item;selfcall=a==b
            span=width-160-xs[a] if selfcall else abs(xs[b]-xs[a])-40
            # Separate label shapes avoid draw.io's edge-label reflow after import.
            wrap=max(22,int(span/7.4))
            wrapped='\n'.join(textwrap.wrap(msg,wrap,break_long_words=False,break_on_hyphens=False))
            lh=max(24,20*len(wrapped.splitlines()))
            y+=lh+12
            events.append(('message',y,a,b,wrapped,kind,selfcall,lh))
            y+=72 if selfcall else 36
    assert not stack,s['key']
    endy=y+32
    # Background fragments precede lifelines and messages in z-order.
    for name,guard,top,bottom,depth in sorted(frames,key=lambda f:f[4]):
        inset=depth*24
        c.vertex('',96+inset,top,width-192-inset*2,bottom-top,f'fillColor={PAPER};fillOpacity=100;strokeColor={INK};rounded=0;connectable=0;',umlRole='combinedFragment')
        c.vertex(label(name),96+inset,top,64,28,f'fillColor={PAPER};strokeColor={MUTED};fontSize=12;align=center;connectable=0;',umlRole='fragmentOperator')
        c.text('['+guard+']',176+inset,top+8,width-320-inset*2,40,13)
    SEQ_ROLE_COLORS = {
        'boundary': (PAPER, INK),
        'controller': (PAPER, INK),
        'service': (PAPER, INK),
        'persistence': (PAPER, INK),
        'database': (PAPER, INK),
        'device': (PAPER, INK),
        'external': (PAPER, INK),
        'hub': (PAPER, INK),
        'interface': (PAPER, INK),
        'worker': (PAPER, INK),
    }

    bottom_top = endy + 48

    def participant_head(pid, name, role, y, position):
        """Draw one repeated sequence participant head.

        Keeping the top and bottom heads as real mxGraph shapes makes them
        independently editable after the file is opened in diagrams.net.
        """
        x = xs[pid]
        common = {
            'umlRole': 'participantHead',
            'participant': pid,
            'participantRole': role,
            'position': position,
        }
        if role == 'actor':
            c.vertex('', x-20, y, 40, 48,
                     f'shape=umlActor;fillColor={PAPER};strokeColor={INK};',
                     **common)
            c.text(name, x-128, y+48, 256, 36, 14, 'center',
                   umlRole='participantLabel', participant=pid,
                   participantRole=role, position=position)
        else:
            fill, stroke = SEQ_ROLE_COLORS.get(role, (PAPER, MUTED))
            c.vertex(label('«'+role+'»\n'+name), x-128, y, 256, 72,
                     f'rounded=0;fillColor={fill};strokeColor={stroke};strokeWidth=1.4;align=center;',
                     **common)

    for pid,name,role in p:
        x=xs[pid]
        participant_head(pid, name, role, 24 if role == 'actor' else 28, 'top')
        lifeline_top = 112 if role == 'actor' else 100
        c.edge([(x, lifeline_top),(x,bottom_top)],dashed=True,end='none',color=INK,
               umlRole='lifeline',participant=pid,
               topParticipantY=str(lifeline_top),bottomParticipantY=str(bottom_top))
    # Bounded execution bars: each receiver runs until its matching response.
    msgs=[e for e in events if e[0]=='message']
    active=[]
    for i,e in enumerate(msgs):
        _,ey,a,b,txt,kind,selfcall,lh=e
        role=next(q[2] for q in p if q[0]==b)
        if kind=='return' or role in ('actor','device','broker','external'):continue
        last=ey+24
        if kind in ('call','http') and not selfcall:
            for r in msgs[i+1:]:
                if r[2]==b and r[3]==a and r[5]=='return':last=r[1];break
        if selfcall:
            c.vertex('',xs[b]+4,ey+24,8,24,f'fillColor={PAPER};strokeColor={INK};',umlRole='nestedActivation')
            continue
        if any(q[0]==b and q[1]<=ey and q[2]>=last for q in active):continue
        active.append((b,ey,last))
        c.vertex('',xs[b]-4,ey,8,max(24,last-ey),f'fillColor={PAPER};strokeColor={INK};',umlRole='activation')
    no=0
    for e in events:
        if e[0]=='divider':
            c.edge([(96,e[1]),(width-96,e[1])],dashed=True,end='none',color=INK)
            c.text('['+e[2]+']',176,e[1]+8,width-320,32,13)
        elif e[0]=='ref':
            c.vertex(label('ref   '+e[2]),112,e[1],width-224,48,f'fillColor={PAPER};strokeColor={MUTED};fontSize=13;align=left;spacingLeft=16;',umlRole='reference')
        else:
            _,ey,a,b,txt,kind,selfcall,lh=e;no+=1
            number='1.' if no==1 else f'1.{no-1}'
            content=number+'  '+txt
            pts=[(xs[a]+4,ey),(xs[b]-4 if xs[b]>xs[a] else xs[b]+4,ey)]
            if selfcall:pts=[(xs[a]+4,ey),(xs[a]+64,ey),(xs[a]+64,ey+40),(xs[a]+12,ey+40)]
            # UML async messages use a solid line with an open arrowhead.
            # Only reply/return messages are dashed.
            c.edge(pts,dashed=kind=='return',end='open' if kind=='async' else 'block',color=LINK if kind=='http' else MUTED,umlRole='selfMessage' if selfcall else 'message',messageNumber=number,sourceParticipant=a,targetParticipant=b,messageText=content,messageKind=kind)
            if selfcall:lx=xs[a]+80;lw=width-lx-80;ly=ey-lh-12
            else:lx=min(xs[a],xs[b])+20;lw=abs(xs[a]-xs[b])-40;ly=ey-lh-12
            c.vertex(label(content),lx,ly,lw,lh,f'text;fillColor={PAPER};strokeColor=none;align={"left" if selfcall else "center"};verticalAlign=bottom;spacing=0;fontSize=14;',umlRole='messageLabel',messageNumber=number)
            c.messages.append({'number':number,'from':a,'to':b,'kind':kind,'label':txt.replace('\n',' ')})
    for pid,name,role in p:
        participant_head(pid, name, role, bottom_top, 'bottom')
    c.footer(bottom_top+112,width,'Call: solid + filled arrow   •   Return: dashed + filled arrow   •   Async: dashed + open arrow\n'+s.get('note','Time flows downward; UI lifelines represent the client boundary of the use case.'))
    c.finish()

def source_index():
    idx={}
    for f in BE.rglob('*.cs'):
        if any(x in f.parts for x in ('obj','bin','Migrations')):continue
        text=f.read_text(encoding='utf-8-sig')
        for m in re.finditer(r'\b(?:class|interface|record)\s+(\w+)',text):idx.setdefault(m[1],[]).append((f,text))
    return idx

IDX=source_index()

def classbox(c,name,members,x,y,w=400,focal=False):
    assert name in IDX, f'Unknown source class {name}'
    f,source=IDX[name][0]
    role='interface' if re.search(r'\binterface\s+'+name+r'\b',source) else 'entity' if 'Entities' in f.parts else 'DTO' if 'DTOs' in f.parts else 'controller' if name.endswith('Controller') else 'persistence' if name.endswith(('Context','Store')) else 'service'
    attrs=[];ops=[]
    for selection in members:
        mem, _, overload = selection.partition('#')
        if mem.startswith('+ ') or mem.startswith('- '):
            (ops if '(' in mem else attrs).append(mem)
        else:
            assert re.search(r'\b'+re.escape(mem)+r'\b',source),f'{name}.{mem} not in source'
            # Keep actual types when selecting properties or methods.
            prop=re.search(r'public\s+(?:virtual\s+)?([\w?<>,.\[\] ]+)\s+'+re.escape(mem)+r'\s*(?:\{|=>)',source)
            if prop:attrs.append('+ '+mem+': '+prop[1].strip())
            else:
                return_type=r'(\([\w?,.<>\s]+\)|[\w?<>.,\[\]]+)\s+'
                pattern=(r'(?:public\s+)?(?:static\s+)?(?:async\s+)?' if role=='interface' else r'public\s+(?:override\s+)?(?:static\s+)?(?:async\s+)?')+return_type+re.escape(mem)+r'\s*\((.*?)\)'
                candidates=list(re.finditer(pattern,source,re.S))
                method=candidates[int(overload or '1')-1] if candidates else None
                if method:
                    params=re.sub(r'\s+',' ',method[2]).strip()
                    params=re.sub(r'CancellationToken\s+\w+(?:\s*=\s*default)?','',params).strip(' ,')
                    params=re.sub(r',\s*,',',',params)
                    ops.append('+ '+mem+'('+params+'): '+method[1])
                else:attrs.append('+ '+mem)
    chunks=[('«'+role+'»\n'+name,56,True)]
    for lines in [attrs,ops]:
        if lines:
            wrapped=[]
            for line in lines:wrapped.extend(textwrap.wrap(line,50,subsequent_indent='  ',break_long_words=False,break_on_hyphens=False))
            chunks.append(('\n'.join(wrapped),max(48,len(wrapped)*20+24),False))
    total=sum(t[1] for t in chunks)
    offset=0
    for txt,h,header in chunks:
        c.vertex(label(txt),x,y+offset,w,h,f'fillColor={PAPER};strokeColor={INK};align={"center" if header else "left"};spacing=12;fontSize={15 if header else 13};fontStyle={1 if header else 0};',umlRole='classCompartment',className=name)
        offset+=h
    c.sources.append(str(f.relative_to(BE)).replace('\\','/'))
    if role=='entity':
        config=BE/'smart-locking-be.Infrastructure'/'Persistence'/'Configurations'/(name+'Configuration.cs')
        if config.exists():c.sources.append(config.relative_to(BE).as_posix())
    return x,y,w,total

def classes(spec):
    c=Canvas(spec['key'],spec['title'],'class')
    boxes=spec['boxes'];rels=spec['relations']
    assert len(boxes)<=7
    width=1720
    c.header(width,'Selected source members; signatures retain Task wrappers. Each relationship uses the UML type shown below.')
    coords={}
    # User-authored layout: three columns, staggered rows with reserved routing gutters.
    for name,members,col,row in boxes:
        coords[name]=classbox(c,name,members,80+col*560,240+row*500,focal=(name==spec.get('focal')))
    for i,r in enumerate(rels):
        a,b,kind,caption,*multiplicity=r
        ax,ay,aw,ah=coords[a];bx,by,bw,bh=coords[b]
        if abs(ax-bx)<1:
            pts=[(ax+aw/2,ay+ah),(bx+bw/2,by)] if by>ay else [(ax+aw/2,ay),(bx+bw/2,by+bh)]
        elif abs(ay-by)<1:
            left=ax<bx;mid=ay+min(ah,bh)/2
            pts=[(ax+aw if left else ax,mid),(bx if left else bx+bw,mid)]
        else:
            # Use the empty column gutter, outside every class rectangle.
            left=ax<bx; sx=ax+aw if left else ax;tx=bx if left else bx+bw
            gutter=(sx+tx)/2
            pts=[(sx,ay+ah/2),(gutter,ay+ah/2),(gutter,by+bh/2),(tx,by+bh/2)]
        dashed=kind in ('dependency','realization')
        end='block' if kind in ('realization','generalization') else 'none' if kind in ('association','composition','aggregation') else 'open'
        edge=c.edge(pts,'',dashed=dashed,end=end,start='diamond' if kind in ('composition','aggregation') else 'none',fill=0 if kind in ('realization','generalization') else 1,umlRole='classRelationship',relationship=kind,fromClass=a,toClass=b)
        if caption:
            if len(pts)==2 and pts[0][1]==pts[1][1]:
                lx=(pts[0][0]+pts[1][0])/2-72;ly=pts[0][1]-80;lw=144;lh=40
            elif len(pts)==2:
                lx=pts[0][0]+20;ly=(pts[0][1]+pts[1][1])/2-20;lw=200;lh=40
            else:
                lx=pts[1][0]+16;ly=(pts[1][1]+pts[2][1])/2-20;lw=144;lh=40
            c.vertex(label(caption),lx,ly,lw,lh,f'text;strokeColor=none;fillColor={PAPER};fontSize=12;align=center;',umlRole='relationshipLabel')
        if kind=='aggregation':edge.set('style',edge.get('style').replace('startFill=1','startFill=0'))
        if multiplicity:
            for pt,neighbor,card in zip((pts[0],pts[-1]),(pts[1],pts[-2]),multiplicity):
                dx,dy=neighbor[0]-pt[0],neighbor[1]-pt[1]
                if dx:lx=pt[0]+12 if dx>0 else pt[0]-64;ly=pt[1]-32
                else:lx=pt[0]+16;ly=pt[1]+12 if dy>0 else pt[1]-36
                c.text(card,lx,ly,52,24,12)
    bottom=c.h+64
    c.footer(bottom,width,'Dependency: dashed / open arrow   •   Realization: dashed / hollow triangle   •   Generalization: solid / hollow triangle\nAssociation: solid / no arrow + multiplicity   •   Composition: filled diamond at owner   •   Aggregation: hollow diamond at owner')
    c.finish()

def write_file(path,canvases):
    root=E.Element('mxfile',host='app.diagrams.net',type='device',version='24.7.17',compressed='false')
    for c in canvases:
        d=E.SubElement(root,'diagram',id='rp4-'+c.key,name=c.key+' '+c.title)
        d.append(c.model)
    E.indent(root)
    path.parent.mkdir(parents=True,exist_ok=True)
    E.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)

def main():
    for s in sequences:sequence(s)
    from rp4_complete_classes import build
    build(globals())
    for key,title in blank_sections:Canvas(key,title,'blank').finish()
    ALL.sort(key=lambda c:tuple(int(x) if x.isdigit() else x for x in re.findall(r'\d+|[a-z]+',c.key)))
    OUT.mkdir(parents=True,exist_ok=True)
    pages_dir=OUT/'pages'
    pages_dir.mkdir(parents=True,exist_ok=True)
    for stale in pages_dir.glob('*.drawio'):
        stale.unlink()
    for stale in (ROOT/'RP4').glob('3.*.drawio'):
        stale.unlink()
    write_file(OUT/'RP4-Detail-Design.drawio',ALL)
    write_file(ROOT/'RP4'/'RP4-Detail-Design.drawio',ALL)
    for chapter in range(1,10):write_file(OUT/f'RP4-3.{chapter}.drawio',[c for c in ALL if c.key.startswith(f'3.{chapter}.')])
    for c in ALL:write_file(OUT/'pages'/(c.key+'.drawio'),[c])
    chapter_folders={
        1:'3.1 Shipper Guest Drop-off',
        2:'3.2 AI-Powered Waybill Processing (OCR)',
        3:'3.3 Dynamic Locker Allocation',
        4:'3.4 Multi-method Package Retrieval',
        5:'3.5 Locker Operations, Monitoring & Incident Handling',
        6:'3.6 Resident Account, Preferences & Parcel Management',
        7:'3.7 Overdue Storage Fee Management',
        8:'3.8 Administrator System Management',
        9:'3.9 Parcel Return Management',
    }
    for folder in chapter_folders.values():
        target=ROOT/'RP4'/folder
        target.mkdir(parents=True,exist_ok=True)
        for stale in target.glob('*.drawio'):
            stale.unlink()
    section_entries=[]
    for c in ALL:
        chapter=int(c.key.split('.')[1])
        title=c.title
        if c.kind=='sequence':title+=' - Sequence Diagram'
        elif c.kind=='blank':title+=' - Sequence Diagram (Blank)'
        safe_title=re.sub(r'[<>:"/\\|?*]','-',title).replace('  ',' ').strip()
        relative=f'{chapter_folders[chapter]}/{c.key} {safe_title}.drawio'
        write_file(ROOT/'RP4'/relative,[c])
        section_entries.append({'section':c.key,'file':relative,'pages':1,'kind':c.kind})
    section_map=ROOT/'scripts'/'rp4-section-files.json'
    section_map.write_text(json.dumps(section_entries,indent=2,ensure_ascii=False),encoding='utf8')
    sources=sorted(set(s for c in ALL for s in c.sources))
    snapshot={'backend':str(BE),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=BE,text=True).strip(),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=BE,text=True).strip(),'files':{s:hashlib.sha256((BE/s).read_bytes()).hexdigest() for s in sources},'pages':[{'key':c.key,'title':c.title,'kind':c.kind,'file':'pages/'+c.key+'.drawio','sources':sorted(set(c.sources)),'messages':c.messages} for c in ALL]}
    (OUT/'source-map.json').write_text(json.dumps(snapshot,indent=2,ensure_ascii=False),encoding='utf8')
    print(json.dumps({'pages':len(ALL),'sequences':len(sequences),'classes':sum(c.kind=='class' for c in ALL),'blank':len(blank_sections),'source_files':len(sources)},indent=2))

if __name__=='__main__':main()
