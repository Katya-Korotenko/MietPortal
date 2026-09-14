from django.db.models import Count
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.listings.models import Listing
from apps.listings.serializers import ListingSerializer
from .models import SearchQuery


class StatisticsViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'])
    def popular_searches(self, request):
        queryset = (
            SearchQuery.objects
            .values('query_text')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        return Response(list(queryset))

    @action(detail=False, methods=['get'])
    def popular_listings(self, request):
        queryset = (
            Listing.objects
            .annotate(views_count=Count('views'))
            .order_by('-views_count')[:10]
        )
        serializer = ListingSerializer(queryset, many=True)
        return Response(serializer.data)

