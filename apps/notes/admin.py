from django.contrib import admin

from apps.notes.models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ["course_node", "content", "created_at", "updated_at"]
    list_filter = ["created_at"]
    search_fields = ["content"]
