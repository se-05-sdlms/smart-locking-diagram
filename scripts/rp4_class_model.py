"""Source-backed, complete per-feature UML models; no node/member truncation.

The old template supplies scope and explanatory captions, never signatures or truth.
Current C# declarations and EF mappings supply members, dependencies and cardinality.
"""
from pathlib import Path
import re,json
from rp4_design_spec import BE,class_specs

ROOT=Path(__file__).resolve().parents[1]
BACKUP=ROOT/'backups'/'RP4-markdown-20261020-133513'

def balanced(text,start,left='(',right=')'):
    depth=0
    for i in range(start,len(text)):
        if text[i]==left:depth+=1
        elif text[i]==right:
            depth-=1
            if not depth:return text[start+1:i],i+1
    raise ValueError('Unbalanced source declaration')

def split_params(text):
    result=[];start=0;stack=[]
    for i,ch in enumerate(text):
        if ch in '(<[':stack.append(ch)
        elif ch in ')>]':
            if stack:stack.pop()
        elif ch==',' and not stack:result.append(text[start:i].strip());start=i+1
    if text[start:].strip():result.append(text[start:].strip())
    return result

def clean(s):
    s=re.sub(r'\[[^\[\]]*\]','',s)
    return re.sub(r'\s+',' ',s).strip()

FILES={}

def current_branch_side(text):
    """Use the checked-out (HEAD) side of unresolved merge blocks for inspection."""
    output=[];state='normal'
    for line in text.splitlines(keepends=True):
        if line.startswith('<<<<<<< '):state='head';continue
        if state=='head' and line.startswith('======='):state='other';continue
        if state=='other' and line.startswith('>>>>>>> '):state='normal';continue
        if state!='other':output.append(line)
    return ''.join(output)

def strip_csharp_comments_and_literals(text):
    """Blank comments/literals while preserving newlines and declaration offsets."""
    out=[];i=0;n=len(text);state='code';verbatim=False
    while i<n:
        ch=text[i];nxt=text[i+1] if i+1<n else ''
        if state=='code':
            if ch=='/' and nxt=='/':out.extend('  ');i+=2;state='line';continue
            if ch=='/' and nxt=='*':out.extend('  ');i+=2;state='block';continue
            prefix_len=0
            if text.startswith('$@"',i) or text.startswith('@$"',i):prefix_len=3;verbatim=True
            elif text.startswith('@"',i):prefix_len=2;verbatim=True
            elif text.startswith('$"',i):prefix_len=2;verbatim=False
            elif ch=='"':prefix_len=1;verbatim=False
            if prefix_len:
                out.append('"');out.extend(' '*(prefix_len-1));i+=prefix_len;state='string';continue
            if ch=="'":out.append("'");i+=1;state='char';continue
            out.append(ch);i+=1;continue
        if state=='line':
            if ch=='\n':out.append(ch);state='code'
            else:out.append(' ')
            i+=1;continue
        if state=='block':
            if ch=='*' and nxt=='/':out.extend('  ');i+=2;state='code';continue
            out.append('\n' if ch=='\n' else ' ');i+=1;continue
        if state=='string':
            if ch=='\n':out.append('\n');i+=1;continue
            if verbatim and ch=='"' and nxt=='"':out.extend('  ');i+=2;continue
            if not verbatim and ch=='\\' and i+1<n:out.extend('  ');i+=2;continue
            if ch=='"':out.append('"');i+=1;state='code';continue
            out.append(' ');i+=1;continue
        if state=='char':
            if ch=='\\' and i+1<n:out.extend('  ');i+=2;continue
            if ch=="'":out.append("'");i+=1;state='code';continue
            out.append('\n' if ch=='\n' else ' ');i+=1
    return ''.join(out)

for f in BE.rglob('*.cs'):
    if any(p in f.parts for p in ('bin','obj','Migrations')):continue
    raw=f.read_text(encoding='utf-8-sig')
    stripped=strip_csharp_comments_and_literals(current_branch_side(raw))
    for match in re.finditer(r'\b(class|interface|record)\s+(\w+)',stripped):
        FILES.setdefault(match[2],[]).append((f,stripped,raw,match.start(),match[1]))

