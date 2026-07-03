from django.db import models


class Note(models.Model):
    course_node = models.ForeignKey(
        "courses.CourseNode",
        on_delete=models.CASCADE,
        related_name="notes",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        preview = self.content[:50].replace("\n", " ")
        return f"Note on {self.course_node.name}: {preview}..."
