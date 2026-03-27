# ClinicOps Backend Architecture

> Django 4.2 + Django REST Framework + PostgreSQL
> Multi-tenant SaaS — each clinic is an isolated data silo

---

## Project Structure

```
clinicops_server/
├── config/                    # Project configuration
│   ├── settings/
│   │   ├── base.py            # Shared settings (all environments)
│   │   ├── development.py     # Dev overrides (DEBUG=True, SQLite fallback)
│   │   ├── production.py      # Prod overrides (HTTPS, secure cookies)
│   │   └── test.py            # Test overrides
│   ├── urls.py                # Root URL configuration
│   ├── wsgi.py / asgi.py      # WSGI/ASGI entry points
│   └── celery.py              # Celery task queue
│
├── apps/
│   ├── core/                  # Shared base classes and utilities
│   │   ├── models.py          # TimestampedModel, SoftDeleteModel
│   │   ├── permissions.py     # Role-based permission classes
│   │   ├── mixins.py          # ClinicScopedMixin
│   │   ├── id_generators.py   # Human-readable ID generation
│   │   ├── pagination.py      # StandardPagination (20/page, max 100)
│   │   ├── throttling.py      # LoginThrottle, RegisterThrottle, SMSThrottle
│   │   ├── exceptions.py      # Custom exception handler
│   │   └── utils.py           # normalize_phone, generate_temp_password
│   │
│   ├── accounts/              # Authentication & user management
│   │   ├── models.py          # User, SMSLog
│   │   ├── managers.py        # UserManager (phone-based)
│   │   ├── authentication.py  # CookieJWTAuthentication
│   │   ├── schema.py          # OpenAPI auth extension
│   │   ├── serializers.py     # Auth serializers
│   │   ├── views.py           # Login, Register, Logout, MeView, etc.
│   │   ├── staff_serializers.py # Staff CRUD serializers
│   │   ├── staff_views.py     # Staff CRUD views
│   │   ├── urls.py            # /auth/ routes
│   │   ├── staff_urls.py      # /staff/ routes
│   │   ├── services/          # Token utilities
│   │   ├── signals.py         # Post-save signals
│   │   └── task.py            # SMS queue (Africa's Talking)
│   │
│   ├── clinics/               # Clinic & service management
│   │   ├── models.py          # Clinic, Service
│   │   ├── serializers.py     # ClinicSerializer, ServiceSerializer
│   │   ├── views.py           # ClinicDetailView, Service CRUD
│   │   ├── filters.py         # ServiceSearchFilter
│   │   ├── urls.py            # /clinic/ routes (includes services)
│   │   └── admin.py
│   │
│   ├── patients/              # Patient records
│   │   ├── models.py          # Patient (SoftDeleteModel)
│   │   ├── serializers.py     # PatientList/DetailSerializer
│   │   ├── views.py           # Patient CRUD
│   │   ├── filters.py         # PatientSearchFilter
│   │   ├── urls.py            # /patients/ routes
│   │   └── admin.py
│   │
│   ├── visits/                # Visit & service tracking
│   │   ├── models.py          # Visit, VisitService
│   │   ├── serializers.py     # Visit and VisitService serializers
│   │   ├── views.py           # Visit CRUD + service add/remove + cancel
│   │   ├── filters.py         # VisitFilter (search, status, date, type)
│   │   ├── urls.py            # /visits/ routes
│   │   └── admin.py
│   │
│   ├── billing/               # Invoices & payments
│   │   ├── models.py          # Invoice, InvoiceLine, Payment
│   │   ├── serializers.py     # Invoice and Payment serializers
│   │   ├── views.py           # Invoice/Payment CRUD + void
│   │   ├── services.py        # Business logic (atomic transactions)
│   │   ├── filters.py         # InvoiceFilter, PaymentFilter
│   │   ├── invoice_urls.py    # /invoices/ routes
│   │   ├── payment_urls.py    # /payments/ routes
│   │   └── admin.py
│   │
│   ├── reports/               # (stub) Reports & analytics
│   ├── audit/                 # (stub) Audit logging
│   └── ...
│
├── templates/
│   └── drf_spectacular/
│       └── swagger_ui.html    # Custom Swagger UI with branded header
│
├── docs/                      # This documentation
├── manage.py
├── Dockerfile
├── compose.dev.yml
├── compose.prod.yml
└── requirements/
```

---

## URL Routing

