from django.db import models


class MediaMetadata(models.Model):
    """
    Cached media metadata extracted via ffprobe.

    Belongs to the Backend Django Agent (persistence) but the data
    is produced by the Media Processing Agent.
    """

    relative_path = models.CharField(max_length=1024, unique=True)
    duration = models.FloatField(null=True, blank=True)
    codec = models.CharField(max_length=50, blank=True, default="")
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    bitrate = models.IntegerField(null=True, blank=True)
    file_format = models.CharField(max_length=50, blank=True, default="")
    subtitle_paths = models.JSONField(default=list, blank=True)
    extracted_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "media metadata"

    def __str__(self) -> str:
        return self.relative_path
