# ClinicOps API Endpoints

> Base URL: `/api/v1/`
> Authentication: JWT Bearer token via `Authorization: Bearer <token>` header
> All data is scoped to the authenticated user's clinic (multi-tenant)

---

## Authentication

| Method | Endpoint | Summary | Auth |
|--------|----------|---------|------|
| POST | `/auth/login/` | Authenticate with phone + password | No |
| POST | `/auth/register/` | Register a new clinic and owner | No |
| POST | `/auth/logout/` | Blacklist the refresh token | Yes |
| POST | `/auth/refresh/` | Get a new access token from the refresh cookie | No |
| POST | `/auth/password-reset/` | Request a 6-digit SMS reset code | No |
| POST | `/auth/password-reset/confirm/` | Confirm reset with code + new password | No |
| POST | `/auth/change-password/` | Change password (authenticated) | Yes |

### POST `/auth/login/`

Authenticates a user by phone and password. Returns a JWT access token in the response body and sets an HTTP-only refresh cookie.

**Request:**
```json
{
  "phone": "+237699123456",
  "password": "mypassword",
  "remember_me": false
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "user": {
    "id": "uuid",
    "firstName": "Jean",
    "lastName": "Mbarga",
    "phone": "+237699123456",
    "email": "jean@example.com",
    "role": "owner",
    "clinic": { "id": "uuid", "name": "Clinique Espoir" },
    "mustChangePassword": false
  }
}
```

**Error responses:**
- `401` — `invalid_credentials`: wrong phone or password
- `401` — `account_locked`: too many failed attempts (5), locked for 15 min
- `403` — `account_disabled`: user was deactivated by admin

### POST `/auth/register/`

Creates a new clinic and its owner account in one request.

**Request:**
```json
{
  "clinic": {
    "name": "Clinique Espoir",
    "address": "Yaounde, Bastos",
    "phone": "+237233424567",
    "email": "contact@clinique-espoir.cm"
  },
  "admin": {
    "firstName": "Jean",
    "lastName": "Mbarga",
    "phone": "+237699123456",
    "email": "jean@example.com",
    "password": "SecurePass123"
  }
}
```

### POST `/auth/refresh/`

Reads the refresh token from the HTTP-only cookie and returns a new access token. No request body needed.

### POST `/auth/password-reset/`

Sends a 6-digit SMS code to the given phone number (if it exists). The code expires after 15 minutes.

**Request:**
```json
{ "phone": "+237699123456" }
```

### POST `/auth/password-reset/confirm/`

Verifies the SMS code and sets a new password.

**Request:**
```json
{
  "phone": "+237699123456",
  "code": "482917",
  "password": "NewSecurePass123"
}
```

### POST `/auth/change-password/`

Changes the password for the currently authenticated user.

**Request:**
```json
{
  "currentPassword": "OldPass123",
  "newPassword": "NewPass456"
}
```

---

## Settings (User Profile)

| Method | Endpoint | Summary | Permission |
|--------|----------|---------|------------|
| GET | `/auth/me/` | Get current user profile | Any authenticated |
| PATCH | `/auth/me/` | Update profile (firstName, lastName, email) | Any authenticated |

### GET `/auth/me/`

Returns the current user's profile including clinic info.

### PATCH `/auth/me/`

**Request:**
```json
{
  "firstName": "Jean-Pierre",
  "lastName": "Mbarga",
  "email": "jp@example.com"
}
```

All fields are optional (partial update). Phone and role cannot be changed here.

---

## Clinics (Clinic Settings)

| Method | Endpoint | Summary | Permission |
|--------|----------|---------|------------|
| GET | `/clinic/` | Get clinic details | Any clinic member |
| PATCH | `/clinic/` | Update clinic settings | Owner, Admin |

### GET `/clinic/`

Returns the full clinic profile: contact info, invoice settings, payment method settings.

