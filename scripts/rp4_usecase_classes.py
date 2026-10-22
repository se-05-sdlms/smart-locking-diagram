"""Named use-case views. Scope is explicit; all displayed declarations come from C#."""
import copy,re
from functools import lru_cache
from rp4_class_model import describe,build_models,FILES,balanced,BE

CASES=[]
def U(key,title,components,entities='',extra=None):
    # Components map actual type names to the operations used in this view.
    CASES.append(dict(key=key,title=title,components=components,entities=entities,extra=extra or {}))
def C(controller,action,interface,service,operation,**other):
    return {controller:action,interface:operation,service:operation,'ApplicationDbContext':'SaveChangesAsync',**other}

U('3.1.1','Start Guest Drop-off Session',{**C('DeliveryRequestsController','Create','IDeliveryRequestService','DeliveryRequestService','CreateAsync',ITokenHashService='CreateSecureToken HashToken'),'LockersController':'GetPublicLocker','ILockerService':'GetPublicLockerAsync','LockerService':'GetPublicLockerAsync'},
  'DeliveryRequest:Id,LockerId,Status,GuestSessionTokenHash,SessionExpiresAt,SystemPolicyId; Locker:Id,Code,OperationalStatus; SystemPolicy:Id,GuestSessionTimeoutMinutes,IsActive,EffectiveFrom,EffectiveTo')
U('3.1.6','Submit Recipient and Parcel Information',C('DeliveryRequestsController','Submit','IDeliveryRequestService','DeliveryRequestService','SubmitAsync',ITokenHashService='HashToken',IPushNotificationService='EnqueueDeliveryApprovalRequest TrySendAsync'),
  'DeliveryRequest:Id,ResidentProfileId,Status,RecipientPhoneSnapshot,ParcelImageUrl,ApprovalModeSnapshot,ApprovalExpiresAt; ResidentProfile:Id,UserId,DeliveryApprovalMode; User:Id,PhoneNumber,Status')
U('3.1.7','Approve or Reject Delivery Request',C('DeliveryRequestsController','GetPendingRequests ApproveRequest RejectRequest','IDeliveryRequestService','DeliveryRequestService','GetPendingRequestsForResidentAsync ApproveDeliveryRequestAsync RejectDeliveryRequestAsync'),
  'DeliveryRequest:Id,ResidentProfileId,Status,RecipientPhoneSnapshot,ParcelImageUrl,ApprovalModeSnapshot,ApprovalExpiresAt; ResidentProfile:Id,UserId,DeliveryApprovalMode; User:Id,PhoneNumber,Status')
U('3.1.8','Open Guest Drop-off Compartment',C('DeliveryRequestsController','OpenCompartment','IDeliveryRequestService','DeliveryRequestService','OpenCompartmentAsync',ICompartmentAllocationService='ReserveAvailableAsync ReleaseAsync',ILockerAccessService='OpenAsync',ITokenHashService='HashToken'),
  'DeliveryRequest:Id,LockerId,Status,AllocatedCompartmentId,ReservationExpiresAt; CompartmentReservation:Id,LockerCompartmentId,DeliveryRequestId,ExpiresAt,ReleasedAt')
U('3.1.9','Complete Parcel Drop-off',{'IDeliveryRequestService':'FinalizeDropOffAsync','DeliveryRequestService':'FinalizeDropOffAsync','ApplicationDbContext':'SaveChangesAsync','ICompartmentAllocationService':'ReleaseAsync','IPushNotificationService':'EnqueueParcelStored TrySendAsync'},
  'DeliveryRequest:Id,LockerId,ResidentProfileId,AllocatedCompartmentId,Status; Parcel:Id,DeliveryRequestId,Status,StoredAt,MaxStorageUntil; ParcelStatusHistory:Id,ParcelId,FromStatus,ToStatus,ChangedAt')

U('3.2.1','Upload Parcel Image',{'ImagesController':'UploadImage','IImageStorageService':'UploadAsync','LocalImageStorageService':'UploadAsync','SupabaseImageStorageService':'UploadAsync'})

U('3.3.1','Reserve Available Compartment',{'ICompartmentAllocationService':'ReserveAvailableAsync','CompartmentAllocationService':'ReserveAvailableAsync','ApplicationDbContext':'SaveChangesAsync'},
  'Locker:Id,OperationalStatus; LockerCompartment:Id,LockerId,Code,DoorStatus; CompartmentReservation:Id,LockerCompartmentId,DeliveryRequestId,ReturnRequestId,ExpiresAt,ReleasedAt; Parcel:Id,DeliveryRequestId,Status,RetrievedAt; ReturnRequest:Id,LockerId,AllocatedCompartmentId,Status,CompartmentReleasedAt')
