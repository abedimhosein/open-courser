from django.urls import path

from apps.progress import views

urlpatterns = [
    path("activity/", views.activity, name="activity"),
    path("update/<int:node_pk>/", views.update_position, name="update_position"),
    path("complete/<int:node_pk>/", views.mark_file_completed, name="mark_completed"),
    path("progress/<int:node_pk>/", views.file_progress, name="file_progress"),
    path("reset/<int:node_pk>/", views.reset_progress, name="reset_progress"),
]