**Response (200):**
```json
{
  "id": "uuid",
  "name": "Clinique Espoir",
  "address": "Yaounde, Bastos",
  "city": "Yaounde",
  "region": "Centre",
  "phonePrimary": "+237233424567",
  "phoneSecondary": "",
  "email": "contact@clinique-espoir.cm",
  "registrationNumber": "RC/DLA/2020/B/1234",
  "invoicePrefix": "INV-",
  "invoiceNumbering": "continuous",
  "invoiceFooter": "Merci pour votre confiance",
  "cashThreshold": 500,
  "mtnMomoNumber": "+237677123456",
  "orangeMoneyNumber": "+237699987654",
  "bankName": "Afriland First Bank",
  "bankAccount": "10005 00001 12345678901 42",
  "isActive": true,
  "createdAt": "2025-01-15T10:00:00Z",
  "updatedAt": "2025-03-15T14:30:00Z"
}
```

### PATCH `/clinic/`

Update any subset of clinic fields. Only `owner` and `admin` roles are allowed.

**Request example:**
```json
{
  "name": "Clinique Espoir Plus",
  "mtnMomoNumber": "+237677999888",
  "cashThreshold": 1000
}
```

---

## Services

| Method | Endpoint | Summary | Permission |
|--------|----------|---------|------------|
| GET | `/clinic/services/` | List all services | Any clinic member |
| POST | `/clinic/services/` | Create a service | Owner, Admin |
| GET | `/clinic/services/{id}/` | Get service details | Any clinic member |
| PATCH | `/clinic/services/{id}/` | Update a service | Owner, Admin |
| DELETE | `/clinic/services/{id}/` | Soft-delete a service | Owner, Admin |

### GET `/clinic/services/`

Lists services for the current clinic. Supports filtering.

**Query parameters:**
- `search` — search by name or code
- `category` — filter by `consultation`, `laboratory`, `pharmacy`, or `care`
- `isActive` — filter by `true` or `false`

### POST `/clinic/services/`

**Request:**
```json
{
  "name": "Consultation generale",
  "code": "CONS-GEN",
  "category": "consultation",
  "price": 5000,
  "description": "Consultation medicale de base"
}
```

**Validation rules:**
- `code` must be unique within the clinic
- `name` must be unique within the clinic (case-insensitive)
- `price` must be >= 0 (integer, XAF)

### DELETE `/clinic/services/{id}/`

Performs a **soft delete** — the service is marked as deleted but remains in the database. Existing visit services referencing it are preserved.

---

## Patients

| Method | Endpoint | Summary | Permission |
|--------|----------|---------|------------|
| GET | `/patients/` | List patients | Any clinic member |
| POST | `/patients/` | Create a patient | Owner, Admin, Receptionist |
| GET | `/patients/{id}/` | Get patient details | Any clinic member |
| PATCH | `/patients/{id}/` | Update a patient | Owner, Admin, Receptionist |
| DELETE | `/patients/{id}/` | Soft-delete a patient | Owner, Admin, Receptionist |

### GET `/patients/`

Paginated list (20 per page, max 100). All queries are scoped to the user's clinic.

**Query parameters:**
- `search` — search by first name, last name, phone, or patient ID
- `gender` — filter by `M`, `F`, or `O`
- `page` — page number
- `page_size` — items per page (max 100)

**Response item:**
```json
{
  "id": "uuid",
  "patientId": "PAT-20250315-0001",
  "firstName": "Marie",
  "lastName": "Atangana",
  "phone": "+237699123456",
  "dateOfBirth": "1985-06-15",
  "gender": "F",
  "lastVisit": "2025-03-15",
  "outstandingBalance": 50000
}
```

### POST `/patients/`

**Request:**
```json
{
  "firstName": "Marie",
  "lastName": "Atangana",
  "phone": "+237699123456",
  "dateOfBirth": "1985-06-15",
  "gender": "F",
  "address": "Yaounde, Bastos",
  "emergencyContactName": "Jean Atangana",
  "emergencyContactPhone": "+237677111222"
}
```

**Duplicate phone detection:** If a patient with the same phone exists in the clinic, the API returns:
```json
{
  "error": "duplicate_phone",
  "message": "Un patient avec ce numero existe deja",
  "existing_patient": {
    "id": "uuid",
    "name": "Marie A.",
    "patient_id": "PAT-20250315-0001"
  }
}
```

To force creation despite a duplicate phone, include `"forceCreate": true` in the request.

---

## Visits

