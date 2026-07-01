from django.urls import path

from apps.media import views

urlpatterns = [
    path("serve/<int:course_pk>/<int:file_pk>/", views.serve_media, name="serve_media"),
]
