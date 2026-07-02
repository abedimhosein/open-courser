from django.contrib import admin

from apps.courses.models import Course, CourseNode


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "workspace", "root_path", "created_at"]
    list_filter = ["workspace"]
    search_fields = ["title"]


@admin.register(CourseNode)
class CourseNodeAdmin(admin.ModelAdmin):
    list_display = ["name", "course", "node_type", "file_type", "sort_order"]
    list_filter = ["node_type", "course__workspace"]
    search_fields = ["name", "relative_path"]