def describe(name):
    assert name in FILES, f'Type missing from backend: {name}'
    parts=FILES[name]
    # Primary declaration first, then any partial implementation.
    parts=sorted(parts,key=lambda p:0 if p[0].stem==name else 1)
    f,text,raw,pos,kind=parts[0]
    declaration=re.search(r'\b(?:class|interface|record)\s+'+re.escape(name)+r'\b',text[pos:])
    after=pos+declaration.end()
    # Generic positional records put their type parameter list between the
    # record name and primary constructor, for example PagedResult<T>(...).
    generic_start=re.match(r'\s*<',text[after:])
    if generic_start:
        _,after=balanced(text,after+generic_start.end()-1,'<','>')
    primary=[]
    primary_start=re.match(r'\s*\(',text[after:])
    if primary_start:
        body,after=balanced(text,after+primary_start.end()-1)
        primary=split_params(body)
    body_start=text.find('{',after)
    end=text.find(';',after)
    if kind=='record' and end>=0 and (body_start<0 or end<body_start):body=''
    elif body_start>=0:body,_=balanced(text,body_start,'{','}')
    else:body=''
    joined='\n'.join(p[1] for p in parts)
    role='interface' if kind=='interface' else 'entity' if 'Entities' in f.parts else 'DTO' if 'DTOs' in f.parts else 'controller' if name.endswith('Controller') else 'persistence' if name.endswith(('Context','Store')) else 'worker' if name.endswith(('Worker','ListenerService')) else 'service'
    attrs=[];dependencies=[];properties={};methods=[];implements=[]
    if kind=='record':
        for param in primary:
            p=clean(param);p=p.split(' = ',1)[0]
            m=re.match(r'(.+?)\s+(\w+)$',p)
            if m:attrs.append('+ '+m[2]+': '+m[1]);properties[m[2]]=m[1]
    else:
        for param in primary:
            p=clean(param);p=p.split(' = ',1)[0]
            m=re.match(r'(.+?)\s+(\w+)$',p)
            if m:
                attrs.append('- '+m[2]+': '+m[1]);dependencies.append((m[1].rstrip('?'),m[2]))
    for m in re.finditer(r'\bpublic\s+(?:virtual\s+)?([\w?<>,.\[\]]+)\s+(\w+)\s*(?:\{\s*get\s*;|=>)',body):
        properties[m[2]]=m[1]
        if m[2] not in {line.split(':')[0][2:] for line in attrs}:attrs.append('+ '+m[2]+': '+m[1])
    # Controller actions can have their attribute and declaration on the same line.
    body=re.sub(r'(?m)^(\s*)\[[^\n]*?\]\s*(?=public\b)',r'\1',body)
    # Class-level declarations only: skip method bodies by checking brace depth.
    for m in re.finditer(r'(?m)^\s*(?:(public|protected|internal)\s+)?(?:(?:static|override|async|virtual|sealed|new)\s+)*(\([^()\n]+\)|[\w?<>.,\[\]]+)\s+(\w+)\s*\(',body):
        if kind!='interface' and not m[1]:continue
        if body[:m.start()].count('{')!=body[:m.start()].count('}'):continue
        params,finish=balanced(body,m.end()-1)
        params=clean(params)
        visibility='+' if m[1] in (None,'public') else '#' if m[1]=='protected' else '~'
        signature=f'{visibility} {m[3]}({params}): {m[2]}'
        if signature not in methods:methods.append(signature)
    # Partial source may supply additional public/internal methods.
    for pf,pt,_,pp,pk in parts[1:]:
        for m in re.finditer(r'(?m)^\s*(public|internal)\s+(?:(?:static|async|override)\s+)*([\w?<>.,\[\]]+)\s+(\w+)\s*\(',pt):
            params,_=balanced(pt,m.end()-1)
            signature=f'{"+" if m[1]=="public" else "~"} {m[3]}({clean(params)}): {m[2]}'
            if signature not in methods:methods.append(signature)
    suffix=text[after:body_start if body_start>=0 else after+300]
    if ':' in suffix:
        implements=[clean(x) for x in split_params(suffix.split(':',1)[1])]
    return {'name':name,'role':role,'attributes':attrs,'operations':methods,'properties':properties,'dependencies':dependencies,
            'implements':implements,'sources':[p[0].relative_to(BE).as_posix() for p in parts], 'source':joined}

def template(path):
    t=path.read_text(encoding='utf-8-sig');names=[];edges=[]
    for m in re.finditer(r'^class\s+(\w+)\[',t,re.M):names.append(m[1])
    for line in t.splitlines():
        m=re.match(r'^(\w+)\s+(?:"([^"]+)"\s+)?(<\|\.\.|\.\.>|-->|\*--|--)\s+(?:"([^"]+)"\s+)?(\w+)(?:\s*:\s*(.*))?$',line)
        if m:
            a,ac,arrow,bc,b,caption=m.groups();kind='realization' if arrow=='<|..' else 'association' if ac or bc or arrow in ('*--','--') else 'dependency'
            if kind=='realization':a,b=b,a
            edges.append(dict(a=a,b=b,kind=kind,caption=caption or 'persists',cards=[ac,bc] if ac and bc else []))
    return names,edges

