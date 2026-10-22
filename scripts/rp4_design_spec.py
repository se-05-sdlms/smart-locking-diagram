"""Source-reviewed RP4 views for feature/bluetooth-offline-unlock.

Client names describe use-case boundaries, not unverified frontend classes.
The backend commit and per-file hashes are captured at build time.
"""
from pathlib import Path
import re
BE=Path(r'D:\code_capstone\smart-locking-be')
sequences=[]
class_specs=[]
blank_sections=[('3.2.2','Extract, Review & Correct Recipient Phone')]

def src(*names):
    result=[]
    for name in names:
        matches=[BE/name] if '/' in name else [p for p in BE.rglob(name+'.cs') if not any(x in p.parts for x in ('bin','obj','Migrations'))]
        assert len(matches)==1,(name,matches)
        result.append(matches[0].relative_to(BE).as_posix())
    return result

def P(id,name,role='service'):
    # UI surfaces are UML boundary objects.  Keep accepting the older
    # authoring token so existing specifications remain concise, but emit the
    # correct stereotype into every generated sequence diagram.
    if role=='client':role='boundary'
    if name=='ApplicationDbContext':role='database'
    return (id,name,role)
def M(a,b,label,kind='call'):return (a,b,label,kind)
def R(a,b,label):return M(a,b,label,'return')
def A(a,b,label):return M(a,b,label,'async')
def F(op,guard):return ('frame',op,guard)
def Else(guard):return ('else',guard)
END=('end',)
def Ref(label):return ('ref',label)

def S(key,title,participants,steps,sources,pre='',note=''):
    sequences.append(dict(key=key,title=title,participants=participants,steps=steps,sources=src(*sources),pre=pre,note=note))

def user_flow(key,title,actor,client,controller,service,endpoint,method,query,change,result='200 OK',pre='',sources=(),extra=(),note=''):
    """Five-lifeline boundary view. Domain checks are explicit self calls."""
    steps=[M('U','UI',title),M('UI','C',endpoint,'http'),M('C','S',method),M('S','DB',query),R('DB','S','Requested records'),M('S','S',change)]
    steps+=list(extra)
    steps += [R('S','C','Response DTO'),R('C','UI',result),R('UI','U','Display result')]
    S(key,title,[P('U',actor,'actor'),P('UI',client,'client'),P('C',controller,'controller'),P('S',service),P('DB','ApplicationDbContext','persistence')],steps,[controller,service,*sources],pre,note)

# 3.1 Guest delivery: separate submission, decisions, polling, dispatch and completion.
user_flow('3.1.2.a','Start Guest Drop-off Session','Shipper','Guest Web','DeliveryRequestsController','DeliveryRequestService',
          'POST /api/delivery-requests { lockerCode }','CreateAsync(request)','Load Locker by code and effective active SystemPolicy',
          'Require operational locker; create raw guest token and SHA-256 hash',result='201 Created: id, token, status, sessionExpiresAt',
          sources=('Sha256TokenHashService',),extra=[M('S','DB','Save Started DeliveryRequest + AuditLog'),R('DB','S','Saved')],
          pre='Shipper enters a locker code; no user account is required.')
user_flow('3.1.2.c','Resolve Public Locker Code','Shipper','Guest Web','LockersController','LockerService',
          'GET /api/lockers/public/by-code/{code}','GetPublicLockerAsync(code)',
          'Read active locker by normalized code','Return code, address and operational availability',
          result='200 OK: PublicLockerResponse',pre='Guest Web resolves the scanned or entered locker code before creating a session.')
S('3.1.2.b','Reject an Unavailable Guest Session',
  [P('UI','Guest Web','client'),P('C','DeliveryRequestsController','controller'),P('S','DeliveryRequestService'),P('DB','ApplicationDbContext','persistence')],
  [M('UI','C','POST /api/delivery-requests','http'),M('C','S','CreateAsync(request)'),M('S','DB','Read locker and effective policy'),R('DB','S','Locker / policy lookup'),F('alt','Locker not found'),R('S','C','NotFoundException'),R('C','UI','404 Not Found via GlobalExceptionHandler'),Else('Locker unavailable OR no effective policy'),R('S','C','ConflictException'),R('C','UI','409 Conflict via GlobalExceptionHandler'),END],
  ['DeliveryRequestsController','DeliveryRequestService','GlobalExceptionHandler'],'Alternative response to 3.1.2.a; no session is created.')
user_flow('3.1.3','Identify Recipient & Submit Parcel Information','Shipper','Guest Web','DeliveryRequestsController','DeliveryRequestService',
          'POST /api/delivery-requests/{id}:submit; X-Guest-Session-Token','SubmitAsync(id, token, request)',
          'Load session + policy; find active Resident by recipient phone','Validate token, Started state, session expiry and image URL; snapshot approval mode',
          result='200 OK: Approved or PendingApproval',pre='Image URL comes from 3.2.3; guest session exists.',
          extra=[M('S','S','Apply Auto or Manual approval mode and persist resulting status')])
S('3.1.4.a','Apply Delivery Approval Mode',
  [P('U','Shipper','actor'),P('UI','Guest Web','client'),P('C','DeliveryRequestsController','controller'),P('S','DeliveryRequestService'),P('PUSH','ExpoPushNotificationService'),P('DB','ApplicationDbContext','persistence')],
  [M('U','UI','Submit parcel information for approval'),M('UI','C','POST /api/delivery-requests/{id}:submit; X-Guest-Session-Token','http'),M('C','S','SubmitAsync(id, token, request)'),F('alt','ApprovalModeSnapshot = Auto'),M('S','S','Set Approved, DecisionAt and activity timestamps'),Else('ApprovalModeSnapshot = Manual'),M('S','S','Set PendingApproval and ApprovalExpiresAt'),M('S','PUSH','EnqueueDeliveryApprovalRequest(userId, requestId, lockerCode)'),M('PUSH','DB','Track InApp Sent + Push Pending notifications'),R('PUSH','S','Push notification id'),END,M('S','DB','SaveChangesAsync: DeliveryRequest, notifications and AuditLog'),R('DB','S','Saved'),F('opt','Manual approval notification exists'),M('S','PUSH','TrySendAsync(notificationId)'),R('PUSH','S','Push attempt completed'),END,R('S','C','DeliveryRequestSummaryResponse'),R('C','UI','200 OK: Approved or PendingApproval'),R('UI','U','Display submission status')],
  ['DeliveryRequestService','ExpoPushNotificationService'],'Internal continuation of SubmitAsync in 3.1.3.','Notification delivery details are shown in 3.5.7.b.')
for suffix,action,method in [('b','Approve','ApproveDeliveryRequestAsync'),('c','Reject','RejectDeliveryRequestAsync')]:
    user_flow('3.1.4.'+suffix,action+' Pending Delivery','Resident','Resident Mobile App','DeliveryRequestsController','DeliveryRequestService',
              'POST /api/delivery-requests/{id}:'+action.lower()+'; Bearer Resident JWT',method+'(userId, id)',
              'Load active resident and delivery request + policy','Require ownership, PendingApproval and unexpired approval; set '+('Approved' if action=='Approve' else 'Rejected'),
              extra=[M('S','DB','Save decision timestamps + AuditLog'),R('DB','S','Saved')],pre='Resident is the recipient of the pending delivery request.')
user_flow('3.1.4.d','Poll Guest Delivery Status','Shipper','Guest Web','DeliveryRequestsController','DeliveryRequestService',
          'GET /api/delivery-requests/{id}; X-Guest-Session-Token','GetAsync(id, token)','Load request, compartment code and parcel id',
          'Validate session hash; expire timed-out PendingApproval requests',result='200 OK: GuestDeliveryStatusResponse',pre='Guest holds the token issued in 3.1.2.a.')
user_flow('3.1.5.a','Allocate & Request Guest Drop-off Unlock','Shipper','Guest Web','DeliveryRequestsController','DeliveryRequestService',
          'POST /api/delivery-requests/{id}:openCompartment; guest token','OpenCompartmentAsync(id, token)',
          'Load request + policy','Require valid token and Approved state',result='200 OK: CompartmentReservationResponse',
          extra=[M('S','S','ReserveAvailableAsync; select eligible compartment'),M('S','DB','Save Allocated state, compartment, expiry and AuditLog'),R('DB','S','Saved'),M('S','S','OpenAsync; release reservation and mark Failed if dispatch fails')],
          pre='Approved request. A successful command response does not confirm deposit.')
S('3.1.5.b','Complete Guest Deposit from Device Journal',
  [P('U','Shipper','actor'),P('DEV','Locker IoT System','device'),P('L','MqttLockerListenerService'),P('SYNC','OfflinePinService')],
  [M('U','DEV','Place parcel and close the opened compartment'),A('DEV','L','MQTT Event via configured broker: lockers/{device}/events/offline (kind D)'),M('L','SYNC','ReceiveAsync(device, proof)'),M('SYNC','SYNC','Validate identity, deduplicate and sequence journal'),M('SYNC','SYNC','Apply approved deposit event and persist parcel state'),R('SYNC','L','OfflinePinSyncResult with acknowledgment'),A('L','DEV','MQTT ACK via configured broker: lockers/{device}/events/offline/ack: k1|eventId')],
  ['MqttLockerListenerService','OfflinePinService'],'The device emits a completed door-cycle journal for an allocated delivery.')
S('3.1.5.c','Apply Deposit & Create Stored Parcel',
  [P('SYNC','OfflinePinService'),P('S','DeliveryRequestService'),P('ALLOC','CompartmentAllocationService'),P('PUSH','ExpoPushNotificationService'),P('DB','ApplicationDbContext','persistence')],
  [M('SYNC','DB','Load delivery + compartment; verify phone, allocation and deadline'),R('DB','SYNC','Matching Allocated delivery'),M('SYNC','S','FinalizeDropOffAsync(deliveryId, completedAt)'),M('S','ALLOC','ReleaseAsync(deliveryId, null, completedAt)'),M('ALLOC','DB','Set ReleasedAt on tracked reservations'),R('ALLOC','S','Reservation changes tracked'),M('S','PUSH','EnqueueParcelStored(...)'),R('PUSH','S','Notification id; pending push is tracked'),M('S','DB','Save Parcel Stored + history + Deposited delivery + AuditLog'),R('DB','S','Saved inside journal transaction'),R('S','SYNC','Finalization complete'),M('SYNC','DB','Add or reconcile device PIN; add observed access; mark Applied')],
  ['OfflinePinService','DeliveryRequestService','CompartmentAllocationService','ExpoPushNotificationService'],'D journal has passed ordering and identity checks.','ReceiveAsync saves and commits after applying the event. Push is deferred while a transaction is active.')

# 3.2 Media is implemented; OCR extraction has no implementation.
S('3.2.3','Upload & Store Parcel Media',
  [P('U','Shipper','actor'),P('UI','Guest Web','client'),P('C','ImagesController','controller'),P('S','IImageStorageService','interface'),P('STORE','Configured Image Store','external')],
  [M('U','UI','Select or capture parcel image'),M('UI','C','POST /api/images; multipart file','http'),M('C','C','Reject empty file or file larger than 8 MB'),M('C','S','UploadAsync(stream, fileName, contentType)'),F('alt','Supabase URL and API key configured'),M('S','STORE','SupabaseImageStorageService: upload to configured bucket'),Else('Local fallback'),M('S','STORE','LocalImageStorageService: write validated image to local storage'),END,R('STORE','S','Image path or absolute URL'),R('S','C','Stored path / URL'),R('C','UI','201 Created { url }'),R('UI','U','Show image preview')],
  ['ImagesController','LocalImageStorageService','SupabaseImageStorageService','smart-locking-be.API/DependencyInjection.cs'],
  'Client boundary uses Guest Web here; the same public upload endpoint is reusable.','The image store lifeline is a configured alternative, not two simultaneous stores.')

