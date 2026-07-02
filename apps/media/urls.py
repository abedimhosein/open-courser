from django.urls import path

from apps.media import views

urlpatterns = [
    path("serve/<int:course_pk>/<int:node_pk>/", views.serve_media, name="serve_media"),
]
