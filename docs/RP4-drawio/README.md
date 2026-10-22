# RP4 — Native draw.io diagrams

Class diagrams are split by named use case, using the supplied JLAS XML form. Each contains only the relevant current backend declarations, DTOs and entity fields. No narrative notes or legends are embedded. Sequence files retain their numbered messages and square self-calls.

Backend: `D:\code_capstone\smart-locking-be`, branch `feature/bluetooth-offline-unlock`, commit `f3db0308538b3376dfa14c184924def1e0a578a3`.

51 use-case class pages; 87 sequence pages; 1 empty page for the unimplemented OCR flow.

Open a `.drawio` file through File → Open From → Device in diagrams.net, or import it through File → Import From → Device. All diagrams consist of editable native mxGraph shapes and connectors.

Within each chapter, class diagrams are numbered first and sequence diagrams follow. The aggregate file is RP4/RP4-Detail-Design.drawio; individual named files are in the RP4 chapter folders.

Dependency: dashed line / open arrow. Realization: dashed line / hollow triangle. Association: solid line / open arrow, with multiplicities. Composition uses a filled owner diamond; aggregation uses a hollow owner diamond. Constructor injection is not represented as composition. Signatures and types are extracted from C#; CancellationToken is omitted for display. Member scope is explicit in scripts/rp4_usecase_classes.py.

XML validation checks source hashes, signatures, class scope, numbering, native shapes, square self-calls, overlaps and connectors passing through classes. Native rendering uses mxGraph and draw.io shape definitions; render-check.json records page loading and text clipping. This verifies diagram rendering, not runtime business behavior or hardware.

Old drafts and original Markdown are preserved outside RP4 in backups. Backend and report documents were not edited.

## Class diagram files

