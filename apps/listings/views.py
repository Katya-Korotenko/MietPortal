from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from core.permissions import IsLandlord, IsOwnerOrReadOnly
from .models import Listing
from .serializers import ListingSerializer
from .filters import ListingFilter
from ..statistic.models import SearchQuery, ViewHistory


class ListingViewSet(viewsets.ModelViewSet):
    """Listing CRUD, plus automatic analytics side effects:
        retrieve() logs a view in ViewHistory, list() logs the search term in
        SearchQuery when a ?search= param is present. Both fail silently on
        IntegrityError so that analytics logging can never break the main response.
    """
    serializer_class = ListingSerializer
    filterset_class = ListingFilter
    search_fields = ['title', 'description']
    ordering_fields = ['price', 'created_at']

    def get_queryset(self):
        user = self.request.user
        public = Q(is_active=True, is_deleted=False)

        if not user.is_authenticated:
            return Listing.all_objects.filter(public)

        query = public | Q(landlord=user, is_deleted=False)
        if self.action == 'retrieve':
            query |= Q(bookings__tenant=user)  
        return Listing.all_objects.filter(query).distinct()

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsLandlord()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        return [permissions.AllowAny()]

    def _save_or_400(self, serializer, **kwargs):
        """Saves the serializer; if the DB unique constraint fires (a race that
        slipped past validate()), returns a clean 400 instead of a 500."""
        try:
            with transaction.atomic():
                serializer.save(**kwargs)
        except IntegrityError:
            raise ValidationError(
                {'street_address': 'You already have an active listing at this address.'}
            )

    def perform_create(self, serializer):
        self._save_or_400(serializer, landlord=self.request.user)

    def perform_update(self, serializer):
        self._save_or_400(serializer)

    def retrieve(self, request, *args, **kwargs):
        """Logs a listing view. Authenticated users are deduplicated via
                get_or_create (one view per user per listing); anonymous views are
                always created fresh, since anonymous visitors can't be told apart.
        """
        instance = self.get_object()
        try:
            if request.user.is_authenticated:
                ViewHistory.objects.get_or_create(listing=instance, user=request.user)
            else:
                ViewHistory.objects.create(listing=instance, user=None)
        except IntegrityError:
            pass
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        """Logs the raw search term (normalized) before delegating to the
                default list behavior, so popularity stats reflect every search —
        even ones that return zero results."""
        search_text = request.query_params.get('search')
        if search_text:
            SearchQuery.objects.create(query_text=search_text.strip().lower()[:255])
        return super().list(request, *args, **kwargs)