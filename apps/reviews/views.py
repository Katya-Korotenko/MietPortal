from rest_framework import viewsets, permissions

from .models import Review
from .serializers import ReviewSerializer

from .permissions import IsReviewOwner


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
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