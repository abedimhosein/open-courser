from django.contrib import admin

from apps.media.models import MediaMetadata


@admin.register(MediaMetadata)
class MediaMetadataAdmin(admin.ModelAdmin):
    list_display = ["relative_path", "duration", "file_format", "extracted_at"]
    search_fields = ["relative_path"]