| Method | Endpoint | Summary | Permission |
|--------|----------|---------|------------|
| GET | `/visits/` | List visits | Any clinic member |
| POST | `/visits/` | Create a visit | Owner, Admin, Receptionist |
| GET | `/visits/{id}/` | Get visit details | Any clinic member |
| POST | `/visits/{visit_id}/services/` | Add a service to a visit | Any clinic member |
| DELETE | `/visits/{visit_id}/services/{service_id}/` | Remove a service from a visit | Owner, Admin, Receptionist |
| POST | `/visits/{visit_id}/cancel/` | Cancel a visit | Owner, Admin |

### Visit Status Workflow

```
open  ──>  invoiced  ──>  completed
  │
  └──>  cancelled
```

- `open` — services can be added/removed
- `invoiced` — invoice generated, services locked, awaiting payment
- `completed` — invoice fully paid
- `cancelled` — visit cancelled with a reason

### GET `/visits/`

**Query parameters:**
- `search` — search by visit ID, patient name, or patient ID
- `status` — `open`, `invoiced`, `completed`, or `cancelled`
- `type` — `walkin`, `appointment`, `followup`, or `emergency`
- `dateFrom` / `dateTo` — date range filter (YYYY-MM-DD)
- `patientId` — filter by patient UUID

### POST `/visits/`

**Request:**
```json
{
  "patientId": "uuid-of-patient",
  "visitType": "walkin",
  "notes": "Patient presents with fever",
  "services": [
    { "serviceId": "uuid-of-service", "quantity": 1 },
    { "serviceId": "uuid-of-service-2", "quantity": 2, "priceOverride": 3000, "overrideReason": "Tarif reduit famille" }
  ]
}
```

- `services` is optional — you can create an empty visit and add services later
- `priceOverride` requires `owner` or `admin` role and a mandatory `overrideReason`

### POST `/visits/{visit_id}/services/`

Add a service to an **open** visit.

**Request:**
```json
{
  "serviceId": "uuid-of-service",
  "quantity": 1,
  "priceOverride": null,
  "overrideReason": ""
}
```

**Business rules:**
- Visit must be in `open` status
- Service must be active and belong to the same clinic
- Duplicate services on the same visit are rejected
- `unit_price` is snapshotted from the current service price

### DELETE `/visits/{visit_id}/services/{service_id}/`

Remove a service from an **open** visit.

**Receptionist restrictions:**
- Can only remove services they personally added
- Can only remove on the same day the service was added

### POST `/visits/{visit_id}/cancel/`

**Request:**
```json
{ "reason": "Patient did not show up" }
```

The reason is mandatory. Cannot cancel `completed` or already `cancelled` visits.

---

## Invoices

| Method | Endpoint | Summary | Permission |
|--------|----------|---------|------------|
| GET | `/invoices/` | List invoices | Any clinic member |
| POST | `/invoices/` | Create invoice from visit | Owner, Admin, Receptionist |
| GET | `/invoices/{id}/` | Get invoice details | Any clinic member |
| POST | `/invoices/{invoice_id}/void/` | Void an invoice | Owner, Admin |

### Invoice Status Workflow

```
pending  ──>  partial  ──>  paid
    │
    └──>  cancelled (voided)
```

### POST `/invoices/`

Generate an invoice from a visit's services.

**Request:**
```json
{
  "visitId": "uuid-of-visit",
  "discountPercent": 10,
  "discountAmount": 0,
  "discountReason": "Fidelite client"
}
```

**Business rules:**
- Visit must be in `open` status with at least one service
- Visit transitions to `invoiced` after invoice creation
- Discount requires `owner` or `admin` role and a reason
- `discountPercent` takes priority over `discountAmount`
- All amounts are in XAF (integer, no decimals)

**Response includes:** invoice number (`INV-YYYYMM-XXXX`), line items, totals, and empty payments array.

### GET `/invoices/{id}/`

Returns the full invoice with line items, payments, patient info, and clinic info.

