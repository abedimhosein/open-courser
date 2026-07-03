import uuid
from pathlib import Path

from django.db import models
from django.utils import timezone

from apps.workspaces.models import Workspace


def _cover_upload_path(_instance, filename: str) -> str:
    ext = Path(filename).suffix
    return f"covers/courses/{uuid.uuid4().hex}{ext}"


class Course(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="courses",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    root_path = models.CharField(max_length=1024)
    cover_image = models.ImageField(upload_to=_cover_upload_path, blank=True)
    locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=timezone.now, blank=True)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title


class CourseNode(models.Model):
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
    NODE_TYPE_CHOICES = [
        ("directory", "Directory"),
        ("file", "File"),
    ]

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="nodes",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    name = models.CharField(max_length=255)
    relative_path = models.CharField(max_length=1024)
    node_type = models.CharField(max_length=16, choices=NODE_TYPE_CHOICES)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, blank=True, default="")
    mime_type = models.CharField(max_length=100, blank=True, default="")
    file_size = models.BigIntegerField(null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        unique_together = [("course", "relative_path")]

    def __str__(self) -> str:
        return self.name
