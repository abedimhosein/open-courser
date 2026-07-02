import uuid
from pathlib import Path

from django.db import models


def _cover_upload_path(_instance, filename: str) -> str:
    ext = Path(filename).suffix
    return f"covers/workspaces/{uuid.uuid4().hex}{ext}"


class Workspace(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    cover_image = models.ImageField(upload_to=_cover_upload_path, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