# 3.3 Internal reusable allocation and worker processing.
S('3.3.2','Reserve Available Compartment',
  [P('OWNER','DeliveryRequestService / ReturnRequestService'),P('S','CompartmentAllocationService'),P('DB','ApplicationDbContext','persistence')],
  [M('OWNER','S','ReserveAvailableAsync(lockerId, deliveryId, returnId, expiresAt, verifyDoorOnDevice)'),M('S','S','Require exactly one owner: deliveryId XOR returnId'),M('S','DB','Begin Serializable transaction when relational; select first eligible compartment'),R('DB','S','Operational candidate ordered by Code, or null'),F('alt','No eligible compartment'),R('S','OWNER','null'),Else('Candidate available'),M('S','DB','Insert reservation; SaveChangesAsync and commit transaction'),R('DB','S','Reservation persisted'),R('S','OWNER','CompartmentReservation'),END],
  ['CompartmentAllocationService'],
  'Exclude active reservations, Stored/Overdue parcels and Allocated/Deposited returns.',
  'MQTT path requires Closed door status; Bluetooth sets verifyDoorOnDevice=true and defers door verification to device.')
for suffix,svc in [('a','DeliveryRequestService'),('b','ReturnRequestService')]:
    S('3.3.3.'+suffix,'Expire '+('Delivery' if suffix=='a' else 'Return')+' Reservations',
      [P('W','DeliveryRequestExpirationWorker','worker'),P('S',svc),P('A','CompartmentAllocationService'),P('DB','ApplicationDbContext','persistence')],
      [M('W','S','ExpireReservationsAsync()'),M('S','DB','Read Allocated requests whose ReservationExpiresAt <= now'),R('DB','S','Expired requests'),F('loop','Each expired request'),M('S','S','Set Expired and relevant expiry metadata'),M('S','A','ReleaseAsync(deliveryId, returnId, now)'),M('A','DB','Set ReleasedAt on unreleased tracked reservations'),R('A','S','Tracked changes'),END,M('S','DB','SaveChangesAsync; return count'),R('DB','S','Saved'),R('S','W','Expired count')],
      ['DeliveryRequestExpirationWorker',svc,'CompartmentAllocationService'],'Worker ticks once per minute; no human actor or UI initiates this flow.')

# 3.4 Backend eligibility, common dispatch, Bluetooth command preparation and journals.
S('3.4.2','Authorize Retrieval & Check Overdue Fee',
  [P('S','ParcelPickupService'),P('E','ParcelRetrievalEligibility'),P('DB','ApplicationDbContext','persistence')],
  [M('S','E','LoadAsync(db, residentUserId, parcelId, now)'),M('E','DB','Load Parcel, resident account, policy, compartment and OverdueCharge'),R('DB','E','Parcel graph or not found'),M('E','E','Check owner, active Resident, Stored/Overdue, now < MaxStorageUntil'),F('alt','Outstanding fee OR overdue billable period without Paid charge'),R('E','S','InvalidOperationException: payment required'),Else('No blocking fee and compartment exists'),R('E','S','Eligible Parcel'),END],
  ['ParcelPickupService','ParcelRetrievalEligibility'],'Invoked inside both RemoteApp and Bluetooth pickup paths.','Fee eligibility is checked even if the overdue calculation worker has not run yet.')
user_flow('3.4.3.a','Request Server-based Parcel Unlock','Resident','Resident Mobile App','ParcelsController','ParcelPickupService',
          'POST /api/parcels/{id}/unlock-pickup; Bearer Resident JWT','UnlockAsync(userId, id, ipAddress, deviceContext)',
          'Read Parcel graph via ParcelRetrievalEligibility.LoadAsync','Check retrieval eligibility, policy EnableRemoteUnlock and allocated compartment',
          result='202 Accepted / 409 Blocked / 503 Failed',sources=('ParcelRetrievalEligibility',),
          extra=[M('S','S','Call LockerAccessService.OpenAsync'),M('S','S','Map access result to PickupUnlockResponse')],
          pre='Server command route; successful dispatch does not prove physical opening.')
S('3.4.3.b','Dispatch Server Unlock via MQTT',
  [P('S','LockerAccessService'),P('DB','ApplicationDbContext','persistence'),P('D','MqttLockerCommandDispatcher'),P('DEV','Locker IoT System','device')],
  [M('S','DB','Load compartment + locker; create LockerAccessEvent'),R('DB','S','Operational and online state'),M('S','S','Validate context and blocking conditions; build workflow c1 command'),M('S','D','DispatchUnlockAsync(LockerUnlockCommand)'),A('D','DEV','Publish MQTT command via configured broker: lockers/{device}/doors/{channel}'),R('D','S','PublishAsync completed, or dispatcher throws'),M('S','DB','Save access Result: Succeeded, Blocked or Failed'),R('DB','S','Saved')],
  ['LockerAccessService','MqttLockerCommandDispatcher','BluetoothProtocol'],'Reusable for guest deposit, resident pickup, return deposit/pickup and emergency access.',
  'Succeeded records dispatch success. Physical completion is processed from device journals, not a fabricated device ACK.')
S('3.4.4.a','Prepare Bluetooth Parcel Pickup Command',
  [P('U','Resident','actor'),P('UI','Resident Mobile App','client'),P('C','BluetoothWorkflowController','controller'),P('S','BluetoothWorkflowService'),P('P','ParcelPickupService')],
  [M('U','UI','Choose Bluetooth pickup for owned parcel'),M('UI','C','POST /api/bluetooth/workflow/prepare { kind: P, subjectId: parcelId }; JWT','http'),M('C','S','PrepareAsync(residentUserId, request)'),M('S','S','Require enabled effective Bluetooth policy; verify requested device'),M('S','P','UnlockAsync(userId, parcelId, ..., Bluetooth)'),M('P','P','Check ownership, account, deadline and overdue fee'),M('P','P','Build Bluetooth command and record access'),R('P','S','PickupUnlockResponse.Bluetooth'),R('S','C','BluetoothCommandResponse'),R('C','UI','200 OK: deviceIdentifier, channel, command, expiresAt'),R('UI','U','Command is ready for local BLE transfer')],
  ['BluetoothWorkflowController','BluetoothWorkflowService','ParcelPickupService'],'Preparing a command requires server connectivity.','Other implemented kinds: D = shipper deposit, R = resident return, G = guest return pickup, N = new resident return draft.')
S('3.4.4.b','Build Bluetooth Unlock Command',
  [P('S','ParcelPickupService'),P('ACCESS','LockerAccessService'),P('CODEC','BluetoothProtocol'),P('DB','ApplicationDbContext','persistence')],
  [M('S','ACCESS','OpenAsync(request with AccessMethod = Bluetooth)'),M('ACCESS','DB','Load compartment, locker and transaction context'),R('DB','ACCESS','Device, channel and workflow identity'),M('ACCESS','ACCESS','Require operational locker / compartment; online status is not required for Bluetooth'),M('ACCESS','CODEC','CreateCommand(device, subject, channel, kind, phone, pin, expiresAt, commandId)'),R('CODEC','ACCESS','c1 wire command; two-minute expiry'),M('ACCESS','DB','Save LockerAccessEvent and return command; no MQTT unlock dispatch'),R('DB','ACCESS','Saved'),R('ACCESS','S','OpenLockerResponse with BluetoothCommandResponse')],
  ['LockerAccessService','BluetoothProtocol','ParcelPickupService'],'BluetoothWorkflowService selects the owning business service for each kind.')
S('3.4.4.c','Transfer Bluetooth Command & Reject Unsigned HTTP Journal',
  [P('DEV','Locker IoT System','device'),P('UI','Resident Mobile App','client'),P('C','OfflinePinController','controller'),P('S','OfflinePinService')],
  [A('UI','DEV','BLE boundary: transfer prepared c1 command'),A('DEV','UI','Expose unsigned o1 journal after completed door cycle'),M('UI','C','POST /api/bluetooth/offline/sync { events: [...] }; JWT','http'),M('C','S','SyncAsync(request)'),M('S','S','Reject unsigned HTTP device evidence'),R('S','C','ForbiddenException: UnverifiedEvidence'),R('C','UI','403 Forbidden'),A('DEV','DEV','Retain journal until replay through authenticated MQTT channel')],
  ['OfflinePinController','OfflinePinService','BluetoothProtocol'],'Backend defines command and journal protocol; actual mobile / firmware internals are outside this source checkout.',
  'JWT authenticates the user, not the ESP. Only the MQTT adapter may invoke ReceiveAsync.')
S('3.4.4.f','Reconcile Offline Bluetooth Event Results',
  [P('U','Resident','actor'),P('UI','Resident Mobile App','boundary'),P('C','OfflinePinController','controller'),P('S','OfflinePinService'),P('DB','ApplicationDbContext','database')],
  [M('U','UI','Request results for locally retained event identifiers'),M('UI','C','POST /api/bluetooth/offline/reconcile { eventIds }; Resident JWT','http'),M('C','S','ReconcileAsync(userId, request)'),M('S','S','Require valid userId and 1..100 distinct non-empty event ids'),M('S','DB','Read matching OfflineLockerEvents owned through resident delivery or return'),R('DB','S','Owned events ordered by device sequence'),M('S','S','Omit unknown and other-owner ids; map status, review reason and acknowledgment'),R('S','C','OfflinePinSyncResponse'),R('C','UI','200 OK: acknowledged results'),R('UI','U','Update local delivery status')],
  ['OfflinePinController','OfflinePinService','OfflinePinDtos'],'Events must already have been stored by the authenticated device adapter.',
  'This read-only endpoint does not accept proof, create an event or apply domain state.')
S('3.4.4.d','Issue Resident Permit for Locker-mediated Requests',
  [P('U','Resident','actor'),P('UI','Resident Mobile App','client'),P('C','BluetoothWorkflowController','controller'),P('S','BluetoothWorkflowService'),P('DB','BluetoothWorkflowStore','persistence')],
  [M('U','UI','Prepare resident permit while online'),M('UI','C','GET /api/bluetooth/workflow/resident-permit; Resident JWT','http'),M('C','S','GetPermitAsync(userId)'),M('S','DB','Check effective Bluetooth policy; load resident account, phone and device'),R('DB','S','ResidentBluetoothContext'),M('S','S','Require active Resident and operational locker; format 24-hour r1 permit'),R('S','C','ResidentBluetoothPermitResponse'),R('C','UI','200 OK: permit, deviceIdentifier, expiresAt'),R('UI','U','Permit available for supported offline operation')],
  ['BluetoothWorkflowController','BluetoothWorkflowService','BluetoothWorkflowStore','BluetoothProtocol'],'Permit acquisition is separate from preparing an individual unlock command.')
S('3.4.4.e','Handle Locker-mediated Resident Bluetooth Request',
  [P('DEV','Locker IoT System','device'),P('L','MqttLockerListenerService'),P('S','BluetoothWorkflowService'),P('CODEC','BluetoothProtocol')],
  [A('DEV','L','MQTT Request via configured broker: lockers/{device}/workflow/request (kind R, P or N)'),M('L','CODEC','ParseResidentPermit(permit, device, now)'),R('CODEC','L','Resident user id and phone'),M('L','L','Verify active Resident account'),M('L','S','PrepareAsync(userId, request with DeviceIdentifier)'),R('S','L','Device-scoped c1 command OR caught rejection'),A('L','DEV','MQTT Response via configured broker: lockers/{device}/workflow/response (c1 command OR FAIL)')],
  ['MqttLockerListenerService','BluetoothWorkflowService','BluetoothProtocol'],
  'Phone may lack internet while the locker retains MQTT connectivity.','This is not a claim that a permit is cryptographically signed; BluetoothProtocol currently validates wire format and expiry.')
S('3.4.5.a','Validate & Sequence Device Journals',
  [P('L','MqttLockerListenerService'),P('S','OfflinePinService'),P('CODEC','BluetoothProtocol'),P('DB','ApplicationDbContext','persistence')],
  [M('L','S','ReceiveAsync(device, proof)'),M('S','CODEC','ParseOfflineEvent(proof, device)'),R('CODEC','S','Typed OfflinePinEvidence'),M('S','DB','Begin Serializable transaction; look up event id, payload hash and device sequence'),R('DB','S','Existing event / sequence / cursor'),F('alt','Same event id and identical payload already stored'),R('S','L','Existing result + k1 acknowledgment'),Else('New event without conflicting id / sequence'),M('S','DB','Persist event; drain contiguous events after cursor.LastSequence'),M('S','S','Apply D, P, R or G journal according to subject state'),M('S','DB','Clear processed PIN, advance cursor; SaveChangesAsync; commit'),R('DB','S','Committed'),R('S','L','Applied / Pending / NeedsReview + acknowledgment'),END],
  ['MqttLockerListenerService','OfflinePinService','BluetoothProtocol'],
  'Only the MQTT listener invokes this path; ordering is scoped to device.',
  'Conflicting event ids or device sequences are rejected. A gap stays pending until the preceding sequence arrives.')
