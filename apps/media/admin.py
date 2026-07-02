from django.contrib import admin

from apps.media.models import MediaMetadata


@admin.register(MediaMetadata)
class MediaMetadataAdmin(admin.ModelAdmin):
    list_display = ["course_node", "duration", "file_format", "extracted_at"]
    search_fields = ["course_node__name"]
