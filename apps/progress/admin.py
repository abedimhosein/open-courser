from django.contrib import admin

from apps.progress.models import WatchHistory


@admin.register(WatchHistory)
class WatchHistoryAdmin(admin.ModelAdmin):
    list_display = ["course_node", "position", "duration_watched", "completed", "last_watched_at"]
    list_filter = ["completed"]
    search_fields = ["course_node__name"]
