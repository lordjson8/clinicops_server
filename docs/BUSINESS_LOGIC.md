# ClinicOps Business Logic

> This document explains the core business workflows, why each decision was made,
> and how the pieces fit together.

---

## 1. ID Generation (`apps/core/id_generators.py`)

Every major entity gets a human-readable ID in addition to its UUID primary key.

| Entity | Format | Scope | Reset |
|--------|--------|-------|-------|
| Patient | `PAT-YYYYMMDD-XXXX` | Per clinic, per day | Daily |
| Visit | `VIS-YYYYMMDD-XXXX` | Per clinic, per day | Daily |
| Invoice | `INV-YYYYMM-XXXX` | Per clinic, per month | Monthly |
| Payment | `PAY-YYYYMMDD-XXXX` | Per clinic, per day | Daily |

### How it works

Each generator follows the same pattern:

1. Build the prefix from today's date (e.g., `PAT-20250315-`)
2. Query the database for the last ID with that prefix, scoped to the clinic
3. Parse the sequence number from the last ID and increment it
4. If no previous ID exists, start at `0001`

```python
last = (
    Patient.all_objects                               # include soft-deleted records
    .filter(clinic_id=clinic_id, patient_id__startswith=prefix)
    .order_by('-patient_id')                          # highest sequence first
    .values_list('patient_id', flat=True)
    .first()                                          # get just the ID string
)
seq = int(last.split('-')[-1]) + 1 if last else 1
return f'{prefix}{seq:04d}'
```

### Why `all_objects`?

Patients use soft delete. If we only counted non-deleted records, a deleted patient's ID could be reused, which would be confusing for medical records. Using `all_objects` ensures the sequence always moves forward.

### Why `order_by('-patient_id').first()` instead of `count()`?

`count()` breaks if records are deleted (even hard delete). Parsing the last sequential ID is always correct — if the last ID is `PAT-20250315-0007`, the next is `0008`, regardless of how many records were deleted in between.

### Invoices use monthly reset

Invoices are numbered `INV-YYYYMM-XXXX` (note: no day). The sequence resets monthly rather than daily because invoices are legal financial documents and monthly numbering is the common standard in Cameroon.

---

## 2. Visit Lifecycle

A visit represents a single patient encounter at the clinic.

### Status flow

```
                      ┌─────────────┐
                      │    open     │  ← created here
                      └──────┬──────┘
                             │
                 ┌───────────┼───────────┐
                 │                       │
          generate invoice          cancel visit
                 │                       │
          ┌──────▼──────┐        ┌───────▼───────┐
          │  invoiced   │        │  cancelled    │
          └──────┬──────┘        └───────────────┘
                 │
           full payment
                 │
          ┌──────▼──────┐
          │  completed  │
          └─────────────┘
```

### What can happen in each status

**open:**
- Services can be added by any clinic member
- Services can be removed (with restrictions for receptionists)
- Invoice can be generated → transitions to `invoiced`
- Visit can be cancelled → transitions to `cancelled`

**invoiced:**
- Services are locked (cannot add or remove)
- Payments can be recorded against the invoice
- When fully paid → transitions to `completed`
- Invoice can be voided → transitions back to `open`

**completed:**
- Read-only. No further actions.
- If a payment is voided, invoice reverts to `partial` and visit reverts to `invoiced`

**cancelled:**
- Read-only. Stores who cancelled, when, and why.

### Price snapshot

When a service is added to a visit, the current price is copied to `VisitService.unit_price`. This snapshot ensures that future price changes to the service catalog do not retroactively affect existing visits or invoices.

```python
vs = VisitService.objects.create(
    visit=visit,
    service=service,
    unit_price=service.price,     # snapshot taken here
    ...
)
```

### Price override

Owners and admins can override the price for a specific visit service. The override reason is mandatory — this creates an audit trail for any price adjustments.

```python
line_total = (price_override if price_override is not None else unit_price) * quantity
```

---

## 3. Invoice Generation (`apps/billing/services.py`)

Invoices are created from visits, not manually.

### `create_invoice_from_visit(visit, created_by, discount_percent, discount_amount, discount_reason)`

This is the core billing function. It runs inside `@transaction.atomic` — if anything fails, the entire operation is rolled back.

**Step by step:**

1. **Validate** — visit must be `open` and have at least one service
2. **Calculate subtotal** — sum of all `VisitService.line_total` values
3. **Apply discount** — percent-based or flat amount, capped at subtotal
4. **Generate invoice number** — `INV-YYYYMM-XXXX`
5. **Create Invoice record** — with all calculated totals, balance = total
6. **Create InvoiceLine records** — one per VisitService, with denormalized name and price
7. **Update visit status** — `open` → `invoiced`

### Why denormalize invoice lines?

