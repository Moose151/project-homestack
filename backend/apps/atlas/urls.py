from django.urls import path

from apps.atlas.views import (
    AtlasSearchView,
    ListDetailView,
    ListItemCompleteView,
    ListItemDetailView,
    ListItemListView,
    ListItemUncompleteView,
    ListListView,
    NoteDetailView,
    NoteListView,
    ReminderDetailView,
    ReminderListView,
)

urlpatterns = [
    # Search
    path("search/", AtlasSearchView.as_view(), name="atlas-search"),

    # Notes
    path("notes/", NoteListView.as_view(), name="atlas-note-list"),
    path("notes/<int:note_id>/", NoteDetailView.as_view(), name="atlas-note-detail"),

    # Lists
    path("lists/", ListListView.as_view(), name="atlas-list-list"),
    path("lists/<int:list_id>/", ListDetailView.as_view(), name="atlas-list-detail"),
    path("lists/<int:list_id>/items/", ListItemListView.as_view(), name="atlas-list-item-list"),
    path("lists/<int:list_id>/items/<int:item_id>/", ListItemDetailView.as_view(), name="atlas-list-item-detail"),
    path("lists/<int:list_id>/items/<int:item_id>/complete/", ListItemCompleteView.as_view(), name="atlas-list-item-complete"),
    path("lists/<int:list_id>/items/<int:item_id>/uncomplete/", ListItemUncompleteView.as_view(), name="atlas-list-item-uncomplete"),

    # Reminders
    path("reminders/", ReminderListView.as_view(), name="atlas-reminder-list"),
    path("reminders/<int:reminder_id>/", ReminderDetailView.as_view(), name="atlas-reminder-detail"),
]
