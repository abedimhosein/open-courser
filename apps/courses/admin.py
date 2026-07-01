from django.contrib import admin

from apps.courses.models import Course, CourseFile


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["name", "workspace", "created_at"]
    list_filter = ["workspace"]
    search_fields = ["name"]


@admin.register(CourseFile)
class CourseFileAdmin(admin.ModelAdmin):
    list_display = ["name", "course", "file_type", "duration", "file_size"]
    list_filter = ["file_type", "course__workspace"]
    search_fields = ["name", "relative_path"]
