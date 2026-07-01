from django.urls import path

from apps.workspaces import views

urlpatterns = [
    path("", views.workspace_list, name="workspace_list"),
    path("workspace/create/", views.workspace_create, name="workspace_create"),
    path("workspace/<int:pk>/", views.workspace_detail, name="workspace_detail"),
    path("workspace/<int:pk>/delete/", views.workspace_delete, name="workspace_delete"),
    path("workspace/<int:pk>/scan/", views.workspace_scan, name="workspace_scan"),
    path("workspace/<int:pk>/edit/", views.workspace_edit, name="workspace_edit"),
    path("workspace/browse/", views.browse_directories, name="browse_directories"),
]
