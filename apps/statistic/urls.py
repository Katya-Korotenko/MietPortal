from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import StatisticsViewSet

router = DefaultRouter()
router.register('', StatisticsViewSet, basename='statistic')

urlpatterns = [
    path('', include(router.urls)),
]