NOTES={
 '3.1.1':['Guest authentication: X-Guest-Session-Token is hashed and compared with GuestSessionTokenHash. Manual / Auto mode is snapshotted from the recipient profile.','FinalizeDropOffAsync changes Allocated to Deposited and creates the Stored Parcel. Releasing a reservation does not release the occupied compartment.'],
 '3.2.1':['ImagesController uses IImageStorageService. API dependency injection chooses Supabase storage when URL and API key are configured; otherwise it chooses local storage.','SubmitDeliveryRequest contains image URL and recipient phone. DeliveryRequest stores OCR-related fields as data; the implemented path accepts submitted recipient information.'],
 '3.3.1':['A reservation has exactly one owner: DeliveryRequestId XOR ReturnRequestId. Relational allocation uses a Serializable transaction.','Available compartments exclude unexpired reservations, Stored/Overdue parcels and Allocated/Deposited returns. Bluetooth may defer door-state verification to the device.'],
 '3.4.1':['LockerAccessService returns a Bluetooth command or dispatches MQTT. Succeeded on this call describes command preparation / dispatch, not completed physical pickup.','OfflinePinService processes ordered o1 device journals. The configured workflow codec disables legacy close-only finalization in MqttLockerListenerService.'],
 '3.5.1':['LockerOperator access is restricted to assigned lockers; Administrator can access the operational endpoints allowed by controller authorization.','Maintenance requests and locker operational status are separate operations. Business services publish operational events through IOperationsRealtimeNotifier.'],
 '3.6.1':['Public registration creates Resident accounts. Administrator provisions LockerOperator accounts through UsersController; first login may require a password change.','OtpService stores hashes, expiry and attempt/lockout state. Login, refresh, logout, reset and first-login password change remain distinct operations.'],
 '3.7.1':['OverdueChargeWorker runs immediately and every 15 minutes. Fee calculation uses billable hours up to min(now, MaxStorageUntil), preserving existing rate snapshots.','OverdueCharge and PaymentTransaction are persisted domain types. This view shows fee calculation and persisted state; no subscription-payment flow is substituted for overdue payment.'],
 '3.8.1':['UsersController, SystemPoliciesController, ReportsController and AuditLogsController require Administrator. Operator accounts are created by Administrator.','An active policy cannot be edited in place. Activation closes previous versions and sets the target effective interval; audit logs are append-only.'],
 '3.9.1':['ReturnRequestService implements both resident return and guest pickup session interfaces. Code is six numeric digits; Created/Allocated responses hide the stored ReturnCode.','Current R/G device journals are reconciled in the OfflinePinService partial implementation. Completed pickup clears the guest token and records CompartmentReleasedAt.']}

