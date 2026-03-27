# ClinicOps Database Models

> All models use UUID primary keys and automatic `created_at`/`updated_at` timestamps.
> Currency: XAF (Central African Franc) — stored as integers, no decimals.
> Phone format: +237XXXXXXXXX (Cameroon)

---

## Base Classes (`apps/core/models.py`)

### TimestampedModel (abstract)

Every model in the system inherits from this. It provides:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key, auto-generated with `uuid4` |
| `created_at` | DateTimeField | Set once when the record is first saved (`auto_now_add`) |
| `updated_at` | DateTimeField | Updated every time the record is saved (`auto_now`) |

Default ordering is `-created_at` (newest first).

### SoftDeleteModel (abstract, extends TimestampedModel)

Used by `Patient` and `Service` — records are never truly deleted.

| Field | Type | Description |
|-------|------|-------------|
| `is_deleted` | BooleanField | `False` by default, set to `True` on soft delete |
| `deleted_at` | DateTimeField | Timestamp of when soft delete occurred |

**Two managers:**
- `objects` — default, excludes soft-deleted records (`is_deleted=False`)
- `all_objects` — includes everything, used for ID generation and admin

**Methods:**
- `soft_delete()` — sets `is_deleted=True` and `deleted_at=now()`
- `restore()` — reverses a soft delete

---

## User (`apps/accounts/models.py`)

The custom user model. Authentication is phone-based (no username).

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `phone` | CharField(20) | **Login identifier**, unique, indexed |
| `email` | EmailField | Optional, unique if provided |
| `first_name` | CharField(100) | Required |
| `last_name` | CharField(100) | Required |
| `role` | CharField(20) | One of: `owner`, `admin`, `receptionist`, `nurse` |
| `clinic` | ForeignKey → Clinic | The clinic this user belongs to |
| `is_active` | BooleanField | `True` = can log in, `False` = deactivated |
| `must_change_password` | BooleanField | `True` on first login with temp password |
| `failed_login_attempts` | IntegerField | Resets on successful login |
| `locked_until` | DateTimeField | Account locked until this time (null = not locked) |
| `last_login_ip` | GenericIPAddressField | Recorded on each login |
| `password_changed_at` | DateTimeField | Last password change timestamp |
| `reset_code` | CharField(6) | SMS reset code (6 digits) |
| `reset_code_expires` | DateTimeField | Code expiry (15 minutes from generation) |

**Role hierarchy** (used for permission checks):
| Role | Level | French | Scope |
|------|-------|--------|-------|
| `owner` | 4 | Proprietaire | Full access, can create admins |
| `admin` | 3 | Administrateur | Day-to-day management |
| `receptionist` | 2 | Receptionniste | Patient intake, billing |
| `nurse` | 1 | Infirmier(e) | View patients, add services |

**Security behavior:**
- 5 failed login attempts → account locked for 15 minutes
- 5 failed reset code attempts → reset locked for 15 minutes

---

## Clinic (`apps/clinics/models.py`)

Represents a medical clinic. Each user belongs to exactly one clinic.

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(200) | Clinic name |
| `address` | TextField | Full address |
| `city` | CharField(100) | City |
| `region` | CharField(100) | Region |
| `phone_primary` | CharField(20) | Main phone number |
| `phone_secondary` | CharField(20) | Secondary phone (optional) |
| `email` | EmailField | Contact email |
| `registration_number` | CharField(50) | Government registration (e.g., RC/DLA/2020/B/1234) |
| `invoice_prefix` | CharField(10) | Default `"INV-"` |
| `invoice_numbering` | CharField(20) | `daily`, `monthly`, or `continuous` |
| `invoice_footer` | TextField | Text printed at bottom of invoices |
| `cash_threshold` | IntegerField | Default `500` XAF — reconciliation discrepancy alert |
| `mtn_momo_number` | CharField(20) | Displayed on invoices |
| `orange_money_number` | CharField(20) | Displayed on invoices |
| `bank_name` | CharField(100) | Displayed on invoices |
| `bank_account` | CharField(50) | Displayed on invoices |
| `is_active` | BooleanField | Clinic active status |

---

## Service (`apps/clinics/models.py`)