U('3.3.4','Expire and Release Compartment Reservation',{'DeliveryRequestExpirationWorker':'ExecuteAsync','IDeliveryRequestService':'ExpireReservationsAsync','DeliveryRequestService':'ExpireReservationsAsync','IReturnRequestService':'ExpireReservationsAsync','ReturnRequestService':'ExpireReservationsAsync','ICompartmentAllocationService':'ReleaseAsync','ApplicationDbContext':'SaveChangesAsync'},
  'CompartmentReservation:Id,DeliveryRequestId,ReturnRequestId,ExpiresAt,ReleasedAt; DeliveryRequest:Id,Status,ReservationExpiresAt; ReturnRequest:Id,Status,ReservationExpiresAt')

U('3.4.1','Authorize and Unlock Parcel Pickup',C('ParcelsController','UnlockPickup','IParcelPickupService','ParcelPickupService','UnlockAsync',ParcelRetrievalEligibility='LoadAsync',ILockerAccessService='OpenAsync'),
  'Parcel:Id,DeliveryRequestId,Status,MaxStorageUntil,RetrievedAt; OverdueCharge:Id,ParcelId,Status,Amount; ResidentProfile:Id,UserId')
U('3.4.6','Dispatch Locker Unlock Command',{'ILockerAccessService':'OpenAsync','LockerAccessService':'OpenAsync','ILockerCommandDispatcher':'DispatchUnlockAsync','MqttLockerCommandDispatcher':'DispatchUnlockAsync','IBluetoothMessageCodec':'CreateCommand','ApplicationDbContext':'SaveChangesAsync'},
  'Locker:Id,DeviceIdentifier,ConnectionStatus,OperationalStatus; LockerCompartment:Id,LockerId,Code,DoorStatus; LockerAccessEvent:Id,LockerId,LockerCompartmentId,Result,OccurredAt')
U('3.4.7','Prepare Bluetooth Pickup Command',{'BluetoothWorkflowController':'Prepare','IBluetoothWorkflowService':'PrepareAsync','BluetoothWorkflowService':'PrepareAsync','IBluetoothWorkflowStore':'IsEnabledAsync GetResidentAsync GetSubjectDeviceAsync','IParcelPickupService':'UnlockAsync'},'')
U('3.4.8','Confirm Parcel Pickup',C('ParcelsController','ConfirmPickup','IParcelPickupService','ParcelPickupService','ConfirmPickupAsync'),
  'Parcel:Id,Status,RetrievedAt; DeliveryRequest:Id,AllocatedCompartmentId,CompartmentReleasedAt; LockerAccessEvent:Id,ParcelId,LockerCompartmentId,Result; LockerCompartment:Id,DoorStatus; ParcelStatusHistory:Id,ParcelId,FromStatus,ToStatus,ChangedAt')
U('3.4.9','Reconcile Offline Device Journal',C('OfflinePinController','Sync Reconcile','IOfflinePinService','OfflinePinService','SyncAsync ReconcileAsync ReceiveAsync',IBluetoothMessageCodec='ParseOfflineEvent CreateOfflineAcknowledgment'),
  'OfflineLockerEvent:Id,DeviceIdentifier,Sequence,Kind,Status,ReviewReason; OfflineLockerCursor:DeviceIdentifier,LastSequence')
U('3.4.10','Issue Resident Bluetooth Permit',{'BluetoothWorkflowController':'Permit','IBluetoothWorkflowService':'GetPermitAsync','BluetoothWorkflowService':'GetPermitAsync','IBluetoothWorkflowStore':'IsEnabledAsync GetResidentAsync','IBluetoothMessageCodec':'CreateResidentPermit'})

U('3.5.1','Monitor Locker and Compartment Status',C('LockersController','GetLockers GetLockerById GetCompartments','ILockerService','LockerService','GetLockersAsync GetLockerByIdAsync GetCompartmentsAsync'),
  'Locker:Id,Code,OperationalStatus,ConnectionStatus,LastSeenAt; LockerCompartment:Id,LockerId,Code,DoorStatus; OperatorAssignment:Id,OperatorUserId,LockerId,RevokedAt')
U('3.5.9','Report Resident or Guest Incident',C('IncidentsController','Create CreateGuest','IIncidentService','IncidentService','CreateResidentIncidentAsync CreateGuestIncidentAsync',IOperationsRealtimeNotifier='PublishToLockerAsync'),
  'Incident:Id,LockerId,ReporterUserId,Status,Description,CreatedAt; ResidentProfile:Id,UserId,RegisteredLockerId')
U('3.5.10','Investigate and Resolve Incident',C('OperatorIncidentsController','AddAction UpdateStatus','IIncidentService','IncidentService','AddActionAsync UpdateStatusAsync',IOperationsRealtimeNotifier='PublishToLockerAsync'),
  'Incident:Id,LockerId,Status,ResolutionSummary,ResolvedAt; IncidentAction:Id,IncidentId,ActionByUserId,Notes,CreatedAt; OperatorAssignment:Id,OperatorUserId,LockerId,RevokedAt')