S('3.4.5.b','Apply Parcel Pickup & Release Compartment',
  [P('S','OfflinePinService'),P('DB','ApplicationDbContext','persistence')],
  [M('S','DB','Load parcel by delivery id and match device, channel, phone and allocation'),R('DB','S','Current parcel state'),F('alt','Parcel already Retrieved'),M('S','DB','Consume remaining PIN; record observed access; mark Applied'),Else('Stored / Overdue physical pickup accepted'),M('S','DB','Set Retrieved, RetrievedAt, CompartmentReleasedAt and release reservations'),M('S','DB','Set door Closed; add status history + observed access + AuditLog'),M('S','DB','Consume PIN and redact old PIN notification'),M('S','S','Mark NeedsReview if event clock or central overdue fee needs reconciliation'),END],
  ['OfflinePinService'],'P event passed shared journal validation; state is saved by ReceiveAsync.',
  'An offline physical pickup may be imported with NeedsReview; this path is distinct from server eligibility checks before unlock.')
user_flow('3.4.5.c','Confirm Pickup through Resident API','Resident','Resident Mobile App','ParcelsController','ParcelPickupService',
          'POST /api/parcels/{id}/confirm-pickup { accessEventId }; Resident JWT','ConfirmPickupAsync(userId, accessEventId)',
          'Load succeeded ResidentPickup access, parcel and compartment door state','Require access ownership, matching compartment and Closed door; handle already Retrieved',
          result='200 OK: PickupConfirmationResponse',extra=[M('S','DB','Save Retrieved, CompartmentReleasedAt and status history when not already completed'),R('DB','S','Saved')],
          pre='Explicit API alternative implemented in ParcelsController; request parcel id is checked against response.')

# 3.5 Operations: both operator and admin are authorized; role-specific variants keep UI boundaries explicit.
for suffix,actor,client in [('a','Locker Operator','Operator Web'),('b','Administrator','Admin Web')]:
    user_flow('3.5.2.'+suffix,'Load Locker Monitoring Dashboard',actor,client,'LockersController','LockerService',
              'GET /api/lockers?search=...; Bearer JWT','GetLockersAsync(userId, role, search)',
              'Read locker summaries and compartment counts; apply active assignment scope for operator',
              'Map operational status and connection status',pre='Administrator sees all lockers; Locker Operator sees assigned lockers.')
S('3.5.2.c','Subscribe to Operational Updates',
  [P('UI','Operator Web / Admin Web','client'),P('H','OperationsHub','hub'),P('DB','ApplicationDbContext','persistence'),P('N','SignalROperationsRealtimeNotifier')],
  [M('UI','H','Connect /hubs/operations with JWT'),M('H','H','OnConnectedAsync: add user:{userId:N} group'),M('UI','H','SubscribeLocker(lockerId)'),M('H','DB','Administrator OR active LockerOperator assignment?'),R('DB','H','Authorization result'),F('alt','Authorized'),M('H','H','Add connection to locker:{lockerId:N} group'),Else('Outside operator scope'),R('H','UI','HubException'),END,M('N','H','IHubContext.Clients.Group(...).SendAsync(operationUpdated, event)'),A('H','UI','operationUpdated notification')],
  ['OperationsHub','SignalROperationsRealtimeNotifier'],
  'Use 3.5.2.a or .b to identify the human actor and client for this reusable subscription.',
  'Business services invoke the notifier. Door status handling alone does not publish a SignalR event in the current listener.')
S('3.5.2.d','Update Door & Locker Connection State',
  [P('DEV','Locker IoT System','device'),P('L','MqttLockerListenerService'),P('DB','ApplicationDbContext','persistence')],
  [A('DEV','L','MQTT Status via configured broker: lockers/{device}/doors/{channel}/status (OPEN or CLOSED)'),M('L','L','Parse topic, channel and status; ignore malformed input'),M('L','DB','Load registered locker and compartments'),R('DB','L','Registered locker or null'),M('L','DB','Set Online, LastSeenAt, UpdatedAt and compartment DoorStatus'),M('L','L','When workflow codec is registered: skip legacy close-only finalization'),M('L','DB','SaveChangesAsync'),R('DB','L','State saved')],
  ['MqttLockerListenerService'],'Registered device reports door state; completed journal processing is separate.')
user_flow('3.5.3.a','Submit Resident Incident','Resident','Resident Mobile App','IncidentsController','IncidentService',
          'POST /api/incidents; Resident JWT','CreateResidentIncidentAsync(userId, request)',
          'Read active resident, registered locker, linked record and active assignment',
          'Validate type, one linked record, ownership and consistent locker / compartment',result='201 Created: IncidentDetailResponse',
          extra=[M('S','DB','Save Open incident + Created action + InApp notifications to operator or active administrators'),R('DB','S','Saved')],
          pre='Only the Resident-authorized endpoint creates a resident incident.')
user_flow('3.5.3.b','Submit Guest Incident','Shipper','Guest Web','IncidentsController','IncidentService',
          'POST /api/incidents/guest; X-Guest-Session-Token; rate limited','CreateGuestIncidentAsync(request, guestSessionToken)',
          'Read locker; resolve active delivery or return guest session from token hash',
          'Validate linked request and compartment; normalize evidence URL and contact phone; create Guest-source Open incident',result='201 Created: GuestIncidentResponse',
          extra=[M('S','DB','Save incident + InApp notification to assigned operator or administrators + AuditLog'),R('DB','S','Saved')],
          pre='A related delivery or return requires a valid guest-session token; an unlinked locker incident may omit it.')
for suffix,actor,client in [('a','Locker Operator','Operator Web'),('b','Administrator','Admin Web')]:
    user_flow('3.5.4.'+suffix,'Investigate, Escalate or Resolve Incident',actor,client,'OperatorIncidentsController','IncidentService',
              'PATCH /api/operator/incidents/{id}/status; JWT','UpdateStatusAsync(userId, role, id, request)',
              'Read incident under role / assignment scope','Validate transition; require notes for escalation and summary for resolution',
              extra=[M('S','DB','Save status + IncidentAction + reporter/admin notifications'),R('DB','S','Saved')],
              pre='Open → Investigating/Escalated; Investigating → Resolved/Escalated. Only Administrator can progress Escalated incidents.')
user_flow('3.5.4.c','Add Investigation Note','Locker Operator','Operator Web','OperatorIncidentsController','IncidentService',
          'POST /api/operator/incidents/{id}/actions; JWT','AddActionAsync(userId, role, id, request)',
          'Load incident within operator assignment','Require nonempty notes and incident not Resolved',
          extra=[M('S','DB','Save NoteAdded IncidentAction and UpdatedAt'),R('DB','S','Saved')],
          pre='Administrator is also authorized through Admin Web using the same endpoint.')
for suffix,actor,client in [('a','Locker Operator','Operator Web'),('b','Administrator','Admin Web')]:
    user_flow('3.5.5.'+suffix,'Request Audited Emergency Unlock',actor,client,'EmergencyUnlocksController','EmergencyUnlockService',
              'POST /api/emergency-unlocks; JWT','CreateAsync(userId, role, request)',
              'Read compartment; verify operator assignment when applicable and matching optional incident',
              'Require reason length >= 10; track Pending EmergencyUnlock',
              extra=[M('S','S','OpenAsync with OperatorEmergency / OperatorAuthorization'),M('S','DB','Save EmergencyUnlock result and AuditLog'),R('DB','S','Saved')],
              pre='Administrator bypasses assignment restriction; operator must have an active assignment.',
              note='Emergency result reflects command dispatch; there is no invented physical door ACK.')
for suffix,title,method,endpoint,change in [
    ('a','Create Maintenance Request','CreateAsync(userId, role, request)','POST /api/maintenance-requests','Validate description and matching compartment / optional incident; set Open'),
    ('b','Update Maintenance Status','UpdateAsync(userId, role, id, request)','PATCH /api/maintenance-requests/{id}','Require resolution summary for Closed; update timestamps and activity')]:
    user_flow('3.5.6.'+suffix,title,'Locker Operator','Operator Web','MaintenanceRequestsController','MaintenanceService',
              endpoint+'; JWT',method,'Read maintenance context and enforce assignment scope',change,
              result='201 Created' if suffix=='a' else '200 OK',extra=[M('S','DB','Save maintenance record + MaintenanceActivity + AuditLog'),R('DB','S','Saved')],
              pre='Administrator is also authorized through Admin Web. Maintenance records do not automatically change locker operational status.')
user_flow('3.5.6.c','Change Locker Operational Status','Administrator','Admin Web','LockersController','LockerService',
          'PUT /api/lockers/{id}/status; JWT','UpdateLockerStatusAsync(userId, role, id, request)',
          'Load locker and operator assignment; check active parcels, returns and reservations','Allow only Operational or OutOfService; require reason; record event and audit',extra=[M('S','DB','Save locker state, LockerEvent and AuditLog'),R('DB','S','Saved')],
          pre='Administrator may update any locker; Locker Operator is restricted to an active assignment.')
for suffix,actor,client in [('a','Locker Operator','Operator Web'),('b','Administrator','Admin Web')]:
    user_flow('3.5.9.'+suffix,'Search Operational Records as '+actor,actor,client,'OperationalRecordsController','OperationalRecordService',
              'GET /api/operational-records?query=...&lockerId=...&kind=...; JWT','SearchAsync(userId, role, query, lockerId, kind, pageNumber, pageSize)',
              'Scope lockers by role; search Parcel, ReturnRequest, Incident, MaintenanceRequest and EmergencyUnlock',
              'Merge, order by OccurredAt and paginate mapped records',result='200 OK: PagedResult<OperationalRecordResponse>',
              pre='Locker Operator can search only assigned lockers; Administrator can search all lockers.')
S('3.5.10.a','Request Safe Compartment Reset',
  [P('U','Locker Operator','actor'),P('UI','Operator Web','client'),P('C','CompartmentResetsController','controller'),P('S','CompartmentResetService'),P('STORE','CompartmentResetStore','database')],
  [M('U','UI','Confirm compartment is empty and enter reason'),M('UI','C','POST /api/compartment-resets/lockers/{lockerId}/compartments/{id}; JWT','http'),M('C','S','RequestAsync(userId, role, lockerId, compartmentId, request)'),M('S','STORE','Authorize assignment; load slot and expected subject'),R('STORE','S','Slot, pending request and ownership state'),M('S','S','Reject other goods; create stable commandId; set compartment OutOfService'),M('S','STORE','Save reset request AuditLog and dispatch command'),R('STORE','S','Pending or dispatch result'),R('S','C','CompartmentResetResponse'),R('C','UI','200 OK: Pending or Applied'),R('UI','U','Display command status')],
  ['CompartmentResetsController','CompartmentResetService','CompartmentResetStore'],'Operator has an active assignment. Administrator uses the same boundary without assignment restriction.')
S('3.5.10.b','Apply Compartment Reset Confirmation from MQTT',
  [P('UI','Operator Web','client'),P('DEV','Locker IoT System','device'),P('L','MqttLockerListenerService'),P('S','CompartmentResetService'),P('STORE','CompartmentResetStore','database')],
  [A('DEV','L','Publish z2 reset result through configured MQTT broker'),M('L','S','ReceiveAsync(device, proof)'),M('S','S','Parse proof; match device, channel, subject and commandId'),M('S','STORE','Begin transaction; load pending reset and current compartment'),R('STORE','S','Pending request state'),F('alt','Valid OK confirmation and not previously applied'),M('S','STORE','Release matching state; restore compartment; add LockerEvent and audit'),Else('Duplicate, failed or mismatched confirmation'),M('S','STORE','Keep idempotent result or persist failure without releasing goods'),END,M('S','STORE','SaveChangesAsync and commit'),R('STORE','S','Committed'),R('S','L','Task completed')],
  ['MqttLockerListenerService','CompartmentResetService','CompartmentResetStore'],'Only the MQTT adapter invokes ReceiveAsync. HTTP confirm never applies unsigned proof.')