Each `InvoiceLine` copies the service name and price. If the service is later renamed from "Consultation" to "Consultation Generale", old invoices still show the original name. This is critical for financial records — an invoice must reflect exactly what was billed at the time.

### Discount rules

- Only `owner` and `admin` can apply discounts
- A reason is required (e.g., "Fidelite client", "Tarif famille")
- `discount_percent` takes priority over `discount_amount`
- The discount cannot exceed the subtotal

---

## 4. Payment Recording

### `record_payment(invoice, amount, payment_method, received_by, reference_number, notes)`

Also wrapped in `@transaction.atomic`.

**Step by step:**

1. **Validate invoice** — must be `pending` or `partial` (not `paid` or `cancelled`)
2. **Validate amount** — must be positive and not exceed the remaining balance
3. **Validate reference** — required for `bank_transfer`
4. **Generate payment ID** — `PAY-YYYYMMDD-XXXX`
5. **Create Payment record**
6. **Update invoice** — increment `paid_amount`, recalculate `balance`
7. **Auto-update invoice status:**
   - `balance == 0` → `paid` + mark visit as `completed`
   - `paid_amount > 0` → `partial`

### Partial payments

Multiple payments per invoice are supported. Each payment is independent — the invoice tracks the cumulative `paid_amount` and `balance`.

Example: Invoice total = 10,000 XAF
- Payment 1: 5,000 XAF cash → status = `partial`, balance = 5,000
- Payment 2: 5,000 XAF MoMo → status = `paid`, balance = 0, visit = `completed`

---

## 5. Void Operations

Financial records are **never deleted**. Corrections are made by voiding and (optionally) re-creating.

### `void_invoice(invoice, voided_by, reason)`

- Can only void if there are **no confirmed payments** (void payments first)
- Sets invoice status to `cancelled`
- Records who voided and why
- **Reverts the visit to `open`** so a new invoice can be generated

### `void_payment(payment, voided_by, reason)`

- Sets payment status to `voided`
- **Recalculates the invoice** from remaining confirmed payments
- May revert invoice status from `paid` → `partial` or `pending`
- If the visit was `completed`, reverts to `invoiced`

### Why void instead of delete?

Voiding preserves the full audit trail. An auditor can see that a payment was made, then voided, and why. Deletion would leave gaps in the financial record.

---

## 6. Staff Lifecycle

### Account creation

1. Owner/admin creates a staff account with phone, name, and role
2. System generates a random temporary password (10 chars, mixed case + digits)
3. Password is sent to the staff member via SMS (Africa's Talking integration)
4. Account is created with `must_change_password = True`

### First login

1. Staff logs in with phone + temp password
2. API response includes `mustChangePassword: true`
3. Frontend forces password change before allowing access
4. After change: `must_change_password = False`, `password_changed_at = now()`

### Deactivation

1. Admin/owner clicks deactivate
2. `is_active = False` — user can no longer log in
3. Historical references (created_by, received_by, etc.) are preserved
4. Can be reactivated later

---

## 7. Multi-Tenant Data Isolation

Every data query is scoped to the current user's clinic. This is enforced at two levels:

### Level 1: ClinicScopedMixin (view level)

```python
class ClinicScopedMixin:
    def get_queryset(self):
        return super().get_queryset().filter(clinic=self.request.user.clinic)
```

Even if you know another clinic's patient UUID, querying `/patients/{uuid}/` returns 404 because the queryset is filtered.

### Level 2: perform_create (write level)

```python
def perform_create(self, serializer):
    serializer.save(clinic=self.request.user.clinic)
```

The clinic is always set from the JWT token, never from the request body. A user cannot create records in another clinic.

### Why not just filter by clinic in the serializer?

The mixin approach is more secure — it's applied at the queryset level before any serialization happens. Even if a serializer bug leaked data, the queryset would still block cross-clinic access.

---

## 8. Soft Delete vs. Status-Based Records

| Entity | Deletion Strategy | Why |
|--------|------------------|-----|
| Patient | Soft delete | Medical records must be preservable. Undo is possible. |
| Service | Soft delete | Existing invoices reference services. Can be restored. |
| Visit | Status (`cancelled`) | Part of the billing chain. Cancellation reason is recorded. |
| Invoice | Status (`cancelled`/void) | Legal financial document. Never truly deleted. |
| Payment | Status (`voided`) | Financial record. Void + reason preserves audit trail. |

---

## 9. Currency and Localization

- **Currency:** XAF (Central African Franc)
- All monetary values are **integers** (no decimals — XAF has no subunit)
- **Phone format:** `+237XXXXXXXXX` (Cameroon)
- **Locale:** French (fr-FR) for formatting on the frontend
- **Names:** Cameroonian names in mock/test data
- **Payment methods:** Cash, MTN MoMo, Orange Money, Bank Transfer