U('3.5.11','Perform Audited Emergency Unlock',C('EmergencyUnlocksController','Create','IEmergencyUnlockService','EmergencyUnlockService','CreateAsync',ILockerAccessService='OpenAsync'),
  'EmergencyUnlock:Id,LockerId,LockerCompartmentId,Reason,OperatorUserId,RequestedAt,Result; AuditLog:Id,ActorUserId,Action,OccurredAt; OperatorAssignment:Id,OperatorUserId,LockerId,RevokedAt')
U('3.5.12','Create and Update Maintenance Request',C('MaintenanceRequestsController','Create Update','IMaintenanceService','MaintenanceService','CreateAsync UpdateAsync'),
  'MaintenanceRequest:Id,LockerId,Status,Description,CreatedAt; MaintenanceActivity:Id,MaintenanceRequestId,CreatedAt; OperatorAssignment:Id,OperatorUserId,LockerId,RevokedAt')
U('3.5.13','Update Locker Operational Status',C('LockersController','UpdateLocker','ILockerService','LockerService','UpdateLockerAsync'),
  'Locker:Id,Code,OperationalStatus,UpdatedAt; AuditLog:Id,ActorUserId,Action,OccurredAt')
U('3.5.14','Send Parcel Pickup Reminders',{'ParcelReminderWorker':'ExecuteAsync','IParcelReminderService':'SendDailyRemindersAsync','ParcelReminderService':'SendDailyRemindersAsync','IPushNotificationService':'EnqueueParcelPickupReminder TrySendAsync','ApplicationDbContext':'SaveChangesAsync'},
  'Parcel:Id,Status,StoredAt,MaxStorageUntil; SystemPolicy:Id,PickupReminderStartDay,ClearanceNoticeBeforeHours,IsActive; Notification:Id,UserId,CreatedAt')
U('3.5.15','Transfer Overdue Parcel to Collection Point',C('ParcelsController','TransferToCollectionPoint','IParcelService','ParcelService','TransferOverdueAsync',IPushNotificationService='EnqueueParcelTransferred TrySendAsync'),
  'Parcel:Id,Status,RemovedAt,RemovedByUserId,RemovalReason; AuditLog:Id,ActorUserId,Action,OccurredAt')
U('3.5.16','Search Operational Records',C('OperationalRecordsController','Get GetDetail','IOperationalRecordService','OperationalRecordService','SearchAsync GetDetailAsync'),
  'Parcel:Id,Status,UpdatedAt; ReturnRequest:Id,Status,UpdatedAt; Incident:Id,Status,UpdatedAt; MaintenanceRequest:Id,Status,UpdatedAt; EmergencyUnlock:Id,Result,RequestedAt')
U('3.5.17','Safely Reset Locker Compartment',{'CompartmentResetsController':'Context Start Status Confirm','ICompartmentResetService':'ContextAsync RequestAsync GetAsync ConfirmAsync ReceiveAsync','CompartmentResetService':'ContextAsync RequestAsync GetAsync ConfirmAsync ReceiveAsync','ICompartmentResetStore':'FindSlotAsync FindPendingAsync FindRequestAsync SaveChangesAsync','CompartmentResetStore':'FindSlotAsync FindPendingAsync FindRequestAsync SaveChangesAsync'},
  'Locker:Id,DeviceIdentifier,OperationalStatus; LockerCompartment:Id,LockerId,HardwareChannel,OperationalStatus,DoorStatus; AuditLog:Id,ActorUserId,Action,EntityId,Details,OccurredAt; LockerEvent:Id,LockerId,LockerCompartmentId,EventType,OccurredAt')

U('3.6.1','Register Resident Account',C('AuthController','Register','IAuthService','AuthService','RegisterAsync',IOtpService='VerifyAndConsumeAsync',IPasswordHashService='HashPassword',IJwtTokenService='CreateAccessToken',ITokenHashService='CreateSecureToken HashToken'),
  'User:Id,PhoneNumber,PasswordHash,Role,Status; ResidentProfile:Id,UserId,RegisteredLockerId,DeliveryApprovalMode')
U('3.6.7','Login Account',C('AuthController','Login','IAuthService','AuthService','LoginAsync',IPasswordHashService='VerifyPassword',IJwtTokenService='CreateAccessToken',ITokenHashService='CreateSecureToken HashToken'),
  'User:Id,PhoneNumber,PasswordHash,Role,Status,MustChangePassword; RefreshToken:Id,UserId,TokenHash,ExpiresAt,RevokedAt')
