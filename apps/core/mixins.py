class ClinicScopedMixin:
    """Scopes querysets to the authenticated user's clinic and auto-sets clinic on create."""

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_authenticated:
            return qs.none()
        return qs.filter(clinic=self.request.user.clinic)

    def perform_create(self, serializer):
        extra = {'clinic': self.request.user.clinic}
        # Auto-set created_by if the model has that field
        model = serializer.Meta.model
        if hasattr(model, 'created_by'):
            extra['created_by'] = self.request.user
        serializer.save(**extra)
