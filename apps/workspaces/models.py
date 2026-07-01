from django.db import models


class Workspace(models.Model):
    name = models.CharField(max_length=255)
    course_root = models.CharField(max_length=1024)
    cover_image = models.ImageField(upload_to="covers/workspaces/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