U('3.6.8','Refresh Access Token',C('AuthController','RefreshToken','IAuthService','AuthService','RefreshTokenAsync',ITokenHashService='HashToken CreateSecureToken',IJwtTokenService='CreateAccessToken'),
  'User:Id,Role,Status; RefreshToken:Id,UserId,TokenHash,ExpiresAt,RevokedAt')
U('3.6.9','Logout Account',C('AuthController','Logout','IAuthService','AuthService','LogoutAsync',ITokenHashService='HashToken'),
  'RefreshToken:Id,UserId,TokenHash,ExpiresAt,RevokedAt')
U('3.6.10','Reset Forgotten Password',C('AuthController','ForgotPassword ResetPassword','IAuthService','AuthService','RequestPasswordResetAsync ResetPasswordAsync',IOtpService='IssueAsync IssueEmailAsync VerifyAndConsumeAsync VerifyAndConsumeEmailAsync',IPasswordHashService='HashPassword',IEmailSender='SendAsync'),
  'User:Id,PhoneNumber,Email,Role,PasswordHash,Status')
U('3.6.11','Change Password',C('AuthController','ChangePassword','IAuthService','AuthService','ChangePasswordAsync',IPasswordHashService='VerifyPassword HashPassword',IJwtTokenService='CreateAccessToken',ITokenHashService='CreateSecureToken HashToken'),
  'User:Id,PasswordHash,MustChangePassword; RefreshToken:Id,UserId,TokenHash,RevokedAt')
U('3.6.12','Issue and Verify OTP',{'AuthController':'RequestRegistrationOtp','IAuthService':'RequestRegistrationOtpAsync','AuthService':'RequestRegistrationOtpAsync','IOtpService':'IssueAsync IssueEmailAsync VerifyAndConsumeAsync VerifyAndConsumeEmailAsync','OtpService':'IssueAsync IssueEmailAsync VerifyAndConsumeAsync VerifyAndConsumeEmailAsync','ITokenHashService':'CreateNumericCode HashToken','IEmailSender':'SendAsync','ApplicationDbContext':'SaveChangesAsync'},
  'OtpChallenge:Id,DestinationPhone,DestinationEmail,Purpose,CodeHash,ExpiresAt,AttemptCount,UsedAt,LockedUntil; SystemPolicy:Id,OtpMaxAttempts,OtpLockoutMinutes,IsActive')
U('3.6.13','Configure Resident Profile and Approval Mode',C('ResidentsController','GetProfile UpdateProfile UpdateApprovalMode','IResidentService','ResidentService','GetProfileAsync UpdateProfileAsync UpdateApprovalModeAsync'),
  'User:Id,Email,PhoneNumber; ResidentProfile:Id,UserId,RegisteredLockerId,DeliveryApprovalMode')
U('3.6.14','View and Mark Resident Notifications',C('NotificationsController','GetNotifications MarkRead MarkAllRead','INotificationService','NotificationService','GetForUserAsync MarkReadAsync MarkAllReadAsync'),
  'Notification:Id,UserId,Type,Channel,DeliveryStatus,ReadAt,CreatedAt; User:Id,Role,Status')
U('3.6.15','View Resident Parcel Activity',C('ParcelsController','GetParcels GetParcel GetHistory','IParcelService','ParcelService','GetParcelsAsync GetParcelAsync GetHistoryAsync'),
  'Parcel:Id,DeliveryRequestId,Status,StoredAt,RetrievedAt,RemovedAt; DeliveryRequest:Id,ResidentProfileId,LockerId; ResidentProfile:Id,UserId; ParcelStatusHistory:Id,ParcelId,FromStatus,ToStatus,ChangedAt')
U('3.6.16','Manage Resident Device Installation',C('DeviceInstallationsController','Register Deactivate','IDeviceInstallationService','DeviceInstallationService','RegisterAsync DeactivateAsync'),
  'DeviceInstallation:Id,UserId,InstallationId,ExpoPushToken,Platform,IsActive,CreatedAt,UpdatedAt; User:Id,Role,Status')

U('3.7.1','Calculate Overdue Storage Fee',{'OverdueChargeWorker':'ExecuteAsync','IOverdueChargeService':'CalculateAsync','OverdueChargeService':'CalculateAsync','ApplicationDbContext':'SaveChangesAsync'},
  'Parcel:Id,Status,StoredAt,MaxStorageUntil; DeliveryRequest:Id,SystemPolicyId; OverdueCharge:Id,ParcelId,Amount,Status,RatePerHourSnapshot; SystemPolicy:Id,OverdueStartAfterHours,OverdueFeePerHour,MaxStorageHours,Currency; ParcelStatusHistory:Id,ParcelId,FromStatus,ToStatus,ChangedAt')