S('3.5.7.a','Generate Pickup & Pre-transfer Reminders',
  [P('W','ParcelReminderWorker','worker'),P('S','ParcelReminderService'),P('DB','ApplicationDbContext','persistence'),P('PUSH','ExpoPushNotificationService')],
  [M('W','S','SendDailyRemindersAsync()'),M('S','DB','Load Stored / Overdue parcels before MaxStorageUntil with policy'),R('DB','S','Candidate parcels'),F('loop','Eligible parcel; reminder start reached and notification not already sent'),M('S','S','Compute Vietnam-local day window and <=24h clearance warning'),M('S','DB','Check prior InApp reminder / clearance warning'),R('DB','S','Deduplication result'),M('S','PUSH','EnqueueParcelPickupReminder(...)'),R('PUSH','S','Push id; InApp/Push records tracked'),END,M('S','DB','SaveChangesAsync'),M('S','PUSH','TrySendAsync(pushId) for queued notifications'),R('S','W','Queued count')],
  ['ParcelReminderWorker','ParcelReminderService','ParcelTimeline','ExpoPushNotificationService'],'Worker runs immediately and every 15 minutes; per-day deduplication happens in service.')
S('3.5.7.b','Deliver Queued Push Notification',
  [P('S','ExpoPushNotificationService'),P('DB','ApplicationDbContext','persistence'),P('EXPO','Expo Push Service','external'),P('UI','Resident Mobile App','client'),P('U','Resident','actor')],
  [M('S','DB','Load pending notification and active DeviceInstallation push tokens'),R('DB','S','Notification and device tokens'),F('opt','Eligible push target available'),M('S','EXPO','POST https://exp.host/--/api/v2/push/send','http'),R('EXPO','S','Push ticket / error response'),A('EXPO','UI','Platform push delivery boundary'),R('UI','U','Present notification'),END,M('S','DB','Save delivery attempt / ticket / result')],
  ['ExpoPushNotificationService'],'Delivery depends on available device tokens and external Expo service.',
  'External-to-client delivery is a protocol boundary; BE observes the push ticket, not a guaranteed human read receipt.')
for suffix,actor,client in [('a','Locker Operator','Operator Web'),('b','Administrator','Admin Web')]:
    user_flow('3.5.8.'+suffix,'Transfer Overdue Parcel to Collection Point',actor,client,'ParcelsController','ParcelService',
              'POST /api/parcels/{id}:transferToCollectionPoint; JWT','TransferOverdueAsync(userId, role, id)',
              'Load parcel, locker and resident; enforce operator scope',
              'Require MaxStorageUntil <= now and Stored/Overdue; set Removed and removal metadata',
              extra=[M('S','DB','Save Removed parcel + AuditLog; queue transfer notification'),R('DB','S','Saved'),M('S','S','Dispatch queued resident notification')],
              pre='API records operator-confirmed transfer; it does not issue an unlock command.',
              note='This implementation does not set DeliveryRequest.CompartmentReleasedAt or add status history during transfer.')

# 3.6 Authentication is split into registration, login, reset, token lifecycle and reusable OTP.
user_flow('3.6.2','Register Resident Account','Resident','Resident Mobile App','AuthController','AuthService',
          'POST /api/auth/register { phoneNumber, password, otpCode, registeredLockerId, ... }','RegisterAsync(request, ipAddress)',
          'Check unique phone / optional email; load operational registered locker',
          'Validate phone, name and password; verify and consume Registration OTP',result='200 OK: AuthTokenResponse',sources=('OtpService',),
          extra=[M('S','DB','In transaction: save Resident User + ResidentProfile using active policy default + AuditLog + RefreshToken'),R('DB','S','Commit')],
          pre='Registration OTP issued through 3.6.6.a. This public endpoint always creates Resident accounts.')
for suffix,actor,client in [('a','Resident','Resident Mobile App'),('b','Locker Operator','Operator Web'),('c','Administrator','Admin Web')]:
    user_flow('3.6.3.'+suffix,'Login '+actor+' Account',actor,client,'AuthController','AuthService',
              'POST /api/auth/login { loginIdentifier, password }','LoginAsync(request, ipAddress)',
              'Find user by normalized email or phone','Require Active user and verify password hash; issue JWT + random hashed refresh token',
              result='200 OK: AuthTokenResponse, including role and MustChangePassword',
              extra=[M('S','DB','Save LastLoginAt and RefreshToken'),R('DB','S','Saved')],
              pre='Shared auth endpoint accepts account credentials; client routes according to returned role.')
user_flow('3.6.3.d','Logout Current Refresh Token','Resident','Resident Mobile App','AuthController','AuthService',
          'POST /api/auth/logout { refreshToken }','LogoutAsync(request, ipAddress)',
          'Hash supplied token; find matching unrevoked RefreshToken','If present, set RevokedAt and RevokedByIp',result='204 No Content',
          extra=[M('S','DB','Save revocation when token exists'),R('DB','S','Saved')],
          pre='Also reusable by Operator Web and Admin Web; endpoint is AllowAnonymous.',
          note='Logout revokes the supplied refresh token; it does not blacklist an already issued access JWT.')
user_flow('3.6.3.e','Rotate Refresh Token','Resident','Resident Mobile App','AuthController','AuthService',
          'POST /api/auth/refresh-token { refreshToken }','RefreshTokenAsync(request, ipAddress)',
          'Load unrevoked, unexpired refresh token + active user','Issue replacement token pair; revoke old token and set ReplacedByTokenId',
          extra=[M('S','DB','Save token rotation'),R('DB','S','Saved')],pre='Same token lifecycle is reused by Operator Web and Admin Web.')
user_flow('3.6.4.a','Request Password Reset OTP','Resident','Resident Mobile App','AuthController','AuthService',
          'POST /api/auth/forgot-password { loginIdentifier }','RequestPasswordResetAsync(request)',
          'Find account by normalized phone or email','Resident phone: IssueAsync; Operator or Administrator email: IssueEmailAsync',result='204 No Content',
          sources=('OtpService','SmtpEmailSender'),pre='Unknown accounts return normally; the endpoint does not disclose account existence.')
user_flow('3.6.4.b','Reset Password with OTP','Resident','Resident Mobile App','AuthController','AuthService',
          'POST /api/auth/reset-password { loginIdentifier, otpCode, newPassword }','ResetPasswordAsync(request, ipAddress)',
          'Load account by identifier','Validate password; verify phone OTP for Resident or email OTP for Operator/Admin; hash password and clear MustChangePassword',
          result='204 No Content',sources=('OtpService','SmtpEmailSender'),extra=[M('S','DB','Save user and ResetPassword AuditLog'),R('DB','S','Saved')],
          pre='OTP must match destination, user and PasswordReset purpose.',
          note='This method does not revoke existing refresh tokens in the current implementation.')
user_flow('3.6.5','Configure Delivery Approval Mode','Resident','Resident Mobile App','ResidentsController','ResidentService',
          'PUT /api/residents/me/approval-mode { deliveryApprovalMode }; Resident JWT','UpdateApprovalModeAsync(userId, request)',
          'Load active Resident user + profile','Validate enum; ensure profile exists; update DeliveryApprovalMode and UpdatedAt',
          extra=[M('S','DB','SaveChangesAsync'),R('DB','S','Saved')],pre='Preference affects approval snapshots for subsequent delivery submissions.')
user_flow('3.6.6.a','Request Registration OTP','Resident','Resident Mobile App','AuthController','AuthService',
          'POST /api/auth/registration-otp/request { phoneNumber }','RequestRegistrationOtpAsync(request)',
          'Check whether phone is already registered','If unused phone: OtpService.IssueAsync(phone, Registration, null)',result='204 No Content',
          sources=('OtpService',),pre='OTP wire delivery is not implemented as an SMS provider in this checkout.')
S('3.6.6.b','Issue OTP Challenge',
  [P('OWNER','AuthService'),P('S','OtpService'),P('HASH','Sha256TokenHashService'),P('MAIL','SmtpEmailSender'),P('DB','ApplicationDbContext','persistence')],
  [M('OWNER','S','IssueAsync(phone, ...) or IssueEmailAsync(email, ...)'),M('S','DB','Load active unused challenges for destination + purpose'),R('DB','S','Existing challenges'),M('S','S','Revoke previous challenges; expiry = now + 10 minutes'),M('S','HASH','CreateNumericCode(); HashToken(code)'),R('HASH','S','Numeric OTP + hash'),M('S','DB','Save OtpChallenge with phone or email destination'),R('DB','S','Saved'),F('opt','Email destination'),M('S','MAIL','SendAsync(email, password-reset subject, code)'),R('MAIL','S','Email accepted or ServiceUnavailableException'),END,R('S','OWNER','Task completes')],
  ['AuthService','OtpService','Sha256TokenHashService','SmtpEmailSender'],'Reusable internal step for registration and password reset.',
  'Resident registration remains phone-based. Operator and Administrator password reset may use email.')
S('3.6.6.c','Verify & Consume OTP Challenge',
  [P('OWNER','AuthService'),P('S','OtpService'),P('DB','ApplicationDbContext','persistence')],
  [M('OWNER','S','VerifyAndConsumeAsync(phone, ...) or VerifyAndConsumeEmailAsync(email, ...)'),M('S','DB','Read latest unused challenge scoped by destination, purpose and user'),R('DB','S','Challenge'),M('S','S','Reject absent, expired or locked challenge'),F('alt','Code hash mismatches'),M('S','DB','Read active policy limits; increment attempts; add lock audit when threshold reached; save'),R('S','OWNER','InvalidOperationException: Invalid OTP'),Else('Code hash matches'),M('S','DB','Set UsedAt and SaveChangesAsync'),R('DB','S','Saved'),R('S','OWNER','OTP consumed'),END],
  ['AuthService','OtpService'],'Fallback policy limits: five attempts and 15-minute lockout.')
user_flow('3.6.7.a','View or Update Resident Profile','Resident','Resident Mobile App','ResidentsController','ResidentService',
          'PUT /api/residents/me; Resident JWT','UpdateProfileAsync(userId, request)',
          'Load active Resident User and ResidentProfile','Map profile or update editable fields and UpdatedAt',
          extra=[M('S','DB','SaveChangesAsync for update request'),R('DB','S','Saved or read-only result')],
          pre='Administrator cannot edit resident personal information through UsersController.')
user_flow('3.6.8.a','View and Mark Notifications','Resident','Resident Mobile App','NotificationsController','NotificationService',
          'GET /api/notifications or PATCH read endpoint; Resident JWT','GetForUserAsync / MarkReadAsync / MarkAllReadAsync',
          'Read notifications owned by current user','Order unread first or set ReadAt on owned notifications',
          extra=[M('S','DB','Save read state when requested'),R('DB','S','Saved')],pre='Resident is authenticated.')
user_flow('3.6.8.b','View Parcel List, Detail and Activity History','Resident','Resident Mobile App','ParcelsController','ParcelService',
          'GET /api/parcels, /{id} or /{id}/history; Resident JWT','GetParcelsAsync / GetParcelAsync / GetHistoryAsync',
          'Load parcels owned through ResidentProfile and DeliveryRequest','Apply filters; map details or order status history',
          pre='Resident can only view parcels linked to the current account.')
user_flow('3.6.9.a','Register Resident Push Device','Resident','Resident Mobile App','DeviceInstallationsController','DeviceInstallationService',
          'PUT /api/device-installations { installationId, expoPushToken, platform }; Resident JWT','RegisterAsync(userId, request)',
          'Require active Resident; normalize installation id, Expo token and Android/iOS platform','Create or reactivate installation; reject a token owned by another device',
          result='200 OK: DeviceInstallationResponse',extra=[M('S','DB','Save DeviceInstallation'),R('DB','S','Saved')],pre='The Expo token must use a supported Expo token format.')
user_flow('3.6.9.b','Deactivate Resident Push Device','Resident','Resident Mobile App','DeviceInstallationsController','DeviceInstallationService',
          'DELETE /api/device-installations/{installationId}; Resident JWT','DeactivateAsync(userId, installationId)',
          'Load installation by current user and normalized installation id','Set IsActive = false and UpdatedAt',result='204 No Content',
          extra=[M('S','DB','SaveChangesAsync'),R('DB','S','Saved')],pre='A resident can deactivate only an owned installation.')

