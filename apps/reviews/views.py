from rest_framework import viewsets, permissions

from .models import Review
from .serializers import ReviewSerializer

from .permissions import IsReviewOwner


class ReviewViewSet(viewsets.ModelViewSet):
    """Reviews are create/read/delete only — never editable once posted
        (http_method_names excludes put/patch), so a published rating can't be
        changed after the fact. Ownership checks for create live in the
        serializer (validate_booking); only destroy needs IsReviewOwner here.
    """
    serializer_class = ReviewSerializer
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        """Supports ?listing=<id> to list all reviews for one listing."""
        queryset = Review.objects.all()
        listing_id = self.request.query_params.get('listing')
        if listing_id:
            queryset = queryset.filter(booking__listing_id=listing_id)
        return queryset

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), IsReviewOwner()]
        return [permissions.AllowAny()]