U('3.7.6','Create and Review Overdue Payment',{'OverduePaymentsController':'CreateCheckout Get GetHistory','IOverduePaymentService':'CreateCheckoutAsync GetAsync GetHistoryAsync','OverduePaymentService':'CreateCheckoutAsync GetAsync GetHistoryAsync','IPaymentGatewayService':'CreatePaymentLinkAsync GetPaymentLinkStatusAsync CancelPaymentLinkAsync','PayOSPaymentGatewayService':'CreatePaymentLinkAsync GetPaymentLinkStatusAsync CancelPaymentLinkAsync','ApplicationDbContext':'SaveChangesAsync'},
  'OverdueCharge:Id,ParcelId,Amount,Currency,Status,PaidAt; PaymentTransaction:Id,OverdueChargeId,ExternalOrderCode,CheckoutUrl,Amount,Currency,Status,RequestedAt,CompletedAt')
U('3.7.7','Process PayOS Payment Webhook',{'PaymentWebhooksController':'PayOS','IOverduePaymentService':'TryCompleteAsync','OverduePaymentService':'TryCompleteAsync','IPaymentGatewayService':'VerifyWebhook','PayOSPaymentGatewayService':'VerifyWebhook','ApplicationDbContext':'SaveChangesAsync'},
  'OverdueCharge:Id,ParcelId,Amount,Currency,Status,PaidAt; PaymentTransaction:Id,OverdueChargeId,ExternalOrderCode,Amount,Currency,Status,CompletedAt; Notification:Id,UserId,PaymentTransactionId,Type,DeliveryStatus; AuditLog:Id,ActorUserId,Action,EntityId,OccurredAt')
U('3.7.8','Purchase and Maintain Resident Subscription',{'ResidentSubscriptionsController':'Current History Subscribe','IResidentSubscriptionService':'GetCurrentAsync GetHistoryAsync SubscribeAsync','ResidentSubscriptionService':'GetCurrentAsync GetHistoryAsync SubscribeAsync','ApplicationDbContext':'SaveChangesAsync'},
  'ResidentSubscription:Id,ResidentProfileId,SubscriptionPlanId,StartDate,EndDate,Status,PriceSnapshot,ExternalOrderCode,ExternalTransactionId,PaidAt; SubscriptionPlan:Id,Code,Name,Price,DurationDays,MaxActiveParcels,IsActive; ResidentProfile:Id,UserId')

U('3.8.1','Browse User and Operator Accounts',C('UsersController','GetUsers GetUserById','IUserService','UserService','GetUsersAsync GetUserByIdAsync'),
  'User:Id,Email,PhoneNumber,Role,Status; ResidentProfile:Id,UserId,FullName')
U('3.8.12','Create or Reissue Operator Credentials',C('UsersController','CreateUser ReissueTemporaryPassword','IUserService','UserService','CreateUserAsync ReissueTemporaryPasswordAsync',IPasswordHashService='HashPassword',IEmailSender='SendAsync'),
  'User:Id,Email,PhoneNumber,Role,PasswordHash,Status,MustChangePassword; AuditLog:Id,ActorUserId,Action,OccurredAt')
U('3.8.14','Update Operator Account and Status',C('UsersController','UpdateUser UpdateUserStatus','IUserService','UserService','UpdateUserAsync UpdateUserStatusAsync'),
  'User:Id,Email,PhoneNumber,Role,Status,MustChangePassword; RefreshToken:Id,UserId,RevokedAt; AuditLog:Id,ActorUserId,Action,OccurredAt')
U('3.8.7','Assign or Revoke Locker Operator',C('UsersController','AssignOperatorScope RevokeOperatorScope','IUserService','UserService','AssignOperatorScopeAsync RevokeOperatorScopeAsync'),
  'User:Id,Role,Status; OperatorAssignment:Id,OperatorUserId,LockerId,RevokedAt; Locker:Id,Code; AuditLog:Id,ActorUserId,Action,OccurredAt')
U('3.8.8','Configure and Activate System Policy',C('SystemPoliciesController','Create Update Activate','ISystemPolicyService','SystemPolicyService','CreateAsync UpdateAsync ActivateAsync'),
  'SystemPolicy:Id,Version,IsActive,EffectiveFrom,EffectiveTo,CreatedByUserId; AuditLog:Id,ActorUserId,Action,OccurredAt')
U('3.8.9','Generate Operations Report',C('ReportsController','Summary','IReportService','ReportService','GetSummaryAsync'),
  'Locker:Id,OperationalStatus; Parcel:Id,Status,StoredAt; Incident:Id,Status; OverdueCharge:Id,Amount,Status')
U('3.8.10','View System Audit Logs',C('AuditLogsController','Get GetById','IAuditLogService','AuditLogService','GetAsync GetByIdAsync'),
  'AuditLog:Id,ActorUserId,Action,EntityType,EntityId,OccurredAt')