# 3.7 Overdue charge calculation and PayOS payment lifecycle.
S('3.7.2','Calculate Overdue Storage Fee',
  [P('W','OverdueChargeWorker','worker'),P('S','OverdueChargeService'),P('DB','ApplicationDbContext','persistence')],
  [M('W','S','CalculateAsync()'),M('S','DB','Load Stored / Overdue parcels with PickupDueAt < now; include policy and charge'),R('DB','S','Eligible parcels'),F('loop','Each parcel with valid nonnegative rate and currency'),M('S','S','Transition Stored → Overdue; add status history'),F('opt','Fee > 0 and existing charge is not Paid'),M('S','S','Cutoff = min(now, MaxStorageUntil); hours = ceiling((cutoff - PickupDueAt).TotalHours)'),M('S','DB','Create Outstanding charge using policy rate OR recalculate using existing rate snapshot'),END,END,M('S','DB','SaveChangesAsync when processed count > 0'),R('DB','S','Saved'),R('S','W','Processed count')],
  ['OverdueChargeWorker','OverdueChargeService'],'Worker runs immediately and every 15 minutes.','Payment checkout is handled separately by OverduePaymentService.')
S('3.7.3','Create PayOS Payment Link for Overdue Charge',
  [P('U','Resident','actor'),P('UI','Resident Mobile App','client'),P('C','OverduePaymentsController','controller'),P('S','OverduePaymentService'),P('DB','ApplicationDbContext','persistence'),P('PAY','PayOS Payment Gateway','external')],
  [M('U','UI','Choose an outstanding overdue charge'),M('UI','C','POST /api/overdue-payments/charges/{chargeId}/checkout; JWT','http'),M('C','S','CreateCheckoutAsync(residentUserId, chargeId)'),M('S','DB','Lock charge row; load charge, parcel, delivery and resident ownership'),R('DB','S','Outstanding charge and pending transaction'),M('S','S','Validate whole positive VND amount; reuse or cancel expired pending link'),M('S','DB','Create pending PaymentTransaction before external call'),R('DB','S','Transaction saved'),M('S','PAY','CreatePaymentLinkAsync(orderCode, amount, returnUrl, cancelUrl)'),R('PAY','S','CheckoutUrl and provider status'),M('S','DB','Save CheckoutUrl'),R('S','C','OverduePaymentResponse'),R('C','UI','200 OK: transaction and checkout URL'),R('UI','U','Open PayOS checkout')],
  ['OverduePaymentsController','OverduePaymentService','PayOSPaymentGatewayService'],'Resident owns the charge and it remains Outstanding.','The pending transaction is persisted before contacting PayOS so a fast webhook remains reconcilable.')
S('3.7.4','Verify PayOS Webhook & Restore Retrieval Eligibility',
  [P('U','Resident','actor'),P('UI','PayOS Checkout','boundary'),P('PAY','PayOS Payment Gateway','external'),P('C','PaymentWebhooksController','controller'),P('G','PayOSPaymentGatewayService'),P('S','OverduePaymentService'),P('DB','ApplicationDbContext','persistence')],
  [M('U','UI','Complete overdue payment'),M('UI','PAY','Submit payment to PayOS'),M('PAY','C','POST /api/webhooks/payos with signed payload','http'),M('C','G','VerifyWebhook(payload)'),R('G','C','Verified PayOSWebhookData'),M('C','S','TryCompleteAsync(payment)'),M('S','DB','Find PaymentTransaction by order code; lock OverdueCharge row'),R('DB','S','Payment, charge, parcel and resident graph'),M('S','S','Validate amount, currency and reference; ignore duplicate final state'),F('alt','PayOS code = 00'),M('S','DB','Set payment Success and charge Paid; add audit and success notification'),Else('Payment failed'),M('S','DB','Set payment Failed; add audit and failure notification'),END,M('S','DB','SaveChangesAsync and commit'),R('S','C','true when overdue transaction handled'),R('C','PAY','200 OK'),R('PAY','UI','Display payment result'),R('UI','U','Payment result')],
  ['PaymentWebhooksController','PayOSPaymentGatewayService','OverduePaymentService'],'Public webhook endpoint; authenticity is established by PayOS signature verification.','A paid charge no longer blocks ParcelRetrievalEligibility.')
user_flow('3.7.5','View Overdue Payment History','Resident','Resident Mobile App','OverduePaymentsController','OverduePaymentService',
          'GET /api/overdue-payments or /{transactionId}; Resident JWT','GetHistoryAsync(userId) or GetAsync(userId, transactionId)',
          'Read PaymentTransactions owned through charge, parcel, delivery and ResidentProfile','Order history by RequestedAt or map selected transaction',
          result='200 OK: payment detail or history',pre='Resident can only read transactions belonging to the current account.')
S('3.7.8.a','Browse and Purchase Resident Subscription',
  [P('U','Resident','actor'),P('UI','Resident Mobile App','boundary'),P('PC','SubscriptionPlansController','controller'),P('PS','SubscriptionPlanService'),P('C','ResidentSubscriptionsController','controller'),P('S','ResidentSubscriptionService'),P('DB','ApplicationDbContext','database'),P('PAY','PayOS Payment Gateway','external')],
  [M('U','UI','Choose an available subscription plan'),M('UI','PC','GET /api/subscription-plans','http'),M('PC','PS','GetPlansAsync(activeOnly: true)'),M('PS','DB','Read active SubscriptionPlans'),R('DB','PS','Available plans'),R('PS','PC','SubscriptionPlanResponse list'),R('PC','UI','200 OK'),M('UI','C','POST /api/resident-subscriptions/subscribe { planId }; Resident JWT','http'),M('C','S','SubscribeAsync(userId, request)'),M('S','DB','Load resident and active plan'),R('DB','S','ResidentProfile and SubscriptionPlan'),M('S','S','Validate VND price and URLs; create duration snapshot and order code'),M('S','DB','Persist PendingPayment ResidentSubscription before provider call'),R('DB','S','Saved'),M('S','PAY','CreatePaymentLinkAsync(orderCode, amount, returnUrl, cancelUrl)'),R('PAY','S','Checkout URL'),R('S','C','SubscriptionCheckoutResponse'),R('C','UI','200 OK'),R('UI','U','Open PayOS checkout')],
  ['ResidentSubscriptionsController','ResidentSubscriptionService','SubscriptionPlansController','SubscriptionPlanService','PayOSPaymentGatewayService'],'Only active public plans are offered to the resident.')
S('3.7.8.b','Activate Resident Subscription from PayOS Webhook',
  [P('U','Resident','actor'),P('UI','PayOS Checkout','boundary'),P('PAY','PayOS Payment Gateway','external'),P('C','PaymentWebhooksController','controller'),P('G','PayOSPaymentGatewayService'),P('S','ResidentSubscriptionService'),P('DB','ApplicationDbContext','database')],
  [M('U','UI','Complete subscription payment'),M('UI','PAY','Submit payment'),M('PAY','C','POST /api/webhooks/payos with signed payload','http'),M('C','G','VerifyWebhook(payload)'),R('G','C','Verified PayOSWebhookData'),M('C','C','Try overdue payment first; continue when not handled'),M('C','S','ActivateSubscriptionAsync(payment)'),M('S','DB','Lock resident subscriptions and load order by ExternalOrderCode'),R('DB','S','Pending subscription and latest active end date'),M('S','S','Validate VND amount/reference; preserve purchased duration; append after active term'),M('S','DB','Set Active, PaidAt and transaction reference; commit'),R('S','C','Activation completed'),R('C','PAY','200 OK'),R('PAY','UI','Display payment result'),R('UI','U','Subscription activated')],
  ['PaymentWebhooksController','PayOSPaymentGatewayService','ResidentSubscriptionService'],'PayOS signature is valid and the order was not an overdue-charge transaction.',
  'Unknown sample or unrelated orders return 200 without creating a subscription.')
user_flow('3.7.8.c','View Current and Historical Subscriptions','Resident','Resident Mobile App','ResidentSubscriptionsController','ResidentSubscriptionService',
          'GET /api/resident-subscriptions/current or /history; Resident JWT','GetCurrentAsync(userId) or GetHistoryAsync(userId)',
          'Read subscriptions owned through ResidentProfile and include SubscriptionPlan','Return the active current interval or history ordered by CreatedAt',
          result='200 OK: current subscription or history',pre='The expiration worker separately changes ended Active subscriptions to Expired.')

# 3.8 Administration: account provision and first login remain distinct.
user_flow('3.8.2.a','Create Locker Operator Account','Administrator','Admin Web','UsersController','UserService',
          'POST /api/users { fullName, email, role: LockerOperator, lockerId?, ... }; Admin JWT','CreateUserAsync(adminId, request, ipAddress)',
          'Check duplicate email / optional phone','Hash supplied or generated temporary password; set LockerOperator, Active and MustChangePassword = true',
          extra=[M('S','DB','Save User + profile + optional OperatorAssignment + CreateUser AuditLog'),R('DB','S','Saved'),M('S','S','Send temporary credentials through IEmailSender')],
          result='200 OK: CreateUserResponse without password',pre='Only Administrator-authorized UsersController provisions this account. Email failure returns 503 after the account is committed.')
user_flow('3.8.2.b','Change Operator Password after First Login','Locker Operator','Operator Web','AuthController','AuthService',
          'POST /api/auth/change-password { currentPassword, newPassword }; JWT','ChangePasswordAsync(userId, request, ipAddress)',
          'Load user and refresh tokens','Verify current password; require new password >=8 and different; clear MustChangePassword',
          extra=[M('S','DB','Revoke old refresh tokens; save new password hash, AuditLog and fresh token pair'),R('DB','S','Saved')],
          result='200 OK: AuthTokenResponse',sources=('PasswordChangeRequiredMiddleware',),
          pre='Operator logs in through 3.6.3.b; middleware restricts use until password is changed.')
user_flow('3.8.2.c','Reissue Operator Temporary Password','Administrator','Admin Web','UsersController','UserService',
          'POST /api/users/{operatorId}/temporary-password; Admin JWT','ReissueTemporaryPasswordAsync(adminId, operatorId, ipAddress)',
          'Load LockerOperator account and active refresh tokens','Generate and hash temporary password; set MustChangePassword; revoke active refresh tokens',
          result='204 No Content',sources=('SmtpEmailSender',),
          extra=[M('S','DB','Save operator, revoked tokens and AuditLog'),R('DB','S','Saved'),M('S','S','Send new temporary password through IEmailSender')],
          pre='Operator must have an email address. Email failure returns 503 after the password reset is committed.')
user_flow('3.8.2.d','Update User Account or Status','Administrator','Admin Web','UsersController','UserService',
          'PUT /api/users/{id} or /api/users/{id}/status; Admin JWT','UpdateUserAsync or UpdateUserStatusAsync',
          'Load user, profile and active refresh tokens','Reject resident personal-data edit; update operator fields or status; revoke tokens when Locked or Disabled',
          extra=[M('S','DB','Save user changes and AuditLog'),R('DB','S','Saved')],
          pre='Administrator may view residents and change status; resident personal information remains resident-managed.')
user_flow('3.8.3.a','Assign Locker Operator','Administrator','Admin Web','UsersController','UserService',
          'POST /api/users/{operatorId}/assignments { lockerId, reason }; Admin JWT','AssignOperatorScopeAsync(adminId, operatorId, request)',
          'Load LockerOperator account; check locker has no unrevoked assignment','Require nonempty LockerId; create OperatorAssignment',
          extra=[M('S','DB','Save assignment + AssignOperatorScope AuditLog; read locker code'),R('DB','S','Saved')],
          pre='Reassignment requires revoking the current assignment first.')
user_flow('3.8.3.b','Revoke Locker Operator Assignment','Administrator','Admin Web','UsersController','UserService',
          'DELETE /api/users/{operatorId}/assignments/{assignmentId}?reason=...; Admin JWT','RevokeOperatorScopeAsync(adminId, operatorId, assignmentId, reason)',
          'Load assignment belonging to specified operator','Reject already revoked assignment; set RevokedAt and reason',result='204 No Content',
          extra=[M('S','DB','Save assignment + RevokeOperatorScope AuditLog'),R('DB','S','Saved')],
          pre='To change operator, execute this flow then 3.8.3.a for the new operator.')
user_flow('3.8.3.c','Create, Update or Deactivate Locker','Administrator','Admin Web','LockersController','LockerService',
          'POST /api/lockers; Administrator JWT','CreateLockerAsync(request)',
          'Load locker and validate unique code and device identifier','Create or update location/device metadata; soft delete by setting Inactive',
          extra=[M('S','DB','Save Locker, LockerEvent and AuditLog'),R('DB','S','Saved')],
          pre='Only Administrator manages locker infrastructure.')
