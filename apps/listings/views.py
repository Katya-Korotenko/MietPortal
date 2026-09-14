from rest_framework import viewsets, permissions
from rest_framework.response import Response

from core.permissions import IsLandlord, IsOwnerOrReadOnly
from .models import Listing
from .serializers import ListingSerializer
from .filters import ListingFilter
from ..statistic.models import SearchQuery, ViewHistory


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    filterset_class = ListingFilter
    search_fields = ['title', 'description']
    ordering_fields = ['price', 'created_at']

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsLandlord()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(landlord=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user if request.user.is_authenticated else None
        ViewHistory.objects.get_or_create(listing=instance, user=user)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        search_text = request.query_params.get('search')
        if search_text:
            SearchQuery.objects.create(query_text=search_text.strip().lower())
        return super().list(request, *args, **kwargs)