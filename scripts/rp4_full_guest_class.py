"""Full 3.1.1 view: retain the original template's layers, DTOs and labels."""
def build(api):
    Canvas, classbox, label = api['Canvas'], api['classbox'], api['label']
    PAPER, MUTED, INK = api['PAPER'], api['MUTED'], api['INK']
    c=Canvas('3.1.1','Shipper Guest Drop-off — Class Diagram','class')
    c.header(3040,'Controller, service contracts, dependencies, DTOs, persistence and domain entities in one complete view.')
    boxes={}
    def box(name,members,x,y,w=520):
        boxes[name]=classbox(c,name,members,x,y,w,focal=name=='DeliveryRequestService')
    box('DeliveryRequestsController',[
        '- deliveryRequestService: IDeliveryRequestService','Create','Submit','GetGuestStatus',
        'GetPendingRequests','ApproveRequest','RejectRequest','OpenCompartment'],760,240,640)
    box('IDeliveryRequestService',[
        'CreateAsync','SubmitAsync','GetAsync','GetPendingRequestsForResidentAsync',
        'ApproveDeliveryRequestAsync','RejectDeliveryRequestAsync','OpenCompartmentAsync',
        'FinalizeDropOffAsync','ExpireStartedSessionsAsync','ExpirePendingApprovalsAsync','ExpireReservationsAsync'],80,1000,680)
    box('DeliveryRequestService',[
        '- dbContext: ApplicationDbContext','- tokenHashService: ITokenHashService',
        '- pushNotificationService: IPushNotificationService','- lockerAccessService: ILockerAccessService',
        '- compartmentAllocationService: ICompartmentAllocationService','- timeProvider: TimeProvider',
        '- realtimeNotifier: IOperationsRealtimeNotifier?'],80,1880,680)
    box('InitiateDeliveryRequest',['+ LockerCode: string'],1040,1000)
    box('SubmitDeliveryRequest',['+ ParcelImageUrl: string','+ RecipientPhone: string'],1740,1000)
    box('InitiateDeliveryResponse',['+ Id: Guid','+ GuestSessionToken: string','+ Status: DeliveryRequestStatus','+ SessionExpiresAt: DateTimeOffset'],2440,1000)
    box('DeliveryRequestSummaryResponse',['+ Id: Guid','+ Status: DeliveryRequestStatus','+ ParcelImageUrl: string?','+ SessionExpiresAt: DateTimeOffset'],1040,1420)
    box('GuestDeliveryStatusResponse',['+ RequestId: Guid','+ Status: DeliveryRequestStatus','+ ApprovalExpiresAt: DateTimeOffset?',
        '+ CompartmentCode: string?','+ ReservationExpiresAt: DateTimeOffset?','+ ParcelId: Guid?',
        '+ FailureCode: DeliveryRequestFailureCode?','+ FailureDetail: string?'],1740,1420)
    box('CompartmentReservationResponse',['+ RequestId: Guid','+ ReservationId: Guid','+ CompartmentId: Guid','+ CompartmentCode: string',
        '+ ReservedAt: DateTimeOffset','+ ReservationExpiresAt: DateTimeOffset','+ Bluetooth: BluetoothCommandResponse? = null'],2440,1420)
    box('ICompartmentAllocationService',['ReserveAvailableAsync','ReleaseAsync'],80,2400,680)
    box('ILockerAccessService',['OpenAsync'],1040,2400)
    box('ApplicationDbContext',['DeliveryRequests','ResidentProfiles','CompartmentReservations','Parcels','SystemPolicies','Notifications','AuditLogs','SaveChangesAsync'],1740,2400)
    box('SystemPolicy',['Id','GuestSessionTimeoutMinutes','ManualApprovalTimeoutMinutes','CompartmentReservationMinutes','IsActive'],2440,2400)
    box('DeliveryRequest',['Id','LockerId','ResidentProfileId','SystemPolicyId','AllocatedCompartmentId','GuestSessionTokenHash',
        'ApprovalModeSnapshot','Status','SessionExpiresAt','ApprovalExpiresAt','ReservationExpiresAt','CompartmentReleasedAt'],1740,3060)
    box('ResidentProfile',['Id','UserId','RegisteredLockerId','DeliveryApprovalMode'],80,3820)
    box('Locker',['Id','Code','OperationalStatus'],820,3820)
    box('CompartmentReservation',['Id','LockerCompartmentId','DeliveryRequestId','ReturnRequestId','ExpiresAt','ReleasedAt'],1740,3820)
    box('Parcel',['Id','DeliveryRequestId','ParcelCode','Status'],2440,3820)
    box('LockerCompartment',['Id','LockerId','Code','DoorStatus','OperationalStatus'],820,4320)

    def pt(name,side,f=.5):
        x,y,w,h=boxes[name]
        return {'top':(x+w*f,y),'bottom':(x+w*f,y+h),'left':(x,y+h*f),'right':(x+w,y+h*f)}[side]
    def rel(a,b,kind,caption,points,lx,ly,card=None):
        c.edge(points,dashed=kind in ('dependency','realization'),end='block' if kind=='realization' else 'none' if kind=='association' else 'open',
               fill=0 if kind=='realization' else 1,umlRole='classRelationship',relationship=kind,fromClass=a,toClass=b)
        c.vertex(label(caption),lx,ly,220,36,f'text;fillColor={PAPER};strokeColor=none;fontSize=14;align=center;',umlRole='relationshipLabel')
        if card:
            for p,adj,text in zip((points[0],points[-1]),(points[1],points[-2]),card):
                dx,dy=adj[0]-p[0],adj[1]-p[1]
                xx=p[0]+16 if dx>=0 else p[0]-64
                yy=p[1]-36 if dx else p[1]+12 if dy>0 else p[1]-36
                c.text(text,xx,yy,48,24,13)
    # Dependencies: every relationship has its original explanatory caption.
    a=pt('DeliveryRequestsController','bottom',.12);b=pt('IDeliveryRequestService','top')
    rel('DeliveryRequestsController','IDeliveryRequestService','dependency','delegates',[a,(a[0],880),(b[0],880),b],540,832)
    a=pt('DeliveryRequestService','top');b=pt('IDeliveryRequestService','bottom')
    rel('DeliveryRequestService','IDeliveryRequestService','realization','implements',[a,b],440,(a[1]+b[1])/2-18)
    for i,(name,caption) in enumerate([('InitiateDeliveryRequest','receives'),('SubmitDeliveryRequest','receives'),('InitiateDeliveryResponse','returns'),
                                        ('DeliveryRequestSummaryResponse','returns'),('GuestDeliveryStatusResponse','returns'),('CompartmentReservationResponse','returns')]):
        a=pt('DeliveryRequestsController','right',.12+i*.13);b=pt(name,'top',.3 if i<3 else .7)
        if i<3:
            rail=740+i*72;points=[a,(b[0],a[1]),(b[0],rail),b]
            # Route from the controller into a separate horizontal band above DTOs.
            points=[a,(1480+i*32,a[1]),(1480+i*32,rail),(b[0],rail),b]
            lx=b[0]-110;ly=rail-48
        else:
            railx=1600+(i-3)*700
            points=[a,(railx,a[1]),(railx,1320),(b[0],1320),b];lx=railx-220;ly=1268
        rel('DeliveryRequestsController',name,'dependency',caption,points,lx,ly)
    a=pt('DeliveryRequestService','bottom',.25);b=pt('ICompartmentAllocationService','top')
    rel('DeliveryRequestService','ICompartmentAllocationService','dependency','allocates',[a,(a[0],2300),(b[0],2300),b],160,2252)
    a=pt('DeliveryRequestService','bottom',.60);b=pt('ILockerAccessService','top')
    rel('DeliveryRequestService','ILockerAccessService','dependency','opens',[a,(a[0],2220),(b[0],2220),b],850,2172)
    a=pt('DeliveryRequestService','right',.6);b=pt('ApplicationDbContext','top')
    rel('DeliveryRequestService','ApplicationDbContext','dependency','reads and writes',[a,(a[0]+100,a[1]),(a[0]+100,2120),(b[0],2120),b],1610,2072)
    a=pt('ApplicationDbContext','bottom');b=pt('DeliveryRequest','top')
    rel('ApplicationDbContext','DeliveryRequest','dependency','persists',[a,b],2010,(a[1]+b[1])/2-18)
    a=pt('SystemPolicy','bottom');b=pt('DeliveryRequest','right',.2)
    rel('SystemPolicy','DeliveryRequest','association','governs',[a,(a[0],b[1]),b],2600,b[1]-72,('1','0..*'))
    for name,caption,cards,f,rail in [
        ('ResidentProfile','receives',('0..*','0..1'),.15,3650),('Locker','hosts',('0..*','1'),.35,3710),
        ('CompartmentReservation','reserves',('0..1','0..*'),.65,3650),('Parcel','creates',('1','0..1'),.85,3710)]:
        a=pt('DeliveryRequest','bottom',f);b=pt(name,'top')
        rel('DeliveryRequest',name,'association',caption,[a,(a[0],rail),(b[0],rail),b],b[0]-110,rail-52,cards)
    a=pt('Locker','bottom');b=pt('LockerCompartment','top')
    rel('Locker','LockerCompartment','association','contains',[a,b],1120,(a[1]+b[1])/2-18,('1','0..*'))
    # UML comments restore explanatory notes as native, editable folded-corner shapes.
    for text,x,y,w in [
        ('Guest session: X-Guest-Session-Token is validated against GuestSessionTokenHash.\nRecipient approval mode is snapshotted when parcel information is submitted.',80,3060,1160),
        ('Lifecycle: Started → PendingApproval / Approved → Allocated → Deposited.\nFinalizeDropOffAsync creates the Stored Parcel and releases the reservation, while the parcel still occupies its compartment.',80,3380,1160),
        ('Relationship definitions:\nDependency = dashed line + open arrow.\nRealization = dashed line + hollow triangle.\nAssociation = solid line without arrow + multiplicity.\nLocker / compartment uses association; a foreign key alone does not imply composition.',1740,4320,1220)]:
        c.vertex(label(text),x,y,w,180,f'shape=note;size=20;fillColor=#ececec;strokeColor={MUTED};align=left;spacing=20;fontSize=16;',umlRole='comment')
    c.footer(c.h+64,3040,'All original template classes are retained on one page. Controller return types follow C#; response DTOs are connected with explicit returns dependencies.\nPrivate members show constructor dependencies; CancellationToken is omitted from signatures for readability.')
    c.finish()
