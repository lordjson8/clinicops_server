from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import Patient
from .serializers import PatientListSerializer, PatientDetailSerializer
from .filters import PatientSearchFilter


class PatientPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class PatientListCreateView(ListCreateAPIView):
    queryset = Patient.objects.all()
    pagination_class = PatientPagination
    filter_backends = [PatientSearchFilter]

    def get_serializer_class(self):
        return PatientListSerializer if self.request.method == "GET" else PatientDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exc:
            # Surface duplicate_phone errors with a clean 400 shape
            errors = exc.detail if hasattr(exc, "detail") else {}
            if isinstance(errors, dict) and "error" in errors:
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        patient = serializer.save()
        output = PatientDetailSerializer(patient, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)


class PatientDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientDetailSerializer
    lookup_field = "id"

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True  # Always allow partial updates (PATCH behaviour)
        return super().update(request, *args, **kwargs)