A billable service offered by the clinic. Uses **soft delete**.

| Field | Type | Description |
|-------|------|-------------|
| `clinic` | ForeignKey → Clinic | Which clinic offers this service |
| `name` | CharField(200) | Service name (unique per clinic) |
| `code` | CharField(20) | Short code (unique per clinic, e.g., `CONS-GEN`) |
| `category` | CharField(20) | One of: `consultation`, `laboratory`, `pharmacy`, `care` |
| `price` | IntegerField | Price in XAF (>= 0, no decimals) |
| `description` | TextField | Optional description |
| `is_active` | BooleanField | Whether the service can be added to new visits |

**Categories explained:**
| Value | French | Examples |
|-------|--------|----------|
| `consultation` | Consultation | General, Specialized, Pediatric |
| `laboratory` | Laboratoire | Malaria test, Blood count, Ultrasound |
| `pharmacy` | Pharmacie | Paracetamol, Amoxicillin |
| `care` | Soins | IM/IV injection, Dressing, Perfusion |

---

## Patient (`apps/patients/models.py`)

Patient records. Uses **soft delete**. All data scoped to a clinic.

| Field | Type | Description |
|-------|------|-------------|
| `clinic` | ForeignKey → Clinic | The clinic this patient belongs to |
| `patient_id` | CharField(20) | Auto-generated: `PAT-YYYYMMDD-XXXX` |
| `first_name` | CharField(150) | First name |
| `last_name` | CharField(150) | Last name |
| `phone` | CharField(20) | Primary phone (+237 format) |
| `phone_secondary` | CharField(20) | Secondary phone (optional) |
| `date_of_birth` | DateField | Nullable |
| `gender` | CharField(1) | `M`, `F`, or `O` |
| `address` | TextField | Patient address |
| `emergency_contact_name` | CharField(255) | Emergency contact |
| `emergency_contact_phone` | CharField(20) | Emergency contact phone |
| `notes` | TextField | Clinical notes |
| `outstanding_balance` | IntegerField | XAF amount owed |
| `registered_by` | ForeignKey → User | Who created this patient record |

**Computed properties:**
- `full_name` — `"{first_name} {last_name}"`
- `last_visit` — date of the most recent visit (from related visits)

**ID generation:** `PAT-YYYYMMDD-XXXX` where XXXX resets daily, scoped per clinic. Soft-deleted records are counted to prevent ID reuse.

---

## Visit (`apps/visits/models.py`)

A patient visit to the clinic.

| Field | Type | Description |
|-------|------|-------------|
| `visit_id` | CharField(20) | Auto-generated: `VIS-YYYYMMDD-XXXX` |
| `clinic` | ForeignKey → Clinic | Scoping |
| `patient` | ForeignKey → Patient | Which patient (PROTECT) |
| `visit_type` | CharField(20) | `walkin`, `appointment`, `followup`, `emergency` |
| `status` | CharField(20) | `open`, `invoiced`, `completed`, `cancelled` |
| `notes` | TextField | Visit notes |
| `created_by` | ForeignKey → User | Staff who created the visit |
| `cancelled_at` | DateTimeField | When cancelled (null if not) |
| `cancelled_by` | ForeignKey → User | Who cancelled (null if not) |
| `cancel_reason` | TextField | Reason for cancellation (required) |

**Status transitions:**
- `open` → `invoiced` — when an invoice is generated from this visit
- `invoiced` → `completed` — when the invoice is fully paid
- `open` → `cancelled` — manual cancellation by owner/admin
- `cancelled` (voided invoice) → `open` — when the invoice is voided, visit reopens

**Computed property:**
- `total` — sum of all `VisitService.line_total` for this visit

---

## VisitService (`apps/visits/models.py`)

A line item linking a service to a visit. This is where price snapshots are taken.

| Field | Type | Description |
|-------|------|-------------|
| `visit` | ForeignKey → Visit | Which visit (CASCADE) |
| `service` | ForeignKey → Service | Which service (PROTECT) |
| `quantity` | PositiveIntegerField | Default 1 |
| `unit_price` | IntegerField | **Snapshot** of `service.price` at time of addition |
| `price_override` | IntegerField | Nullable — custom price set by owner/admin |
| `override_reason` | TextField | Required if `price_override` is set |
| `added_by` | ForeignKey → User | Staff who added this service |

