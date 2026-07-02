from django.db import models

from apps.courses.models import CourseNode


class WatchHistory(models.Model):
    course_node = models.ForeignKey(
        CourseNode,
        on_delete=models.CASCADE,
        related_name="watch_history",
    )
    position = models.FloatField(default=0.0)
    duration_watched = models.FloatField(default=0.0)
    completed = models.BooleanField(default=False)
    last_watched_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_watched_at"]
        verbose_name_plural = "watch histories"

    def __str__(self) -> str:
        return f"{self.course_node.name} @ {self.position:.1f}s"
