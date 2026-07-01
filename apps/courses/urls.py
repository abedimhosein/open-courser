from django.urls import path

from apps.courses import views

urlpatterns = [
    path("<int:pk>/", views.course_detail, name="course_detail"),
    path("<int:pk>/edit/", views.course_edit, name="course_edit"),
    path("<int:pk>/progress/", views.course_progress_partial, name="course_progress_partial"),
    path("<int:pk>/files/", views.course_files_partial, name="course_files_partial"),
    path("<int:course_pk>/files/<int:file_pk>/", views.file_detail, name="file_detail"),
    path(
        "<int:course_pk>/files/<int:file_pk>/toggle/",
        views.toggle_complete,
        name="toggle_complete",
    ),
    path(
        "<int:course_pk>/files/<int:file_pk>/toggle-panel/",
        views.toggle_file_complete,
        name="toggle_file_complete",
    ),
]
