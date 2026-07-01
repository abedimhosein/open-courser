from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.workspaces.urls")),
    path("courses/", include("apps.courses.urls")),
    path("media/", include("apps.media.urls")),
    path("progress/", include("apps.progress.urls")),
]