user_flow('3.8.3.d','Create, Update or Deactivate Compartment','Administrator','Admin Web','LockersController','LockerService',
          'POST /api/lockers/{id}/compartments; Administrator JWT','CreateCompartmentAsync(lockerId, request)',
          'Load locker and compartment; validate code, hardware code and channel uniqueness','Create or update hardware mapping; deactivate by setting Inactive',
          extra=[M('S','DB','Save LockerCompartment, LockerEvent and AuditLog'),R('DB','S','Saved')],
          pre='Only Administrator creates or changes compartment infrastructure.')
user_flow('3.8.4.a','Create System Policy Version','Administrator','Admin Web','SystemPoliciesController','SystemPolicyService',
          'POST /api/system-policies; Administrator JWT','CreateAsync(adminId, request)',
          'Read maximum policy version','Validate timeouts, 7+7-day storage timeline, rate, currency and OTP limits; version = max + 1',
          result='201 Created: SystemPolicyResponse',extra=[M('S','DB','Save policy and SystemPolicy.Created AuditLog'),R('DB','S','Saved')],
          pre='New policy is activated through 3.8.4.c.')
user_flow('3.8.4.b','Edit Inactive System Policy','Administrator','Admin Web','SystemPoliciesController','SystemPolicyService',
          'PATCH /api/system-policies/{id}; Administrator JWT','UpdateAsync(adminId, id, request)',
          'Load target policy','Validate input; reject active policy; apply fields',
          extra=[M('S','DB','Save policy + SystemPolicy.Updated AuditLog'),R('DB','S','Saved')],
          pre='An active policy is immutable; create a new version to change it.')
user_flow('3.8.4.c','Activate System Policy','Administrator','Admin Web','SystemPoliciesController','SystemPolicyService',
          'POST /api/system-policies/{id}:activate; Administrator JWT','ActivateAsync(adminId, id)',
          'Begin transaction; load target and other active versions','Deactivate old versions with EffectiveTo = now; activate target with EffectiveFrom = now',
          extra=[M('S','DB','Save activation + AuditLog and commit'),R('DB','S','Committed')],pre='Only one version remains active.')
user_flow('3.8.5','Generate & Export System Report','Administrator','Admin Web','ReportsController','ReportService',
          'GET /api/reports/summary?from=...&to=...&lockerId=...; Admin JWT','GetSummaryAsync(from, to, lockerId)',
          'Count deliveries, returns, retrievals, open incidents, maintenance and emergency unlocks','Require to > from and valid optional locker',
          result='200 OK: JSON or CSV when Accept contains text/csv',pre='Controller defaults to the last 30 days; export format is selected at HTTP boundary.')
user_flow('3.8.6.a','Search System Audit Logs','Administrator','Admin Web','AuditLogsController','AuditLogService',
          'GET /api/audit-logs?query=...&actorUserId=...&action=...; Admin JWT','GetAsync(filters, cancellationToken, pageNumber, pageSize)',
          'Filter AuditLogs by term, actor, action, entity and date; count then paginate','Order descending by OccurredAt; clamp page size to 1..100',
          result='200 OK: PagedResult<AuditLogResponse>',pre='AuditLogsController is Administrator-only.')
user_flow('3.8.6.b','View Audit Log Detail','Administrator','Admin Web','AuditLogsController','AuditLogService',
          'GET /api/audit-logs/{id}; Admin JWT','GetByIdAsync(id)','Read audit log and actor','Map actor name or System/Guest',
          pre='Unknown id raises KeyNotFoundException (404).')
user_flow('3.8.9.a','Create or Update Subscription Plan','Administrator','Admin Web','SubscriptionPlansController','SubscriptionPlanService',
          'POST /api/admin/subscription-plans or PUT /api/admin/subscription-plans/{id}; Admin JWT','CreateAsync(request) or UpdateAsync(id, request)',
          'Validate code/name, whole-number VND price, duration and capacity; enforce unique code','Create active plan or update mutable plan fields and IsActive',
          result='201 Created or 200 OK: SubscriptionPlanResponse',extra=[M('S','DB','Save SubscriptionPlan'),R('DB','S','Saved')],pre='Public GET returns active plans only; admin GET returns all plans.')
user_flow('3.8.9.b','Create or Update Notification Rule','Administrator','Admin Web','NotificationRulesController','NotificationRuleService',
          'POST /api/notification-rules or PATCH /api/notification-rules/{id}; Admin JWT','CreateAsync(adminId, request) or UpdateAsync(adminId, id, request)',
          'Load policy; validate event, channel and lead time; enforce unique event/channel within policy','Reject active policy mutation; create or update rule and add AuditLog',
          result='201 Created or 200 OK: NotificationRuleResponse',extra=[M('S','DB','Save NotificationRule and AuditLog'),R('DB','S','Saved')],pre='Rules belonging to an active SystemPolicy are immutable.')
user_flow('3.8.9.c','View Administration Dashboard and Statistics','Administrator','Admin Web','AdminController','AdminService',
          'GET /api/Admin/dashboard or /statistics; Admin JWT','GetDashboardOverviewAsync(request) or GetSystemStatisticsAsync(request)',
          'Aggregate users, lockers, compartments, parcels, overdue charges, incidents and audit logs','Apply bounded trend/recent/day filters and map dashboard distributions',
          result='200 OK: AdminDashboardResponse or SystemStatisticsResponse',pre='AdminController is Administrator-only and performs read-only aggregation.')

# 3.9 Return lifecycle: current codec processes R/G journals directly in OfflinePinService.
user_flow('3.9.2','Create Resident Return Request','Resident','Resident Mobile App','ReturnsController','ReturnRequestService',
          'POST /api/returns { imageUrl, note?, deviceIdentifier? }; Resident JWT','CreateAsync(userId, request)',
          'Load active resident and chosen device or registered operational locker',
          'Require image; generate unique six-digit ReturnCode; set Created',result='201 Created: ReturnRequestResponse with empty code',
          extra=[M('S','DB','Save ReturnRequest and AuditLog'),R('DB','S','Saved')],
          pre='Image is uploaded separately. ReturnCode is stored at creation but hidden while Created / Allocated.')
user_flow('3.9.3','Allocate & Request Return Deposit Unlock','Resident','Resident Mobile App','ReturnsController','ReturnRequestService',
          'POST /api/returns/{id}:openCompartment; Resident JWT','OpenCompartmentAsync(userId, id)',
          'Load owned Created return and active policy','Require Created state; compute reservation expiry',
          extra=[M('S','S','ReserveAvailableAsync; select eligible compartment'),M('S','DB','Save Allocated return, compartment and reservation expiry'),R('DB','S','Saved'),M('S','S','OpenAsync; on failure release reservation and mark Failed')],
          result='200 OK: ReturnUnlockResponse',pre='For Bluetooth, BluetoothWorkflowService calls this method with accessMethod=Bluetooth.')
S('3.9.4','Complete Return Deposit & Expose Pickup Code',
  [P('L','MqttLockerListenerService'),P('S','OfflinePinService'),P('DB','ApplicationDbContext','persistence')],
  [M('L','S','ReceiveAsync(device, o1 journal with kind R)'),M('S','S','Validate identity; deduplicate and sequence journal'),M('S','DB','Load return + resident and compartment; check phone, code and allocation'),R('DB','S','Matching return OR unimported offline return'),M('S','S','ApplyReturnAsync: reconcile R event; reject conflicting transaction / code'),M('S','DB','Set Deposited and ResidentDepositedAt; release reservation; set door Closed'),M('S','DB','Track observed access + AuditLog + InApp / pending Push notifications'),R('S','L','Committed journal result + acknowledgment')],
  ['MqttLockerListenerService','OfflinePinService','OfflineReturnSync','ReturnRequestService'],
  'Code is generated at create time (or imported for offline return); deposit makes it visible in ReturnRequestResponse.',
  'Resident reads GET /api/returns/{id}. This current journal path does not call legacy FinalizeDepositAsync.')
user_flow('3.9.5.a','Validate Return Pickup Code & Create Guest Session','Shipper','Guest Web','ReturnPickupSessionsController','ReturnRequestService',
          'POST /api/return-pickup-sessions { lockerCode, pickupCode }','CreateAsync(ValidateReturnPickupRequest)',
          'Find return by locker code and six-digit pickup code; load active policy',
          'Require Deposited and allocated compartment; hash new shipper session token',
          result='201 Created: ReturnPickupSessionResponse',extra=[M('S','DB','Save ShipperSessionTokenHash and UpdatedAt'),R('DB','S','Saved')],
          pre='Anonymous guest endpoint; code must be exactly six numeric digits.')
user_flow('3.9.5.b','Request Return Pickup Compartment Unlock','Shipper','Guest Web','ReturnPickupSessionsController','ReturnRequestService',
          'POST /api/return-pickup-sessions/{id}:openCompartment; X-Guest-Session-Token',
          'OpenCompartmentAsync(id, guestSessionToken)','Load Deposited return, session hash and active policy',
          'Validate token hash and UpdatedAt-based session expiry',extra=[M('S','S','OpenAsync with ShipperReturnPickup / GuestSession')],
          result='200 OK: ReturnPickupSessionResponse',pre='Guest session was established in 3.9.5.a.')
S('3.9.6','Complete Guest Return Pickup',
  [P('L','MqttLockerListenerService'),P('S','OfflinePinService'),P('DB','ApplicationDbContext','persistence')],
  [M('L','S','ReceiveAsync(device, o1 journal with kind G)'),M('S','S','Validate identity; deduplicate and sequence journal'),M('S','DB','Load return, resident and compartment; match phone / device / allocation'),R('DB','S','Deposited or already Completed return'),M('S','S','ApplyReturnAsync: reject conflicting compartment or pickup before deposit'),M('S','DB','Set Completed, ShipperPickedUpAt, CompartmentReleasedAt; clear session hash'),M('S','DB','Set door Closed; track observed access + AuditLog and notifications'),R('S','L','Committed result + acknowledgment')],
  ['MqttLockerListenerService','OfflinePinService','OfflineReturnSync'],
  'Shipper action and Guest Web authorization are shown in 3.9.5.a/b; completion is device initiated.',
  'Duplicate completion preserves original completion timestamps; current journal path does not call legacy FinalizePickupAsync.')

# Class views use actual source members and typed UML edges. Each large feature is split by responsibility.
def component(key,title,controller,interface,implementation,methods,dependencies=()):
    boxes=[];rels=[]
    if controller:
        source=(BE/src(controller)[0]).read_text(encoding='utf-8-sig')
        declarations=list(re.finditer(r'public\s+(?:async\s+)?[\w<>,?.]+\s+(\w+)\s*\(',source))
        ops=[]
        for i,d in enumerate(declarations):
            body=source[d.start():declarations[i+1].start() if i+1<len(declarations) else len(source)]
            if any(re.search(r'\.'+re.escape(m)+r'\s*\(',body) for m in methods):ops.append(d[1])
        boxes.append((controller,ops[:5],0,0));rels.append((controller,interface,'dependency','uses'))
    impl_methods=[m+'#2' if interface=='IReturnPickupSessionService' and m in ('CreateAsync','GetAsync','OpenCompartmentAsync') else m for m in methods]
    boxes.extend([(interface,methods,1,0),(implementation,impl_methods,1,1)])
    rels.append((implementation,interface,'realization','implements'))
    for i,(dep,members) in enumerate(dependencies):
        col,row=[(0,1),(2,1),(1,2),(0,2)][i]
        boxes.append((dep,members,col,row));rels.append((implementation,dep,'dependency','uses'))
    class_specs.append(dict(key=key,title=title,boxes=boxes,relations=rels,focal=implementation))

def domain(key,title,boxes,rels):
    class_specs.append(dict(key=key,title=title,boxes=boxes,relations=rels))

component('3.1.1.a','Guest Session & Approval Services','DeliveryRequestsController','IDeliveryRequestService','DeliveryRequestService',
          ['CreateAsync','SubmitAsync','GetAsync','ApproveDeliveryRequestAsync','RejectDeliveryRequestAsync'],
          [('ApplicationDbContext',['DeliveryRequests','ResidentProfiles','SystemPolicies','SaveChangesAsync']),('ITokenHashService',['CreateSecureToken','HashToken']),('IPushNotificationService',['EnqueueDeliveryApprovalRequest','TrySendAsync'])])
