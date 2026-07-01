from django.db import models

from apps.workspaces.models import Workspace


class Course(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="courses",
    )
    name = models.CharField(max_length=255)
    relative_path = models.CharField(max_length=1024)
    cover_image = models.ImageField(upload_to="covers/courses/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("workspace", "relative_path")]

    def __str__(self) -> str:
        return self.name


class CourseFile(models.Model):
    FILE_TYPE_CHOICES = [
        ("video", "Video"),
        ("audio", "Audio"),
        ("subtitle", "Subtitle"),
        ("document", "Document"),
        ("image", "Image"),
        ("archive", "Archive"),
        ("source_code", "Source Code"),
        ("other", "Other"),
    ]

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="files",
    )
    name = models.CharField(max_length=255)
    relative_path = models.CharField(max_length=1024)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    mime_type = models.CharField(max_length=100, blank=True, default="")
    file_size = models.BigIntegerField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["relative_path"]
        unique_together = [("course", "relative_path")]

    def __str__(self) -> str:
        return self.name
