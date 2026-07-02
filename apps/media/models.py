from django.db import models

from apps.courses.models import CourseNode


class MediaMetadata(models.Model):
    course_node = models.OneToOneField(
        CourseNode,
        on_delete=models.CASCADE,
        related_name="media_metadata",
    )
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
        return str(self.course_node)