domain('3.1.1.b','Delivery Request Domain',[
    ('ResidentProfile',['Id','UserId','DeliveryApprovalMode'],0,0),('DeliveryRequest',['Id','Status','GuestSessionTokenHash','ResidentProfileId','LockerId'],1,0),
    ('Locker',['Id','Code','OperationalStatus'],2,0),('SystemPolicy',['Id','GuestSessionTimeoutMinutes','ManualApprovalTimeoutMinutes'],1,1)],
    [('DeliveryRequest','ResidentProfile','association','recipient','0..*','0..1'),('DeliveryRequest','Locker','association','locker','0..*','1'),('DeliveryRequest','SystemPolicy','association','policy snapshot','0..*','1')])
component('3.2.1.a','Implemented Image Upload Contracts','ImagesController','IImageStorageService','SupabaseImageStorageService',['UploadAsync'],[])
component('3.2.1.b','Local Image Storage Alternative','ImagesController','IImageStorageService','LocalImageStorageService',['UploadAsync'],[])
component('3.3.1.a','Allocation Service Contracts',None,'ICompartmentAllocationService','CompartmentAllocationService',
          ['ReserveAvailableAsync','ReleaseAsync'],[('ApplicationDbContext',['CompartmentReservations','LockerCompartments','Parcels','ReturnRequests'])])
domain('3.3.1.b','Compartment Reservation Domain',[
    ('DeliveryRequest',['Id','AllocatedCompartmentId','ReservationExpiresAt'],0,0),('CompartmentReservation',['Id','DeliveryRequestId','ReturnRequestId','ExpiresAt','ReleasedAt'],1,0),
    ('ReturnRequest',['Id','AllocatedCompartmentId','ReservationExpiresAt'],2,0),('LockerCompartment',['Id','LockerId','DoorStatus','OperationalStatus'],1,1)],
    [('CompartmentReservation','DeliveryRequest','association','delivery owner (XOR return)','0..*','0..1'),('CompartmentReservation','ReturnRequest','association','return owner (XOR delivery)','0..*','0..1'),('CompartmentReservation','LockerCompartment','association','reserved compartment','0..*','1')])
component('3.4.1.a','Parcel Pickup Service','ParcelsController','IParcelPickupService','ParcelPickupService',
          ['UnlockAsync','ConfirmPickupAsync'],[('ApplicationDbContext',['Parcels','LockerAccessEvents','LockerCompartments','SaveChangesAsync']),('ILockerAccessService',['OpenAsync']),('ParcelRetrievalEligibility',['LoadAsync'])])
component('3.4.1.b','Locker Access & Transport Contracts',None,'ILockerAccessService','LockerAccessService',
          ['OpenAsync'],[('ApplicationDbContext',['LockerCompartments','LockerAccessEvents','SaveChangesAsync']),('ILockerCommandDispatcher',['DispatchUnlockAsync']),('IBluetoothMessageCodec',['CreateCommand'])])
component('3.4.1.c','MQTT Command Transport',None,'ILockerCommandDispatcher','MqttLockerCommandDispatcher',['DispatchUnlockAsync'],[])
component('3.4.1.d','Bluetooth Workflow Orchestration','BluetoothWorkflowController','IBluetoothWorkflowService','BluetoothWorkflowService',
          ['PrepareAsync','GetPermitAsync','AttachImageAsync'],[('IBluetoothWorkflowStore',['IsEnabledAsync','GetResidentAsync','GetSubjectDeviceAsync']),('IBluetoothMessageCodec',['CreateResidentPermit','CreateCommand']),('IParcelPickupService',['UnlockAsync'])])
component('3.4.1.e','Device Journal Reconciliation','OfflinePinController','IOfflinePinService','OfflinePinService',
          ['SyncAsync','ReceiveAsync','GetEventsAsync','ConfirmProvisionAsync'],[('ApplicationDbContext',['OfflineLockerEvents','OfflineLockerCursors','OfflineLockerPins','SaveChangesAsync']),('IBluetoothMessageCodec',['ParseOfflineEvent','CreateOfflineAcknowledgment']),('IDeliveryRequestService',['FinalizeDropOffAsync'])])
domain('3.4.1.f','Pickup State & Evidence Domain',[
    ('DeliveryRequest',['Id','AllocatedCompartmentId','CompartmentReleasedAt'],0,0),('Parcel',['Id','DeliveryRequestId','Status','PickupDueAt','MaxStorageUntil'],1,0),
    ('OverdueCharge',['Id','ParcelId','Amount','Status'],2,0),('LockerAccessEvent',['Id','ParcelId','AccessMethod','Result'],1,1)],
    [('Parcel','DeliveryRequest','association','origin','0..1','1'),('OverdueCharge','Parcel','association','charge','0..1','1'),('LockerAccessEvent','Parcel','association','access evidence','0..*','0..1')])
component('3.5.1.a','Locker Monitoring Services','LockersController','ILockerService','LockerService',
          ['GetLockersAsync','GetLockerByIdAsync','UpdateLockerAsync','UpdateCompartmentStatusAsync'],[('ApplicationDbContext',['Lockers','LockerCompartments','OperatorAssignments'])])
component('3.5.1.b','Incident Service Contracts','IncidentsController','IIncidentService','IncidentService',
          ['CreateResidentIncidentAsync','CreateGuestIncidentAsync','GetOperationalIncidentsAsync','UpdateStatusAsync','AddActionAsync'],
          [('ApplicationDbContext',['Incidents','IncidentActions','Notifications']),('IOperationsRealtimeNotifier',['PublishToLockerAsync','PublishToUserAsync'])])
component('3.5.1.c','Maintenance Service Contracts','MaintenanceRequestsController','IMaintenanceService','MaintenanceService',
          ['CreateAsync','UpdateAsync','GetAsync','GetByIdAsync'],[('ApplicationDbContext',['MaintenanceRequests','MaintenanceActivities','AuditLogs'])])
component('3.5.1.d','Emergency Unlock Service','EmergencyUnlocksController','IEmergencyUnlockService','EmergencyUnlockService',
          ['CreateAsync'],[('ApplicationDbContext',['EmergencyUnlocks','LockerCompartments','OperatorAssignments','AuditLogs']),('ILockerAccessService',['OpenAsync'])])
component('3.5.1.e','Reminder Delivery Services',None,'IParcelReminderService','ParcelReminderService',
          ['SendDailyRemindersAsync'],[('ApplicationDbContext',['Parcels','Notifications','SaveChangesAsync']),('IPushNotificationService',['EnqueueParcelPickupReminder','TrySendAsync'])])
component('3.5.1.f','Realtime Notification Implementation',None,'IOperationsRealtimeNotifier','SignalROperationsRealtimeNotifier',
          ['PublishToLockerAsync','PublishToUserAsync'],[])
domain('3.5.1.g','Operational Incident Domain',[
    ('User',['Id','Role','Status'],0,0),('Incident',['Id','LockerId','Status','ReporterUserId','AssignedOperatorUserId'],1,0),
    ('Locker',['Id','Code','OperationalStatus'],2,0),('IncidentAction',['Id','IncidentId','ActionByUserId','ActionType'],1,1)],
    [('Incident','User','association','assigned operator','0..*','0..1'),('Incident','Locker','association','context','0..*','0..1'),('IncidentAction','Incident','association','action history','0..*','1')])
component('3.6.1.a','Authentication Contracts','AuthController','IAuthService','AuthService',
          ['RegisterAsync','LoginAsync','LogoutAsync','RefreshTokenAsync','ChangePasswordAsync'],
          [('ApplicationDbContext',['Users','ResidentProfiles','RefreshTokens','SaveChangesAsync']),('IPasswordHashService',['HashPassword','VerifyPassword']),('IJwtTokenService',['CreateAccessToken'])])
component('3.6.1.b','OTP Service',None,'IOtpService','OtpService',['IssueAsync','VerifyAndConsumeAsync'],
          [('ApplicationDbContext',['OtpChallenges','SystemPolicies','SaveChangesAsync']),('ITokenHashService',['CreateNumericCode','HashToken'])])
component('3.6.1.c','Resident Profile & Preferences','ResidentsController','IResidentService','ResidentService',
          ['GetProfileAsync','UpdateProfileAsync','UpdateApprovalModeAsync'],[('ApplicationDbContext',['Users','ResidentProfiles','SaveChangesAsync'])])
domain('3.6.1.d','Account & Token Domain',[
    ('ResidentProfile',['Id','UserId','RegisteredLockerId','DeliveryApprovalMode'],0,0),('User',['Id','Role','Status','PasswordHash','MustChangePassword'],1,0),
    ('RefreshToken',['Id','UserId','TokenHash','ExpiresAt','RevokedAt'],2,0),('OtpChallenge',['Id','UserId','Purpose','CodeHash','AttemptCount'],1,1)],
    [('ResidentProfile','User','association','profile','0..1','1'),('RefreshToken','User','association','token owner','0..*','1'),('OtpChallenge','User','association','optional user','0..*','0..1')])
component('3.7.1.a','Implemented Overdue Fee Calculation',None,'IOverdueChargeService','OverdueChargeService',
          ['CalculateAsync'],[('ApplicationDbContext',['Parcels','OverdueCharges','ParcelStatusHistories','SaveChangesAsync'])])
domain('3.7.1.b','Overdue Charge Domain',[
    ('SystemPolicy',['Id','OverdueFeePerHour','Currency','MaxStorageHours'],0,0),('DeliveryRequest',['Id','SystemPolicyId'],1,0),
    ('Parcel',['Id','DeliveryRequestId','PickupDueAt','MaxStorageUntil','Status'],2,0),('OverdueCharge',['Id','ParcelId','RatePerHourSnapshot','Amount','Status'],2,1)],
    [('DeliveryRequest','SystemPolicy','association','fee policy snapshot','0..*','1'),('Parcel','DeliveryRequest','association','origin','0..1','1'),('OverdueCharge','Parcel','association','charge','0..1','1')])
component('3.8.1.a','Admin User & Assignment Services','UsersController','IUserService','UserService',
          ['CreateUserAsync','AssignOperatorScopeAsync','RevokeOperatorScopeAsync'],
          [('ApplicationDbContext',['Users','OperatorAssignments','AuditLogs','SaveChangesAsync']),('IPasswordHashService',['HashPassword'])])
component('3.8.1.b','Policy Version Management','SystemPoliciesController','ISystemPolicyService','SystemPolicyService',
          ['CreateAsync','UpdateAsync','ActivateAsync'],[('ApplicationDbContext',['SystemPolicies','AuditLogs','SaveChangesAsync'])])
component('3.8.1.c','System Reports','ReportsController','IReportService','ReportService',
          ['GetSummaryAsync'],[('ApplicationDbContext',['DeliveryRequests','ReturnRequests','Parcels','Incidents','MaintenanceRequests'])])
component('3.8.1.d','System Audit Queries','AuditLogsController','IAuditLogService','AuditLogService',
          ['GetAsync','GetByIdAsync'],[('ApplicationDbContext',['AuditLogs','Users'])])
domain('3.8.1.e','Locker Assignment Domain',[
    ('User',['Id','Role','Status'],0,0),('OperatorAssignment',['Id','OperatorUserId','LockerId','AssignedByUserId','RevokedAt'],1,0),
    ('Locker',['Id','Code','OperationalStatus'],2,0)],
    [('OperatorAssignment','User','association','operator','0..*','1'),('OperatorAssignment','Locker','association','assigned locker','0..*','1')])
component('3.9.1.a','Resident Return Service','ReturnsController','IReturnRequestService','ReturnRequestService',
          ['CreateAsync','GetAsync','GetMineAsync','OpenCompartmentAsync','ExpireReservationsAsync'],
          [('ApplicationDbContext',['ReturnRequests','ResidentProfiles','SystemPolicies']),('ICompartmentAllocationService',['ReserveAvailableAsync','ReleaseAsync']),('ILockerAccessService',['OpenAsync'])])
component('3.9.1.b','Guest Return Pickup Service','ReturnPickupSessionsController','IReturnPickupSessionService','ReturnRequestService',
          ['CreateAsync','GetAsync','OpenCompartmentAsync','FinalizePickupAsync'],
          [('ITokenHashService',['CreateSecureToken','HashToken']),('ILockerAccessService',['OpenAsync'])])
