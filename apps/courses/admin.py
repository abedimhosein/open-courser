from django.contrib import admin

from apps.courses.models import Course, CourseNode, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "color"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "workspace", "root_path", "created_at"]
    list_filter = ["workspace", "tags"]
    search_fields = ["title"]
    filter_horizontal = ["tags"]


@admin.register(CourseNode)
class CourseNodeAdmin(admin.ModelAdmin):
    list_display = ["name", "course", "node_type", "file_type", "sort_order"]
    list_filter = ["node_type", "course__workspace"]
    search_fields = ["name", "relative_path"]