U('3.8.11','Manage Locker Infrastructure',C('LockersController','CreateLocker UpdateLocker SoftDeleteLocker','ILockerService','LockerService','CreateLockerAsync UpdateLockerAsync SoftDeleteLockerAsync'),
  'Locker:Id,Code,Address,DeviceIdentifier,OperationalStatus,UpdatedAt; LockerEvent:Id,LockerId,LockerCompartmentId,EventType,OccurredAt; AuditLog:Id,ActorUserId,Action,EntityId,OccurredAt')
U('3.8.13','Manage Locker Compartments',C('LockersController','CreateCompartment UpdateCompartment DeactivateCompartment UpdateCompartmentStatus','ILockerService','LockerService','CreateCompartmentAsync UpdateCompartmentAsync UpdateCompartmentStatusAsync'),
  'Locker:Id,Code,OperationalStatus; LockerCompartment:Id,LockerId,Code,HardwareCode,HardwareChannel,OperationalStatus; LockerEvent:Id,LockerId,LockerCompartmentId,EventType,OccurredAt; AuditLog:Id,ActorUserId,Action,EntityId,OccurredAt')
U('3.8.15','Manage Subscription Plans',C('SubscriptionPlansController','Get GetAll Create Update','ISubscriptionPlanService','SubscriptionPlanService','GetPlansAsync CreateAsync UpdateAsync'),
  'SubscriptionPlan:Id,Code,Name,Description,Price,DurationDays,MaxActiveParcels,IsActive,CreatedAt,UpdatedAt; ResidentSubscription:Id,SubscriptionPlanId,Status')
U('3.8.16','Manage Notification Rules',C('NotificationRulesController','Get GetById Create Update','INotificationRuleService','NotificationRuleService','GetAsync GetByIdAsync CreateAsync UpdateAsync'),
  'NotificationRule:Id,SystemPolicyId,EventType,Channel,LeadTimeMinutes,IsEnabled; SystemPolicy:Id,Version,IsActive; AuditLog:Id,ActorUserId,Action,EntityId,OccurredAt')
U('3.8.17','View Administration Dashboard',{'AdminController':'GetDashboard','IAdminService':'GetDashboardOverviewAsync','AdminService':'GetDashboardOverviewAsync','ApplicationDbContext':'SaveChangesAsync'})
U('3.8.18','View System Statistics',{'AdminController':'GetStatistics','IAdminService':'GetSystemStatisticsAsync','AdminService':'GetSystemStatisticsAsync','ApplicationDbContext':'SaveChangesAsync'})

U('3.9.1','Create Resident Return Request',C('ReturnsController','Create','IReturnRequestService','ReturnRequestService','CreateAsync',ITokenHashService='CreateNumericCode'),
  'ReturnRequest:Id,ResidentProfileId,LockerId,ReturnCode,ReturnReason,ReturnImageUrl,Status; ResidentProfile:Id,UserId,RegisteredLockerId; Locker:Id,OperationalStatus')
U('3.9.7','Allocate and Open Return Compartment',C('ReturnsController','OpenCompartment','IReturnRequestService','ReturnRequestService','OpenCompartmentAsync',ICompartmentAllocationService='ReserveAvailableAsync ReleaseAsync',ILockerAccessService='OpenAsync'),
  'ReturnRequest:Id,ResidentProfileId,LockerId,AllocatedCompartmentId,Status,ReservationExpiresAt; CompartmentReservation:Id,ReturnRequestId,LockerCompartmentId,ExpiresAt,ReleasedAt')
U('3.9.8','Validate Return Pickup Code',C('ReturnPickupSessionsController','Create Get','IReturnPickupSessionService','ReturnRequestService','CreateAsync GetAsync',ITokenHashService='CreateSecureToken HashToken'),
  'ReturnRequest:Id,LockerId,ReturnCode,ShipperSessionTokenHash,Status')
U('3.9.9','Open Guest Return Pickup Compartment',C('ReturnPickupSessionsController','OpenCompartment','IReturnPickupSessionService','ReturnRequestService','OpenCompartmentAsync',ITokenHashService='HashToken',ILockerAccessService='OpenAsync'),
  'ReturnRequest:Id,LockerId,AllocatedCompartmentId,ShipperSessionTokenHash,Status')
U('3.9.10','Reconcile Return Deposit and Pickup Journal',{'IOfflinePinService':'ReceiveAsync','OfflinePinService':'ReceiveAsync','IBluetoothMessageCodec':'ParseOfflineEvent CreateOfflineAcknowledgment','ApplicationDbContext':'SaveChangesAsync'},
  'ReturnRequest:Id,AllocatedCompartmentId,Status,ReturnCode,ShipperSessionTokenHash,ResidentDepositedAt,ShipperPickedUpAt,CompartmentReleasedAt; OfflineLockerEvent:Id,DeliveryId,Kind,Sequence,Status; OfflineLockerCursor:DeviceIdentifier,LastSequence')

