from rest_framework import serializers as drf_serializers, status
from rest_framework.generics import ListCreateAPIView, GenericAPIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, inline_serializer

from apps.core.permissions import IsOwnerOrAdmin
from apps.core.utils import generate_temp_password

from .models import User
from .staff_serializers import StaffListSerializer, StaffCreateSerializer, StaffUpdateSerializer


class StaffListCreateView(ListCreateAPIView):
    """List and create staff members for the current clinic."""
    serializer_class = StaffListSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()
        return User.objects.filter(clinic=self.request.user.clinic).order_by('-created_at')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return StaffListSerializer
        return StaffCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        temp_password = generate_temp_password()

        user = User.objects.create_user(
            phone=data['phone'],
            password=temp_password,
            first_name=data['firstName'],
            last_name=data['lastName'],
            email=data.get('email') or None,
            role=data['role'],
            clinic=request.user.clinic,
            must_change_password=True,
        )

        # TODO: Send SMS with temp_password to user.phone via Africa's Talking

        output = StaffListSerializer(user)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @extend_schema(tags=['Staff'], summary='List staff members')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=['Staff'], summary='Create a staff member', request=StaffCreateSerializer, responses={201: StaffListSerializer})
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class StaffDetailView(GenericAPIView):
    """GET / PATCH a staff member."""
    permission_classes = [IsOwnerOrAdmin]

    def get_staff_or_404(self, request, staff_id):
        try:
            return User.objects.get(id=staff_id, clinic=request.user.clinic)
        except User.DoesNotExist:
            return None

    def _check_hierarchy(self, request, target):
        """Ensure requester outranks or matches target (owner > admin > others)."""
        if request.user.role_level <= target.role_level and request.user.id != target.id:
            return Response(
                {'error': 'forbidden', 'message': 'Vous ne pouvez pas modifier un utilisateur de rang egal ou superieur.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    @extend_schema(tags=['Staff'], summary='Get staff member details', responses={200: StaffListSerializer})
    def get(self, request, staff_id):
        staff = self.get_staff_or_404(request, staff_id)
        if not staff:
            return Response({'error': 'not_found', 'message': 'Membre du personnel introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(StaffListSerializer(staff).data)

    @extend_schema(tags=['Staff'], summary='Update a staff member', request=StaffUpdateSerializer, responses={200: StaffListSerializer})
    def patch(self, request, staff_id):
        staff = self.get_staff_or_404(request, staff_id)
        if not staff:
            return Response({'error': 'not_found', 'message': 'Membre du personnel introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        hierarchy_error = self._check_hierarchy(request, staff)
        if hierarchy_error:
            return hierarchy_error

        serializer = StaffUpdateSerializer(data=request.data, context={'request': request, 'staff': staff})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if 'firstName' in data:
            staff.first_name = data['firstName']
        if 'lastName' in data:
            staff.last_name = data['lastName']
        if 'phone' in data:
            staff.phone = data['phone']
        if 'email' in data:
            staff.email = data['email'] or None
        if 'role' in data:
            staff.role = data['role']

        staff.save()
        return Response(StaffListSerializer(staff).data)


class StaffDeactivateView(GenericAPIView):
    """POST /staff/<id>/deactivate/"""
    permission_classes = [IsOwnerOrAdmin]

    @extend_schema(tags=['Staff'], summary='Deactivate a staff member', request=None, responses={200: inline_serializer('MessageResponse', fields={'message': drf_serializers.CharField()})})
    def post(self, request, staff_id):
        try:
            staff = User.objects.get(id=staff_id, clinic=request.user.clinic)
        except User.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Membre du personnel introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if staff.id == request.user.id:
            return Response({'error': 'forbidden', 'message': 'Vous ne pouvez pas vous desactiver vous-meme.'}, status=status.HTTP_400_BAD_REQUEST)

        if staff.role == 'owner':
            return Response({'error': 'forbidden', 'message': 'Impossible de desactiver le proprietaire.'}, status=status.HTTP_403_FORBIDDEN)

        if request.user.role_level <= staff.role_level:
            return Response({'error': 'forbidden', 'message': 'Vous ne pouvez pas desactiver un utilisateur de rang egal ou superieur.'}, status=status.HTTP_403_FORBIDDEN)

        staff.is_active = False
        staff.save(update_fields=['is_active', 'updated_at'])
        return Response({'message': 'Membre du personnel desactive.'})


class StaffReactivateView(GenericAPIView):
    """POST /staff/<id>/reactivate/"""
    permission_classes = [IsOwnerOrAdmin]

    @extend_schema(tags=['Staff'], summary='Reactivate a staff member', request=None, responses={200: inline_serializer('MessageResponse2', fields={'message': drf_serializers.CharField()})})
    def post(self, request, staff_id):
        try:
            staff = User.objects.get(id=staff_id, clinic=request.user.clinic)
        except User.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Membre du personnel introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        staff.is_active = True
        staff.save(update_fields=['is_active', 'updated_at'])
        return Response({'message': 'Membre du personnel reactive.'})