domain('3.9.1.c','Return Request Domain',[
    ('ResidentProfile',['Id','UserId'],0,0),('ReturnRequest',['Id','ReturnCode','Status','ResidentProfileId','AllocatedCompartmentId'],1,0),
    ('Locker',['Id','Code'],2,0),('LockerCompartment',['Id','LockerId','HardwareChannel'],1,1)],
    [('ReturnRequest','ResidentProfile','association','owner','0..*','1'),('ReturnRequest','Locker','association','deposit locker','0..*','1'),('ReturnRequest','LockerCompartment','association','allocated slot','0..*','0..1')])

# Inline every backend call previously summarized by a UML ``ref`` frame.
# These expansions use actual services and methods from the current backend so
# each sequence can be read on its own in draw.io.
_INLINE_PARTICIPANTS = {}

_APPROVAL = [
    F('alt','ApprovalModeSnapshot = Auto'),
    M('S','S','Set Approved and DecisionAt'),
    Else('ApprovalModeSnapshot = Manual'),
    M('S','S','Set PendingApproval and ApprovalExpiresAt'),
    M('S','PUSH','EnqueueDeliveryApprovalRequest(userId, requestId, lockerCode)'),
    R('PUSH','S','Notification id'), END,
    M('S','DB','Save DeliveryRequest, notifications and AuditLog'), R('DB','S','Saved'),
]

_RESERVE = [
    M('S','ALLOC','ReserveAvailableAsync(lockerId, deliveryId, returnId, expiresAt, verifyDoorOnDevice)'),
    M('ALLOC','DB','Select eligible compartment and insert reservation'),
    R('DB','ALLOC','CompartmentReservation or null'), R('ALLOC','S','Reservation result'),
]

_OPEN = [
    M('S','ACCESS','OpenAsync(LockerOpenRequest)'),
    M('ACCESS','DB','Load compartment and locker; create LockerAccessEvent'),
    R('DB','ACCESS','Operational state and transaction context'),
    M('ACCESS','D','DispatchUnlockAsync(LockerUnlockCommand)'),
    A('D','DEV','Publish MQTT unlock command via configured broker'),
    R('D','ACCESS','PublishAsync completed or dispatcher throws'),
    M('ACCESS','DB','Save LockerAccessEvent result'), R('DB','ACCESS','Saved'),
    R('ACCESS','S','OpenLockerResponse'),
]

_JOURNAL_VALIDATION = [
    M('S','CODEC','ParseOfflineEvent(proof, device)'), R('CODEC','S','Typed OfflinePinEvidence'),
    M('S','DB','Begin transaction; check event id, payload hash and device sequence'),
    R('DB','S','Existing event and cursor state'),
    M('S','DB','Persist event and drain contiguous device sequence'),
]

_JOURNAL_VALIDATION_SYNC = [
    M('SYNC','CODEC','ParseOfflineEvent(proof, device)'), R('CODEC','SYNC','Typed OfflinePinEvidence'),
    M('SYNC','DB','Begin transaction; check event id, payload hash and device sequence'),
    R('DB','SYNC','Existing event and cursor state'),
    M('SYNC','DB','Persist event and drain contiguous device sequence'),
]

_REF_EXPANSIONS = {}

_INLINE_SOURCES = {
    '3.1.3': ('ExpoPushNotificationService',),
    '3.1.5.a': ('CompartmentAllocationService','LockerAccessService','MqttLockerCommandDispatcher'),
    '3.1.5.b': ('BluetoothProtocol','DeliveryRequestService','CompartmentAllocationService','ExpoPushNotificationService'),
    '3.4.3.a': ('LockerAccessService','MqttLockerCommandDispatcher'),
    '3.4.4.a': ('ParcelRetrievalEligibility','LockerAccessService','BluetoothProtocol'),
    '3.4.4.c': ('BluetoothProtocol',),
    '3.5.5.a': ('LockerAccessService','MqttLockerCommandDispatcher'),
    '3.5.5.b': ('LockerAccessService','MqttLockerCommandDispatcher'),
    '3.5.8.a': ('ExpoPushNotificationService',), '3.5.8.b': ('ExpoPushNotificationService',),
    '3.9.3': ('CompartmentAllocationService','LockerAccessService','MqttLockerCommandDispatcher'),
    '3.9.4': ('BluetoothProtocol',), '3.9.5.b': ('LockerAccessService','MqttLockerCommandDispatcher'),
    '3.9.6': ('BluetoothProtocol',),
}

for _sequence in sequences:
    _key = _sequence['key']
    for _participant in _INLINE_PARTICIPANTS.get(_key, []):
        if all(existing[0] != _participant[0] for existing in _sequence['participants']):
            _sequence['participants'].append(_participant)
    _expansions = iter(_REF_EXPANSIONS.get(_key, []))
    _expanded_steps=[]
    for _step in _sequence['steps']:
        if _step[0]=='ref':
            _expanded_steps.extend(next(_expansions))
        else:
            _expanded_steps.append(_step)
    try:
        next(_expansions)
        raise AssertionError('Unused ref expansion for '+_key)
    except StopIteration:
        pass
    _sequence['steps']=_expanded_steps
    for _source in src(*_INLINE_SOURCES.get(_key, ())):
        if _source not in _sequence['sources']:_sequence['sources'].append(_source)

assert not any(step[0]=='ref' for sequence in sequences for step in sequence['steps'])

# Every sequence has an explicit external actor.  For reusable/internal
# continuations the actor records the upstream business initiator; scheduled
# jobs and device-originated flows use the external scheduler/device actor.
_ACTOR_CONTEXT = {
    '3.1.2.b': ('Shipper', 'UI', 'Start guest drop-off session', 'call'),
    '3.1.4.a': ('Shipper', 'UI', 'Submit parcel information for approval', 'call'),
    '3.1.5.c': ('Shipper', 'DEV', 'Place parcel and close compartment', 'call'),
    '3.3.2': ('Shipper', 'UI', 'Request compartment allocation', 'call'),
    '3.3.3.a': ('Shipper', 'UI', 'Track guest delivery request', 'call'),
    '3.3.3.b': ('Resident', 'UI', 'Track return request', 'call'),
    '3.4.2': ('Resident', 'UI', 'Request parcel retrieval', 'call'),
    '3.4.3.b': ('Resident', 'UI', 'Request compartment unlock', 'call'),
    '3.4.4.b': ('Resident', 'UI', 'Request Bluetooth pickup command', 'call'),
    '3.4.4.c': ('Resident', 'UI', 'Transfer prepared command at locker', 'call'),
    '3.4.4.e': ('Resident', 'DEV', 'Present resident permit and request', 'call'),
    '3.4.5.a': ('Resident', 'DEV', 'Complete locker operation and close door', 'call'),
    '3.4.5.b': ('Resident', 'UI', 'Complete parcel pickup at locker', 'call'),
    '3.5.2.c': ('Locker Operator', 'UI', 'Open live monitoring', 'call'),
    '3.5.2.d': ('Locker Operator', 'UI', 'Open live locker monitoring', 'call'),
    '3.5.10.b': ('Locker Operator', 'UI', 'Review compartment reset result', 'call'),
    '3.5.7.a': ('Resident', 'UI', 'View current parcel status', 'call'),
    '3.6.6.b': ('Resident', 'UI', 'Request OTP challenge', 'call'),
    '3.6.6.c': ('Resident', 'UI', 'Submit OTP for verification', 'call'),
    '3.7.2': ('Administrator', 'UI', 'Monitor overdue storage charges', 'call'),
    '3.9.4': ('Resident', 'DEV', 'Deposit return and close compartment', 'call'),
    '3.9.6': ('Shipper', 'DEV', 'Collect return and close compartment', 'call'),
}

_ACTOR_CLIENTS = {
    '3.1.4.a': 'Guest Web',
    '3.3.2': 'Guest Web',
    '3.3.3.a': 'Guest Web',
    '3.3.3.b': 'Resident Mobile App',
    '3.4.2': 'Resident Mobile App',
    '3.4.3.b': 'Resident Mobile App',
    '3.4.4.b': 'Resident Mobile App',
    '3.4.5.b': 'Resident Mobile App',
    '3.5.2.d': 'Operator Web',
    '3.5.7.a': 'Resident Mobile App',
    '3.6.6.b': 'Resident Mobile App',
    '3.6.6.c': 'Resident Mobile App',
    '3.7.2': 'Admin Web',
}

_ACTOR_DEVICES = {
    '3.1.5.c': ('Locker IoT System','Publish completed deposit journal via configured broker'),
    '3.4.5.a': ('Locker IoT System','Publish completed device journal via configured broker'),
    '3.9.4': ('Locker IoT System','Publish completed return-deposit journal via configured broker'),
    '3.9.6': ('Locker IoT System','Publish completed return-pickup journal via configured broker'),
}

_ACTOR_SCHEDULERS = {
    '3.3.3.a': 'Scheduled delivery-expiration tick',
    '3.3.3.b': 'Scheduled return-expiration tick',
    '3.5.7.a': 'Scheduled reminder tick',
    '3.7.2': 'Scheduled overdue-charge tick',
}

for _sequence in sequences:
    if not any(participant[2] == 'actor' for participant in _sequence['participants']):
        _actor, _target, _label, _kind = _ACTOR_CONTEXT[_sequence['key']]
        _sequence['participants'].insert(0, P('U', _actor, 'actor'))
        if _sequence['key'] in _ACTOR_CLIENTS:
            _sequence['participants'].insert(1, P('UI', _ACTOR_CLIENTS[_sequence['key']], 'client'))
        if _sequence['key'] in _ACTOR_DEVICES:
            _device, _device_message = _ACTOR_DEVICES[_sequence['key']]
            _sequence['participants'].insert(1, P('DEV', _device, 'device'))
            _sequence['steps'].insert(0, A('DEV', 'L', _device_message))
            if _sequence['key']=='3.1.5.c':
                _sequence['participants'].insert(2, P('L','MqttLockerListenerService'))
                _sequence['steps'].insert(1, M('L','SYNC','ReceiveAsync(device, proof)'))
        if _sequence['key'] in _ACTOR_SCHEDULERS:
            _sequence['participants'].insert(2, P('SCH','System Scheduler','external'))
            _sequence['steps'].insert(0, A('SCH','W',_ACTOR_SCHEDULERS[_sequence['key']]))
        _sequence['steps'].insert(0, M('U', _target, _label, _kind))

# Device-originated completion flows still pass through a visible locker user
# interface.  Model that presentation boundary explicitly so the human actor
# never connects directly to the IoT/device lifeline.
for _sequence in sequences:
    if any(participant[2]=='boundary' for participant in _sequence['participants']):
        continue
    _actor_id=next(participant[0] for participant in _sequence['participants'] if participant[2]=='actor')
    _device_id=next((participant[0] for participant in _sequence['participants'] if participant[2]=='device'),None)
    if _device_id is None:
        continue
    _sequence['participants'].insert(1,P('UI','Locker Interface','boundary'))
    for _index,_step in enumerate(_sequence['steps']):
        if len(_step)==4 and _step[0]==_actor_id:
            _sequence['steps'][_index]=M(_actor_id,'UI',_step[2],_step[3])
            _sequence['steps'].insert(_index+1,M('UI',_device_id,'Submit operation to Locker IoT System'))
            break

# Apply the final numeric-only Report 4 numbering to keys and cross-references
# after the source-backed specifications have been assembled.
from rp4_numbering import SEQUENCE_KEY_MAP, BLANK_KEY_MAP, renumber_text

def _renumber_value(value):
    if isinstance(value, str):
        return renumber_text(value)
    if isinstance(value, tuple):
        return tuple(_renumber_value(item) for item in value)
    if isinstance(value, list):
        return [_renumber_value(item) for item in value]
    return value

for _sequence in sequences:
    _old_key = _sequence['key']
    _sequence['key'] = SEQUENCE_KEY_MAP[_old_key]
    _sequence['steps'] = _renumber_value(_sequence['steps'])
    _sequence['pre'] = renumber_text(_sequence['pre'])
    _sequence['note'] = renumber_text(_sequence['note'])

blank_sections = [
    (BLANK_KEY_MAP[key], title) for key, title in blank_sections
]