All API routes are under `/api/v1/`:

| Prefix | App | Description |
|--------|-----|-------------|
| `/api/v1/auth/` | accounts | Login, register, password reset, profile |
| `/api/v1/clinic/` | clinics | Clinic settings + nested services |
| `/api/v1/staff/` | accounts | Staff CRUD |
| `/api/v1/patients/` | patients | Patient CRUD |
| `/api/v1/visits/` | visits | Visit CRUD + service management |
| `/api/v1/invoices/` | billing | Invoice generation + void |
| `/api/v1/payments/` | billing | Payment recording + void |
| `/health/` | config | Health check (`{"status": "ok"}`) |
| `/` | config | Swagger UI |
| `/api/schema/` | config | OpenAPI JSON schema |
| `/api/schema/redoc/` | config | ReDoc documentation |

---

## Authentication Flow

```
Client                              Server
  │                                    │
  │  POST /auth/login/                 │
  │  {phone, password}                 │
  │ ──────────────────────────────────>│
  │                                    │ validate credentials
  │                                    │ generate JWT access + refresh
  │  {access_token, user}              │
  │  Set-Cookie: refresh=<token>       │
  │ <──────────────────────────────────│
  │                                    │
  │  GET /patients/                    │
  │  Authorization: Bearer <access>    │
  │ ──────────────────────────────────>│
  │                                    │ CookieJWTAuthentication validates
  │  {count, results: [...]}           │
  │ <──────────────────────────────────│
  │                                    │
  │  (access token expired)            │
  │  POST /auth/refresh/               │
  │  Cookie: refresh=<token>           │
  │ ──────────────────────────────────>│
  │                                    │ validate refresh token
  │  {access_token: <new>}             │ rotate refresh token
  │  Set-Cookie: refresh=<new>         │
  │ <──────────────────────────────────│
```

**Key decisions:**
- Access token (15 min) is stored in memory (JS variable) — never in cookies or localStorage
- Refresh token (7–30 days) is stored in an HTTP-only, Secure, SameSite=Lax cookie
- Refresh tokens are rotated on each use and blacklisted after rotation
- The `CookieJWTAuthentication` class only reads the `Authorization` header, not the cookie

---

## Data Flow: Visit → Invoice → Payment

```
1. Create patient          POST /patients/
2. Create visit            POST /visits/           → status: open
3. Add services            POST /visits/{id}/services/
4. Generate invoice        POST /invoices/         → visit: invoiced
5. Record payment          POST /payments/         → invoice: partial/paid
6. (If fully paid)                                 → visit: completed
```

Each step is an independent API call. The frontend drives the flow.

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | Django 4.2 + DRF | REST API |
| Database | PostgreSQL | Primary datastore |
| Cache | Redis | Caching, Celery broker |
| Task Queue | Celery + Redis | Async SMS sending |
| Auth | SimpleJWT | JWT access + refresh tokens |
| SMS | Africa's Talking | Password reset codes, staff invitations |
| API Docs | drf-spectacular | OpenAPI 3.0 + Swagger UI + ReDoc |
| Deployment | Docker + Railway/Render | Containerized deployment |

---

## Design Patterns Used

### 1. Mixin-based multi-tenancy

`ClinicScopedMixin` is applied to every view that touches clinic-scoped data. It handles both read filtering and write injection in one place, so individual views don't need to repeat the clinic logic.

### 2. Service layer for business logic

Complex operations (invoice creation, payment recording, voiding) live in `apps/billing/services.py`, not in views. This keeps views thin, makes logic testable in isolation, and ensures atomic transactions.

### 3. Soft delete for reversible operations

Patients and services use `SoftDeleteModel` — they can be "deleted" from the user's perspective while preserving referential integrity with existing visits and invoices.

### 4. Status-based lifecycle for financial records

Visits, invoices, and payments use status fields instead of deletion. This preserves the complete audit trail required for financial compliance.

### 5. Price snapshots

When a service is added to a visit, the price is copied to `VisitService.unit_price`. When an invoice is generated, the service name is copied to `InvoiceLine.name`. This denormalization ensures historical accuracy.

### 6. Custom filter backends

Each app defines its own filter class (e.g., `VisitFilter`, `PatientSearchFilter`) that inherits from DRF's `BaseFilterBackend`. This keeps filtering logic in one place per model and integrates with drf-spectacular's schema generation via `get_schema_operation_parameters()`.
