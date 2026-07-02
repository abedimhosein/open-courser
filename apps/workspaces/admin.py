from django.contrib import admin

from apps.workspaces.models import Workspace


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "created_at"]
    search_fields = ["name"]