**Response:**
```json
{
  "id": "uuid",
  "invoiceNumber": "INV-202503-0001",
  "date": "2025-03-15T14:30:00Z",
  "patient": { "id": "uuid", "name": "Marie Atangana", "phone": "+237699123456" },
  "items": [
    { "id": "uuid", "name": "Consultation generale", "quantity": 1, "unitPrice": 5000, "total": 5000 },
    { "id": "uuid", "name": "Test paludisme", "quantity": 1, "unitPrice": 2500, "total": 2500 }
  ],
  "subtotal": 7500,
  "discountPercent": 0,
  "discountAmount": 0,
  "discountReason": "",
  "total": 7500,
  "paidAmount": 5000,
  "balance": 2500,
  "status": "partial",
  "payments": [
    { "id": "uuid", "date": "2025-03-15T15:00:00Z", "method": "cash", "amount": 5000, "reference": "" }
  ],
  "clinic": { "name": "Clinique Espoir", "address": "Yaounde, Bastos", "phone": "+237233424567" },
  "createdBy": "Jean Mbarga",
  "voidedAt": null,
  "voidedBy": null,
  "voidReason": ""
}
```

### POST `/invoices/{invoice_id}/void/`

**Request:**
```json
{ "reason": "Erreur de facturation" }
```

**Rules:** Can only void an invoice with no confirmed payments. Void first reverses the visit status back to `open`.

---

## Payments

| Method | Endpoint | Summary | Permission |
|--------|----------|---------|------------|
| GET | `/payments/` | List confirmed payments | Any clinic member |
| POST | `/payments/` | Record a payment | Owner, Admin, Receptionist |
| POST | `/payments/{payment_id}/void/` | Void a payment | Owner, Admin |

### POST `/payments/`

**Request:**
```json
{
  "invoiceId": "uuid-of-invoice",
  "amount": 5000,
  "method": "cash",
  "referenceNumber": "",
  "notes": ""
}
```

**Payment methods:**
- `cash` — no reference required
- `mtn_momo` — reference recommended
- `orange_money` — reference recommended
- `bank_transfer` — reference **required**

**Business rules:**
- `amount` must be > 0 and <= invoice balance
- Cannot pay a `paid` or `cancelled` invoice
- When balance reaches 0, invoice status becomes `paid` and visit becomes `completed`
- Partial payments are tracked — invoice status becomes `partial`

### POST `/payments/{payment_id}/void/`

**Request:**
```json
{ "reason": "Paiement duplique par erreur" }
```

Voiding a payment recalculates the invoice balance and may revert the invoice status from `paid` to `partial` or `pending`.

---

## Staff

| Method | Endpoint | Summary | Permission |
|--------|----------|---------|------------|
| GET | `/staff/` | List staff members | Owner, Admin |
| POST | `/staff/` | Create a staff member | Owner, Admin |
| GET | `/staff/{staff_id}/` | Get staff details | Owner, Admin |
| PATCH | `/staff/{staff_id}/` | Update a staff member | Owner, Admin |
| POST | `/staff/{staff_id}/deactivate/` | Deactivate a staff member | Owner, Admin |
| POST | `/staff/{staff_id}/reactivate/` | Reactivate a staff member | Owner, Admin |

### POST `/staff/`

Creates a new staff account with a temporary password sent via SMS.

**Request:**
```json
{
  "firstName": "Paul",
  "lastName": "Biya",
  "phone": "+237677555444",
  "email": "paul@example.com",
  "role": "receptionist"
}
```

**Role hierarchy:**
- `owner` can create `admin`, `receptionist`, `nurse`
- `admin` can create `receptionist`, `nurse` only
- Only `owner` can assign the `admin` role

The created user must change their password on first login (`mustChangePassword: true`).

### POST `/staff/{staff_id}/deactivate/`

Deactivates the account — the user can no longer log in. No request body needed.

**Constraints:**
- Cannot deactivate yourself
- Cannot deactivate the owner
- Cannot deactivate a user of equal or higher rank

### POST `/staff/{staff_id}/reactivate/`

Re-enables a previously deactivated account. No request body needed.

---

## Pagination

All list endpoints use the same pagination format:

```json
{
  "count": 42,
  "next": "http://api.example.com/patients/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

Default page size: **20**, max: **100**. Use `?page_size=50` to adjust.

---

## Error Format

All errors follow a consistent shape:

```json
{
  "error": "error_code",
  "message": "Human-readable message in French"
}
```

Some errors include additional fields (e.g., `lockedUntil`, `existing_patient`).

---

## Interactive Documentation

- **Swagger UI:** `http://localhost:8000/` or `http://localhost:8000/api/docs/`
- **ReDoc:** `http://localhost:8000/api/schema/redoc/`
- **OpenAPI schema:** `http://localhost:8000/api/schema/`