@lru_cache(None)
def D(name):return describe(name)

# Whole/part semantics proven by domain navigation, FK exclusivity and the
# lifecycle implemented by the corresponding application service.
OWNERSHIP_RELATIONS={
    frozenset(('Locker','LockerCompartment')):
        ('Locker','LockerCompartment','composition','contains'),
    frozenset(('User','ResidentProfile')):
        ('User','ResidentProfile','composition','owns profile'),
    frozenset(('DeliveryRequest','Parcel')):
        ('DeliveryRequest','Parcel','composition','creates parcel'),
    frozenset(('Incident','IncidentAction')):
        ('Incident','IncidentAction','composition','records actions'),
    frozenset(('MaintenanceRequest','MaintenanceActivity')):
        ('MaintenanceRequest','MaintenanceActivity','composition','records activity'),
    frozenset(('Parcel','ParcelStatusHistory')):
        ('Parcel','ParcelStatusHistory','composition','records status history'),
    frozenset(('User','RefreshToken')):
        ('User','RefreshToken','composition','owns refresh tokens'),
    frozenset(('Parcel','OverdueCharge')):
        ('Parcel','OverdueCharge','composition','incurs charge'),
    frozenset(('DeliveryRequest','CompartmentReservation')):
        ('DeliveryRequest','CompartmentReservation','composition','owns reservations'),
    frozenset(('ReturnRequest','CompartmentReservation')):
        ('ReturnRequest','CompartmentReservation','composition','owns reservations'),
    frozenset(('ResidentProfile','DeliveryRequest')):
        ('ResidentProfile','DeliveryRequest','aggregation','receives delivery requests'),
    frozenset(('ResidentProfile','ReturnRequest')):
        ('ResidentProfile','ReturnRequest','aggregation','submits return requests'),
    frozenset(('OverdueCharge','PaymentTransaction')):
        ('OverdueCharge','PaymentTransaction','aggregation','has payment attempts'),
}

def method_bodies(node,operations):
    """Extract selected declarations and bodies (also explicit interface implementations)."""
    result=[]
    for op in operations:
        method=op.split('(',1)[0][2:]
        # Overloads are included conservatively; no unrelated operation enters the view.
        for match in re.finditer(r'\b'+re.escape(method)+r'\s*\(',node['source']):
            _,end=balanced(node['source'],match.end()-1)
            tail=node['source'][end:];opening=re.match(r'\s*\{',tail)
            if opening:
                body,_=balanced(node['source'],end+opening.end()-1,'{','}')
                result.append(body)
    return '\n'.join(result)

