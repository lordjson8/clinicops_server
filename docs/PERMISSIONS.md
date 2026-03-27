# ClinicOps Role-Based Permissions

> Every user belongs to a clinic and has one of four roles.
> All data is scoped to the user's clinic — you can never see another clinic's data.

---

## Roles

| Role | Level | French | Description |
|------|-------|--------|-------------|
| `owner` | 4 | Proprietaire | Clinic owner. Full system access. Only one per clinic. |
| `admin` | 3 | Administrateur | Day-to-day manager. Cannot modify other admins or the owner. |
| `receptionist` | 2 | Receptionniste | Patient intake, visit creation, billing, payments. |
| `nurse` | 1 | Infirmier(e) | View patients, add services to visits. Read-only on billing. |

---

## Permission Classes (`apps/core/permissions.py`)

These are DRF permission classes applied to views. Each one inherits from `IsAnyClinicRole`, which checks that the user is authenticated and belongs to a clinic.

### IsAnyClinicRole

```python
class IsAnyClinicRole(BasePermission):
```

The base check. Verifies:
1. `request.user` exists and is authenticated
2. The user has a `clinic_id` (is not null)

Used on: all read endpoints (patient list, visit detail, etc.)

### IsOwner

```python
class IsOwner(IsAnyClinicRole):
```

Only allows users with `role == 'owner'`. Used for operations that only the clinic owner can do (e.g., assigning admin role).

### IsOwnerOrAdmin

```python
class IsOwnerOrAdmin(IsAnyClinicRole):
```

Allows `owner` or `admin`. Used on:
- Clinic settings (PATCH)
- Service create/update/delete
- Staff management
- Invoice void
- Payment void
- Visit cancel

### IsOwnerAdminOrReceptionist

```python
class IsOwnerAdminOrReceptionist(IsAnyClinicRole):
```

Allows `owner`, `admin`, or `receptionist`. Used on:
- Patient create/update/delete
- Visit service removal

### ReadAnyWriteRestricted

```python
class ReadAnyWriteRestricted(IsAnyClinicRole):
```

The most commonly used permission. Split behavior:
- **GET/HEAD/OPTIONS** — any clinic member can read
- **POST/PUT/PATCH/DELETE** — only roles listed in `write_roles`

The `write_roles` tuple defaults to `('owner', 'admin')` but can be overridden per view:

```python
class PatientListCreateView(ListCreateAPIView):
    permission_classes = [ReadAnyWriteRestricted]
    write_roles = ('owner', 'admin', 'receptionist')  # receptionist can also create
```

---

## Permission Matrix

### Clinic & Services

| Action | Owner | Admin | Receptionist | Nurse |
|--------|:-----:|:-----:|:------------:|:-----:|
| View clinic details | Y | Y | Y | Y |
| Edit clinic settings | Y | Y | - | - |
| List services | Y | Y | Y | Y |
| Create/edit/delete service | Y | Y | - | - |

### Patients

| Action | Owner | Admin | Receptionist | Nurse |
|--------|:-----:|:-----:|:------------:|:-----:|
| List patients | Y | Y | Y | Y |
| View patient details | Y | Y | Y | Y |
| Create patient | Y | Y | Y | - |
| Update patient | Y | Y | Y | - |
| Soft-delete patient | Y | Y | Y | - |

### Visits

| Action | Owner | Admin | Receptionist | Nurse |
|--------|:-----:|:-----:|:------------:|:-----:|
| List visits | Y | Y | Y | Y |
| View visit details | Y | Y | Y | Y |
| Create visit | Y | Y | Y | - |
| Add service to visit | Y | Y | Y | Y |
| Remove service from visit | Y | Y | Y* | - |
| Override service price | Y | Y | - | - |
| Cancel visit | Y | Y | - | - |

*Receptionist can only remove services they added, same day only.

### Invoices

| Action | Owner | Admin | Receptionist | Nurse |
|--------|:-----:|:-----:|:------------:|:-----:|
| List invoices | Y | Y | Y | Y |
| View invoice details | Y | Y | Y | Y |
| Create invoice | Y | Y | Y | - |
| Apply discount | Y | Y | - | - |
| Void invoice | Y | Y | - | - |

### Payments

| Action | Owner | Admin | Receptionist | Nurse |
|--------|:-----:|:-----:|:------------:|:-----:|
| List payments | Y | Y | Y | Y |
| Record payment | Y | Y | Y | - |
| Void payment | Y | Y | - | - |

### Staff Management

| Action | Owner | Admin | Receptionist | Nurse |
|--------|:-----:|:-----:|:------------:|:-----:|
| List staff | Y | Y | - | - |
| View staff details | Y | Y | - | - |
| Create admin | Y | - | - | - |
| Create receptionist/nurse | Y | Y | - | - |
| Edit staff | Y | Y** | - | - |
| Deactivate staff | Y | Y** | - | - |
| Reactivate staff | Y | Y | - | - |

**Admin can only edit/deactivate users of lower rank (receptionist, nurse).

---

## Multi-Tenant Data Isolation (`apps/core/mixins.py`)

### ClinicScopedMixin

Applied to all list/detail views. This mixin does two things:

**1. Filters querysets by clinic:**
```python
def get_queryset(self):
    return super().get_queryset().filter(clinic=self.request.user.clinic)
```

A user from Clinic A can never see data from Clinic B, even if they guess a UUID.

**2. Auto-sets clinic on create:**
```python
def perform_create(self, serializer):
    serializer.save(
        clinic=self.request.user.clinic,
        created_by=self.request.user,  # if model has created_by
    )
```

The clinic is always set server-side from the JWT token — it cannot be spoofed in the request body.

---

## Staff Hierarchy Enforcement

Staff management views enforce an additional rule beyond role checks: **you cannot modify users of equal or higher rank.**

| Requester | Can manage |
|-----------|-----------|
| Owner (4) | Admin (3), Receptionist (2), Nurse (1) |
| Admin (3) | Receptionist (2), Nurse (1) |

This is checked using the `role_level` property on the User model:
```python
@property
def role_level(self):
    return self.ROLE_HIERARCHY.get(self.role, 0)
    # owner=4, admin=3, receptionist=2, nurse=1
```

Additional constraints:
- Cannot deactivate yourself
- Cannot deactivate the owner
- Only the owner can assign the `admin` role
