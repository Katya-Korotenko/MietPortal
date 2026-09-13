from django.contrib import admin

from .models import SearchQuery, ViewHistory


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ('query_text', 'created_at')
    search_fields = ('query_text',)


@admin.register(ViewHistory)
class ViewHistoryAdmin(admin.ModelAdmin):
    list_display = ('listing', 'user', 'viewed_at')
    list_filter = ('viewed_at',)