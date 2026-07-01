from django.contrib import admin

from apps.progress.models import WatchHistory


@admin.register(WatchHistory)
class WatchHistoryAdmin(admin.ModelAdmin):
    list_display = ["course_file", "position", "duration_watched", "completed", "last_watched_at"]
    list_filter = ["completed"]
    search_fields = ["course_file__name"]
