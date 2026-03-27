from rest_framework.permissions import BasePermission


class IsAnyClinicRole(BasePermission):
    """Any authenticated user who belongs to a clinic."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'clinic_id')
            and request.user.clinic_id is not None
        )


class IsOwner(IsAnyClinicRole):
    """Only clinic owners."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'owner'


class IsOwnerOrAdmin(IsAnyClinicRole):
    """Clinic owners or admins."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in ('owner', 'admin')


class IsOwnerAdminOrReceptionist(IsAnyClinicRole):
    """Clinic owners, admins, or receptionists."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in (
            'owner', 'admin', 'receptionist',
        )


class ReadAnyWriteRestricted(IsAnyClinicRole):
    """
    GET/HEAD/OPTIONS: any clinic role.
    POST/PUT/PATCH/DELETE: only the roles specified in `write_roles`.
    Subclass and set `write_roles` or pass via view attribute.
    """
    write_roles = ('owner', 'admin')

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        roles = getattr(view, 'write_roles', self.write_roles)
        return request.user.role in roles