| Section | Use case | File |
|---|---|---|
| 3.1.1 | Start Guest Drop-off Session - Class Diagram | [draw.io](../../RP4/3.1 Shipper Guest Drop-off/3.1.1 Start Guest Drop-off Session - Class Diagram.drawio) |
| 3.1.2 | Submit Recipient and Parcel Information - Class Diagram | [draw.io](../../RP4/3.1 Shipper Guest Drop-off/3.1.2 Submit Recipient and Parcel Information - Class Diagram.drawio) |
| 3.1.3 | Approve or Reject Delivery Request - Class Diagram | [draw.io](../../RP4/3.1 Shipper Guest Drop-off/3.1.3 Approve or Reject Delivery Request - Class Diagram.drawio) |
| 3.1.4 | Open Guest Drop-off Compartment - Class Diagram | [draw.io](../../RP4/3.1 Shipper Guest Drop-off/3.1.4 Open Guest Drop-off Compartment - Class Diagram.drawio) |
| 3.1.5 | Complete Parcel Drop-off - Class Diagram | [draw.io](../../RP4/3.1 Shipper Guest Drop-off/3.1.5 Complete Parcel Drop-off - Class Diagram.drawio) |
| 3.2.1 | Upload Parcel Image - Class Diagram | [draw.io](../../RP4/3.2 AI-Powered Waybill Processing (OCR)/3.2.1 Upload Parcel Image - Class Diagram.drawio) |
| 3.3.1 | Reserve Available Compartment - Class Diagram | [draw.io](../../RP4/3.3 Dynamic Locker Allocation/3.3.1 Reserve Available Compartment - Class Diagram.drawio) |
| 3.3.2 | Expire and Release Compartment Reservation - Class Diagram | [draw.io](../../RP4/3.3 Dynamic Locker Allocation/3.3.2 Expire and Release Compartment Reservation - Class Diagram.drawio) |
| 3.4.1 | Authorize and Unlock Parcel Pickup - Class Diagram | [draw.io](../../RP4/3.4 Multi-method Package Retrieval/3.4.1 Authorize and Unlock Parcel Pickup - Class Diagram.drawio) |
| 3.4.2 | Dispatch Locker Unlock Command - Class Diagram | [draw.io](../../RP4/3.4 Multi-method Package Retrieval/3.4.2 Dispatch Locker Unlock Command - Class Diagram.drawio) |
| 3.4.3 | Prepare Bluetooth Pickup Command - Class Diagram | [draw.io](../../RP4/3.4 Multi-method Package Retrieval/3.4.3 Prepare Bluetooth Pickup Command - Class Diagram.drawio) |
| 3.4.4 | Confirm Parcel Pickup - Class Diagram | [draw.io](../../RP4/3.4 Multi-method Package Retrieval/3.4.4 Confirm Parcel Pickup - Class Diagram.drawio) |
| 3.4.5 | Reconcile Offline Device Journal - Class Diagram | [draw.io](../../RP4/3.4 Multi-method Package Retrieval/3.4.5 Reconcile Offline Device Journal - Class Diagram.drawio) |
| 3.4.6 | Issue Resident Bluetooth Permit - Class Diagram | [draw.io](../../RP4/3.4 Multi-method Package Retrieval/3.4.6 Issue Resident Bluetooth Permit - Class Diagram.drawio) |
| 3.5.1 | Monitor Locker and Compartment Status - Class Diagram | [draw.io](../../RP4/3.5 Locker Operations, Monitoring & Incident Handling/3.5.1 Monitor Locker and Compartment Status - Class Diagram.drawio) |
| 3.5.2 | Report Resident or Guest Incident - Class Diagram | [draw.io](../../RP4/3.5 Locker Operations, Monitoring & Incident Handling/3.5.2 Report Resident or Guest Incident - Class Diagram.drawio) |
| 3.5.3 | Investigate and Resolve Incident - Class Diagram | [draw.io](../../RP4/3.5 Locker Operations, Monitoring & Incident Handling/3.5.3 Investigate and Resolve Incident - Class Diagram.drawio) |
| 3.5.4 | Perform Audited Emergency Unlock - Class Diagram | [draw.io](../../RP4/3.5 Locker Operations, Monitoring & Incident Handling/3.5.4 Perform Audited Emergency Unlock - Class Diagram.drawio) |
| 3.5.5 | Create and Update Maintenance Request - Class Diagram | [draw.io](../../RP4/3.5 Locker Operations, Monitoring & Incident Handling/3.5.5 Create and Update Maintenance Request - Class Diagram.drawio) |
| 3.5.6 | Update Locker Operational Status - Class Diagram | [draw.io](../../RP4/3.5 Locker Operations, Monitoring & Incident Handling/3.5.6 Update Locker Operational Status - Class Diagram.drawio) |
| 3.5.7 | Send Parcel Pickup Reminders - Class Diagram | [draw.io](../../RP4/3.5 Locker Operations, Monitoring & Incident Handling/3.5.7 Send Parcel Pickup Reminders - Class Diagram.drawio) |
| 3.5.8 | Transfer Overdue Parcel to Collection Point - Class Diagram | [draw.io](../../RP4/3.5 Locker Operations, Monitoring & Incident Handling/3.5.8 Transfer Overdue Parcel to Collection Point - Class Diagram.drawio) |
| 3.5.9 | Search Operational Records - Class Diagram | [draw.io](../../RP4/3.5 Locker Operations, Monitoring & Incident Handling/3.5.9 Search Operational Records - Class Diagram.drawio) |
| 3.5.10 | Safely Reset Locker Compartment - Class Diagram | [draw.io](../../RP4/3.5 Locker Operations, Monitoring & Incident Handling/3.5.10 Safely Reset Locker Compartment - Class Diagram.drawio) |
| 3.6.1 | Register Resident Account - Class Diagram | [draw.io](../../RP4/3.6 Resident Account, Preferences & Parcel Management/3.6.1 Register Resident Account - Class Diagram.drawio) |
| 3.6.2 | Login Account - Class Diagram | [draw.io](../../RP4/3.6 Resident Account, Preferences & Parcel Management/3.6.2 Login Account - Class Diagram.drawio) |
| 3.6.3 | Refresh Access Token - Class Diagram | [draw.io](../../RP4/3.6 Resident Account, Preferences & Parcel Management/3.6.3 Refresh Access Token - Class Diagram.drawio) |
| 3.6.4 | Logout Account - Class Diagram | [draw.io](../../RP4/3.6 Resident Account, Preferences & Parcel Management/3.6.4 Logout Account - Class Diagram.drawio) |
| 3.6.5 | Reset Forgotten Password - Class Diagram | [draw.io](../../RP4/3.6 Resident Account, Preferences & Parcel Management/3.6.5 Reset Forgotten Password - Class Diagram.drawio) |
| 3.6.6 | Change Password - Class Diagram | [draw.io](../../RP4/3.6 Resident Account, Preferences & Parcel Management/3.6.6 Change Password - Class Diagram.drawio) |
| 3.6.7 | Issue and Verify OTP - Class Diagram | [draw.io](../../RP4/3.6 Resident Account, Preferences & Parcel Management/3.6.7 Issue and Verify OTP - Class Diagram.drawio) |
| 3.6.8 | Configure Resident Profile and Approval Mode - Class Diagram | [draw.io](../../RP4/3.6 Resident Account, Preferences & Parcel Management/3.6.8 Configure Resident Profile and Approval Mode - Class Diagram.drawio) |
| 3.6.9 | View and Mark Resident Notifications - Class Diagram | [draw.io](../../RP4/3.6 Resident Account, Preferences & Parcel Management/3.6.9 View and Mark Resident Notifications - Class Diagram.drawio) |
| 3.6.10 | View Resident Parcel Activity - Class Diagram | [draw.io](../../RP4/3.6 Resident Account, Preferences & Parcel Management/3.6.10 View Resident Parcel Activity - Class Diagram.drawio) |
| 3.7.1 | Calculate Overdue Storage Fee - Class Diagram | [draw.io](../../RP4/3.7 Overdue Storage Fee Management/3.7.1 Calculate Overdue Storage Fee - Class Diagram.drawio) |
| 3.7.2 | Create and Review Overdue Payment - Class Diagram | [draw.io](../../RP4/3.7 Overdue Storage Fee Management/3.7.2 Create and Review Overdue Payment - Class Diagram.drawio) |
| 3.7.3 | Process PayOS Payment Webhook - Class Diagram | [draw.io](../../RP4/3.7 Overdue Storage Fee Management/3.7.3 Process PayOS Payment Webhook - Class Diagram.drawio) |
| 3.8.1 | Browse User and Operator Accounts - Class Diagram | [draw.io](../../RP4/3.8 Administrator System Management/3.8.1 Browse User and Operator Accounts - Class Diagram.drawio) |
| 3.8.2 | Create or Reissue Operator Credentials - Class Diagram | [draw.io](../../RP4/3.8 Administrator System Management/3.8.2 Create or Reissue Operator Credentials - Class Diagram.drawio) |
| 3.8.3 | Update Operator Account and Status - Class Diagram | [draw.io](../../RP4/3.8 Administrator System Management/3.8.3 Update Operator Account and Status - Class Diagram.drawio) |
| 3.8.4 | Assign or Revoke Locker Operator - Class Diagram | [draw.io](../../RP4/3.8 Administrator System Management/3.8.4 Assign or Revoke Locker Operator - Class Diagram.drawio) |
| 3.8.5 | Configure and Activate System Policy - Class Diagram | [draw.io](../../RP4/3.8 Administrator System Management/3.8.5 Configure and Activate System Policy - Class Diagram.drawio) |
| 3.8.6 | Generate Operations Report - Class Diagram | [draw.io](../../RP4/3.8 Administrator System Management/3.8.6 Generate Operations Report - Class Diagram.drawio) |
| 3.8.7 | View System Audit Logs - Class Diagram | [draw.io](../../RP4/3.8 Administrator System Management/3.8.7 View System Audit Logs - Class Diagram.drawio) |
| 3.8.8 | Manage Locker Infrastructure - Class Diagram | [draw.io](../../RP4/3.8 Administrator System Management/3.8.8 Manage Locker Infrastructure - Class Diagram.drawio) |
| 3.8.9 | Manage Locker Compartments - Class Diagram | [draw.io](../../RP4/3.8 Administrator System Management/3.8.9 Manage Locker Compartments - Class Diagram.drawio) |
| 3.9.1 | Create Resident Return Request - Class Diagram | [draw.io](../../RP4/3.9 Parcel Return Management/3.9.1 Create Resident Return Request - Class Diagram.drawio) |
| 3.9.2 | Allocate and Open Return Compartment - Class Diagram | [draw.io](../../RP4/3.9 Parcel Return Management/3.9.2 Allocate and Open Return Compartment - Class Diagram.drawio) |
| 3.9.3 | Validate Return Pickup Code - Class Diagram | [draw.io](../../RP4/3.9 Parcel Return Management/3.9.3 Validate Return Pickup Code - Class Diagram.drawio) |
| 3.9.4 | Open Guest Return Pickup Compartment - Class Diagram | [draw.io](../../RP4/3.9 Parcel Return Management/3.9.4 Open Guest Return Pickup Compartment - Class Diagram.drawio) |
| 3.9.5 | Reconcile Return Deposit and Pickup Journal - Class Diagram | [draw.io](../../RP4/3.9 Parcel Return Management/3.9.5 Reconcile Return Deposit and Pickup Journal - Class Diagram.drawio) |