def build_usecases():
    legacy={m['key']:m for m in build_models()}
    # A domain entity has one stable structural view throughout Report 4.
    # Use the ordered union of fields selected by every use case so the same
    # class never appears with a contradictory-looking set of attributes.
    canonical_entity_fields={}
    for case in CASES:
        for entry in case['entities'].split(';'):
            if not entry.strip():continue
            entity_name,fields=entry.strip().split(':')
            bucket=canonical_entity_fields.setdefault(entity_name,[])
            for field in fields.split(','):
                if field not in bucket:bucket.append(field)
    result=[]
    for spec in CASES:
        nodes={};bodies={};selected=spec['components']
        # All methods must exist; no fabricated signatures or placeholder attributes.
        for name,methods in selected.items():
            n=copy.deepcopy(D(name));wanted=methods.split()
            n['operations']=[op for op in n['operations'] if op.split('(')[0][2:] in wanted]
            # This implementation has resident and guest overloads with the same names.
            # Keep the overloads of the contract that this particular use case invokes.
            if name=='ReturnRequestService':
                contract='IReturnPickupSessionService' if 'IReturnPickupSessionService' in selected else 'IReturnRequestService'
                allowed={op for op in D(contract)['operations'] if op.split('(')[0][2:] in wanted}
                n['operations']=[op for op in n['operations'] if op in allowed]
            found={op.split('(')[0][2:] for op in n['operations']}
            assert set(wanted)<=found,(spec['key'],name,set(wanted)-found)
            bodies[name]=method_bodies(n,n['operations'])
            n['attributes']=[];nodes[name]=n
        for entry in spec['entities'].split(';'):
            if not entry.strip():continue
            name,fields=entry.strip().split(':');n=copy.deepcopy(D(name))
            wanted=canonical_entity_fields[name]
            # During authoring this strict check exposes schema assumptions immediately.
            assert set(wanted)<=set(n['properties']),(spec['key'],name,set(wanted)-set(n['properties']))
            n['attributes']=['+ '+p+': '+n['properties'][p] for p in wanted];n['operations']=[];nodes[name]=n
        # Include the concrete DTOs appearing in the selected signatures, recursively.
        pending=list(nodes.values())
        while pending:
            n=pending.pop(0)
            signatures='\n'.join(n['operations']+n['attributes'])
            for name in dict.fromkeys(re.findall(r'\b[A-Z]\w+\b',signatures)):
                if name in nodes or name not in FILES:continue
                dto=D(name)
                if dto['role']=='DTO':
                    nodes[name]=copy.deepcopy(dto);pending.append(nodes[name])
        # Restrict injection fields and DbSets to the types actually drawn in this use case.
        for name,n in nodes.items():
            if name in selected:
                n['attributes']=[a for a in D(name)['attributes'] if a.startswith('- ') and a.split(': ')[-1].rstrip('?') in nodes]
                if n['role']=='persistence':
                    n['attributes']=[a for a in D(name)['attributes'] if any('DbSet<'+x+'>' in a for x in nodes if nodes[x]['role']=='entity')]
        edges=[];seen=set()
        def edge(a,b,kind,caption='',cards=(),basis='C# declaration'):
            if a==b or a not in nodes or b not in nodes:return
            ownership=OWNERSHIP_RELATIONS.get(frozenset((a,b)))
            if ownership:
                owner,part,kind,ownership_caption=ownership
                if (a,b)!=(owner,part):
                    a,b=b,a
                    cards=list(reversed(cards))
                caption=ownership_caption
                if not cards:
                    cards=['1','0..*'] if (owner,part)==('Locker','LockerCompartment') else []
            if (a,b,kind) in seen:return
            if kind in ('association','composition','aggregation') and any(
                candidate in seen for candidate in (
                    (b,a,'association'),(b,a,'composition'),(b,a,'aggregation'),
                    (a,b,'association'),(a,b,'composition'),(a,b,'aggregation'))
            ):return
            if not caption:
                if kind=='dependency': caption='«uses»'
                elif kind=='realization': caption='«implements»'
                elif kind=='composition': caption='contains'
                elif kind=='aggregation': caption='aggregates'
                elif kind=='association': caption='relates to'
            seen.add((a,b,kind));edges.append(dict(a=a,b=b,kind=kind,caption=caption,cards=list(cards),basis=basis))
        for name,n in nodes.items():
            for dep,param in n['dependencies']:edge(name,dep,'dependency')
            for parent in n['implements']:edge(name,parent,'realization')
            for dep in re.findall(r'GetRequiredService<(\w+)>',bodies.get(name,'')):edge(name,dep,'dependency')
            for dep in re.findall(r'\b([A-Z]\w+)\s*\.',bodies.get(name,'')):
                if dep in nodes and nodes[dep]['role'] not in ('entity','DTO'):edge(name,dep,'dependency')
            if n['role']=='persistence':
                for target,t in nodes.items():
                    if t['role']=='entity' and re.search(r'DbSet<'+target+r'>',n['source']):edge(name,target,'dependency','«persists»')
        # One contract consumer per DTO; prefer controller so DTOs are grouped cleanly on the left.
        ctrl_node = next((t for t in nodes.values() if t['role'] in ('controller','worker')), None)
        for name,n in nodes.items():
            if n['role']!='DTO':continue
            dto_caption='«accepts»' if name.endswith(('Request','Payload')) else '«returns»' if name.endswith(('Response','Result')) else '«uses»'
            if ctrl_node:
                edge(ctrl_node['name'],name,'dependency',caption=dto_caption)
            else:
                consumers=[t for t in nodes.values() if t['role'] in ('interface','worker','service','DTO') and re.search(r'\b'+name+r'\b','\n'.join(t['operations']+t['attributes'])) and t['name']!=name]
                if consumers:
                    consumer=sorted(consumers,key=lambda t:{'worker':0,'interface':1,'service':2,'DTO':3}[t['role']])[0]
                    edge(consumer['name'],name,'dependency',caption=dto_caption)
        for e in legacy['.'.join(spec['key'].split('.')[:2])+'.1']['edges']:
            if e['kind']=='association':edge(e['a'],e['b'],e['kind'],caption=e['caption'],cards=e['cards'],basis=e['basis'])
        # EF navigation mappings are relevant even when the related types were in another feature.
        for base in legacy.values():
            for e in base['edges']:
                if e['kind']=='association':edge(e['a'],e['b'],e['kind'],caption=e['caption'],cards=e['cards'],basis=e['basis'])
        from rp4_numbering import CLASS_KEY_MAP
        result.append(dict(key=CLASS_KEY_MAP[spec['key']],title=spec['title']+' - Class Diagram',nodes=list(nodes.values()),edges=edges,notes=[],ledger=[],scope=spec))
    return result
