from django.urls import path

from apps.progress import views

urlpatterns = [
    path("update/<int:file_pk>/", views.update_position, name="update_position"),
    path("complete/<int:file_pk>/", views.mark_file_completed, name="mark_completed"),
    path("progress/<int:file_pk>/", views.file_progress, name="file_progress"),
    path("reset/<int:file_pk>/", views.reset_progress, name="reset_progress"),
]
