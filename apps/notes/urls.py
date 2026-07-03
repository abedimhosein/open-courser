from django.urls import path

from apps.notes import views

urlpatterns = [
    path(
        "courses/<int:course_pk>/nodes/<int:node_pk>/notes/",
        views.note_list_partial,
        name="note_list_partial",
    ),
    path(
        "courses/<int:course_pk>/nodes/<int:node_pk>/notes/create/",
        views.note_create,
        name="note_create",
    ),
    path("<int:pk>/edit/", views.note_edit, name="note_edit"),
    path("<int:pk>/delete/", views.note_delete, name="note_delete"),
    path("search/", views.notes_search, name="notes_search"),
]
