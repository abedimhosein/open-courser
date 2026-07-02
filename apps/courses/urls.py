from django.urls import path

from apps.courses import views

urlpatterns = [
    path("<int:pk>/", views.course_detail, name="course_detail"),
    path("<int:pk>/edit/", views.course_edit, name="course_edit"),
    path("<int:pk>/delete/", views.course_delete, name="course_delete"),
    path("<int:pk>/scan/", views.course_scan, name="course_scan"),
    path("<int:pk>/complete-all/", views.course_complete_all, name="course_complete_all"),
    path("<int:pk>/reset-all/", views.course_reset_all, name="course_reset_all"),
    path("<int:pk>/progress/", views.course_progress_partial, name="course_progress_partial"),
    path("<int:pk>/files/", views.course_files_partial, name="course_files_partial"),
    path("create/<int:workspace_pk>/", views.course_create, name="course_create"),
    path("<int:course_pk>/nodes/<int:node_pk>/", views.file_detail, name="file_detail"),
    path(
        "<int:course_pk>/nodes/<int:node_pk>/toggle/",
        views.toggle_complete,
        name="toggle_complete",
    ),
    path(
        "<int:course_pk>/nodes/<int:node_pk>/toggle-panel/",
        views.toggle_file_complete,
        name="toggle_file_complete",
    ),
]
