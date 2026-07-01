from django.urls import path

from apps.workspaces import views

urlpatterns = [
    path("", views.workspace_list, name="workspace_list"),
    path("create/", views.workspace_create, name="workspace_create"),
    path("<int:pk>/", views.workspace_detail, name="workspace_detail"),
    path("<int:pk>/delete/", views.workspace_delete, name="workspace_delete"),
    path("<int:pk>/scan/", views.workspace_scan, name="workspace_scan"),
    path("browse/", views.browse_directories, name="browse_directories"),
]
