from django.urls import path

from apps.media import views

urlpatterns = [
    path("serve/<int:course_pk>/<int:node_pk>/", views.serve_media, name="serve_media"),
    path("serve-subtitle/<int:course_pk>/<path:sub_path>/", views.serve_subtitle, name="serve_subtitle"),
]