**Unique constraint:** One service per visit (`unique_together = ['visit', 'service']`).

**Computed property:**
- `line_total` — `(price_override or unit_price) * quantity`

**Why snapshot the price?** If a service price changes later, existing visits and invoices are not affected. The price at the time of service is what the patient pays.

---

## Invoice (`apps/billing/models.py`)

Generated from a visit's services.

| Field | Type | Description |
|-------|------|-------------|
| `invoice_number` | CharField(20) | Auto-generated: `INV-YYYYMM-XXXX` (monthly) |
| `visit` | OneToOneField → Visit | One invoice per visit (PROTECT) |
| `patient` | ForeignKey → Patient | Denormalized for queries |
| `clinic` | ForeignKey → Clinic | Scoping |
| `subtotal` | IntegerField | Sum of line items before discount |
| `discount_percent` | IntegerField | 0–100 |
| `discount_amount` | IntegerField | Calculated flat amount in XAF |
| `discount_reason` | TextField | Required if discount > 0 |
| `total` | IntegerField | `subtotal - discount_amount` |
| `paid_amount` | IntegerField | Cumulative payments received |
| `balance` | IntegerField | `total - paid_amount` |
| `status` | CharField(20) | `pending`, `partial`, `paid`, `cancelled` |
| `issued_at` | DateTimeField | When the invoice was created |
| `created_by` | ForeignKey → User | Staff who generated the invoice |
| `voided_at` | DateTimeField | When voided (null if not) |
| `voided_by` | ForeignKey → User | Who voided (null if not) |
| `void_reason` | TextField | Required when voiding |

**Invoice numbering:** `INV-YYYYMM-XXXX` — resets monthly, scoped per clinic.

---

## InvoiceLine (`apps/billing/models.py`)

A denormalized copy of each VisitService at the time of invoicing.

| Field | Type | Description |
|-------|------|-------------|
| `invoice` | ForeignKey → Invoice | Parent invoice (CASCADE) |
| `visit_service` | ForeignKey → VisitService | Source line item (nullable, PROTECT) |
| `name` | CharField(200) | Service name (denormalized — survives renames) |
| `quantity` | IntegerField | Copy from VisitService |
| `unit_price` | IntegerField | Copy from VisitService (with override applied) |
| `total` | IntegerField | `quantity * unit_price` |

**Why denormalize?** If a service is renamed or soft-deleted after invoicing, the invoice line items remain readable with the original name and price.

---

## Payment (`apps/billing/models.py`)

A payment against an invoice.

| Field | Type | Description |
|-------|------|-------------|
| `payment_id` | CharField(20) | Auto-generated: `PAY-YYYYMMDD-XXXX` |
| `invoice` | ForeignKey → Invoice | Which invoice (PROTECT) |
| `clinic` | ForeignKey → Clinic | Scoping |
| `amount` | IntegerField | Payment amount in XAF |
| `payment_method` | CharField(20) | `cash`, `mtn_momo`, `orange_money`, `bank_transfer` |
| `reference_number` | CharField(100) | Transaction reference (required for bank_transfer) |
| `payment_date` | DateTimeField | When the payment was made |
| `notes` | TextField | Optional notes |
| `status` | CharField(20) | `confirmed` or `voided` |
| `received_by` | ForeignKey → User | Staff who recorded the payment |
| `voided_at` | DateTimeField | When voided (null if not) |
| `voided_by` | ForeignKey → User | Who voided (null if not) |
| `void_reason` | TextField | Required when voiding |

**Financial records are never deleted** — only voided. This preserves the full audit trail.

---

## Entity Relationship Summary

```
Clinic ──< User
Clinic ──< Service (soft delete)
Clinic ──< Patient (soft delete)
Clinic ──< Visit
Clinic ──< Invoice
Clinic ──< Payment

Patient ──< Visit
Visit ──< VisitService >── Service
Visit ──1 Invoice
Invoice ──< InvoiceLine >── VisitService
Invoice ──< Payment
```

`──<` = one-to-many, `──1` = one-to-one, `>──` = many-to-one reference