def build_models():
    models=[]
    for path in sorted(BACKUP.glob('3.*/*Class Diagram.md')):
        key=path.name.split(' ',1)[0]
        names,old_edges=template(path)
        if key=='3.7.1':
            remove={'PaymentWebhooksController','IPaymentGatewayService','IResidentSubscriptionService','PayOSPaymentGatewayService','ResidentSubscriptionService','CreatePaymentLinkRequest','CreatePaymentLinkResult','PayOSWebhookPayload','PayOSWebhookData','ResidentSubscription'}
            names=[n for n in names if n not in remove]
        # Merge every type already represented in the approved feature scope.
        extras=[]
        for s in class_specs:
            if s['key'].startswith(key+'.'):
                for n,_,_,_ in s['boxes']:
                    if n not in names and n not in extras:extras.append(n)
        names+=extras
        if key=='3.1.1':
            names+=['DeliveryRequestSummaryResponse','GuestDeliveryStatusResponse','CompartmentReservationResponse']
        if key=='3.5.1':names+=['OperatorIncidentsController','ParcelService','IParcelService','ParcelsController','ParcelReminderWorker','ParcelReminderService','IParcelReminderService']
        if key=='3.6.1':names+=['OtpService','UpdateApprovalModeRequest','ResetPasswordRequest','ChangePasswordRequest','RefreshTokenRequest']
        if key=='3.9.1':names+=['ICompartmentAllocationService','ILockerAccessService','OfflinePinService','IOfflinePinService']
        if key=='3.4.1':names+=['PickupConfirmationResponse','BluetoothPrepareRequest','BluetoothCommandResponse','OfflinePinSyncRequest','OfflinePinSyncResponse']
        if key=='3.5.1':names+=['CreateIncidentRequest','CreateGuestIncidentRequest','IncidentDetailResponse','UpdateIncidentStatusRequest','EmergencyUnlockRequest','EmergencyUnlockResponse','CreateMaintenanceRequest','MaintenanceResponse']
        if key=='3.8.1':names+=['CreateUserRequest','CreateUserResponse','AssignOperatorScopeRequest','OperatorAssignmentResponse','SaveSystemPolicyRequest','SystemPolicyResponse','AuditLogResponse','OperationsReportResponse','AdminDashboardResponse']
        names=list(dict.fromkeys(names));nodes={name:describe(name) for name in names}
        edges=[];seen=set();ledger=[]
        def add(a,b,kind,caption,cards=(),basis='source'):
            if a not in nodes or b not in nodes or (a,b,kind) in seen:return
            seen.add((a,b,kind));edges.append(dict(a=a,b=b,kind=kind,caption=caption,cards=list(cards),basis=basis))
        # Retain every explanatory caption whose connection is justified by source.
        for e in old_edges:
            a,b=e['a'],e['b'];kind=e['kind']
            if a not in nodes or b not in nodes:continue
            evidence=nodes[a]['source']
            if kind=='realization' and b not in nodes[a]['implements']:
                ledger.append(f'Removed unsupported realization {a} -> {b}');continue
            if kind=='association':
                # Derive multiplicities from actual navigation/FK mapping below.
                continue
            delegated_contract='\n'.join('\n'.join(nodes[dep]['operations']) for dep,param in nodes[a]['dependencies'] if dep in nodes and nodes[dep]['role']=='interface')
            caption=e['caption']
            if a=='MqttLockerListenerService' and b in ('IParcelService','IDeliveryRequestService','IReturnRequestService','IReturnPickupSessionService'):
                caption='legacy finalization only'
            if b in evidence or (nodes[b]['role']=='DTO' and b in delegated_contract):add(a,b,kind,caption,basis='template caption + source / delegated contract')
            else:ledger.append(f'Removed unsupported dependency {a} -> {b}')
        for name,node in nodes.items():
            for dep,param in node['dependencies']:
                add(name,dep,'dependency','delegates' if node['role']=='controller' else 'reads and writes' if dep=='ApplicationDbContext' else 'uses '+param)
            for interface in node['implements']:add(name,interface,'realization','implements')
            # Workers/listeners resolve service contracts via IServiceProvider rather than constructor injection.
            for dep in re.findall(r'GetRequiredService<([\w]+)>',node['source']):add(name,dep,'dependency','resolves '+dep)
            if node['role'] in ('controller','service','interface'):
                signatures='\n'.join(node['operations'])
                for target,t in nodes.items():
                    if t['role']=='DTO' and re.search(r'\b'+target+r'\b',signatures):
                        uses_in_return=any(re.search(r'\):.*\b'+target+r'\b',op) for op in node['operations'])
                        add(name,target,'dependency','returns' if uses_in_return else 'receives')
            if node['role']=='persistence':
                for target,t in nodes.items():
                    if t['role']=='entity' and re.search(r'DbSet<'+target+r'>',node['source']):add(name,target,'dependency','persists')
        # Source-backed entity relations: FK nullability and WithOne/WithMany set multiplicities.
        for name,node in nodes.items():
            if node['role']!='entity':continue
            cfg=BE/'smart-locking-be.Infrastructure'/'Persistence'/'Configurations'/(name+'Configuration.cs')
            cfg_text=cfg.read_text(encoding='utf-8-sig') if cfg.exists() else ''
            if cfg.exists():node['sources'].append(cfg.relative_to(BE).as_posix())
            for prop,typ in node['properties'].items():
                target=typ.rstrip('?')
                if target not in nodes or nodes[target]['role']!='entity':continue
                # Ignore collection navigations: their child FK supplies the same relation.
                if '<' in typ:continue
                chain=re.search(r'HasOne\([^;]*?\.'+re.escape(prop)+r'\s*\)(.*?);',cfg_text,re.S)
                relation=chain[1] if chain else ''
                fk_match=re.search(r'HasForeignKey(?:<[^>]+>)?\([^)]*\.([\w]+)',relation)
                fk=fk_match[1] if fk_match else prop+'Id'
                if fk not in node['properties'] and not fk_match:continue
                nullable='?' in node['properties'].get(fk,typ)
                cards=('0..1' if '.WithOne(' in relation else '0..*','0..1' if nullable else '1')
                old=next((e for e in old_edges if e['kind']=='association' and {e['a'],e['b']}=={name,target}),None)
                if old and old['a']==target:
                    add(target,name,'association',old['caption'],cards[::-1],basis='entity navigation + EF FK mapping')
                else:add(name,target,'association',old['caption'] if old else prop,cards,basis='entity navigation + EF FK mapping')
        models.append(dict(key=key,title=path.parent.name.split(' ',1)[1]+' — Class Diagram',nodes=list(nodes.values()),edges=edges,notes=NOTES[key],ledger=ledger,template_classes=template(path)[0]))
    return models

if __name__=='__main__':
    models=build_models()
    out=ROOT/'docs'/'RP4-drawio';out.mkdir(parents=True,exist_ok=True)
    for m in models:
        for n in m['nodes']:n.pop('source',None)
    (out/'complete-class-models.json').write_text(json.dumps(models,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps([{ 'key':m['key'],'classes':len(m['nodes']),'relations':len(m['edges']),'changes':m['ledger']} for m in models],indent=2))
