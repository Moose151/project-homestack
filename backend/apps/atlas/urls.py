from django.urls import path

from apps.atlas.views import (
    AtlasSearchView,
    BirthdayOccurrenceView,
    ContactDetailView,
    ContactListView,
    GroceryClearBoughtView,
    GroceryListView,
    GrocerySuggestionsView,
    ListDetailView,
    ListItemCompleteView,
    ListItemDetailView,
    ListItemListView,
    ListItemMoveView,
    ListItemUncompleteView,
    ListSuggestionListView,
    ListSuggestionReviewView,
    ListListView,
    NoteDetailView,
    NoteListView,
    ReminderDetailView,
    ReminderListView,
    TodoListsView,
    TodoQuickCreateView,
    TodoTodayView,
)

urlpatterns = [
    path("contacts/", ContactListView.as_view(), name="atlas-contact-list"),
    path("contacts/<int:contact_id>/", ContactDetailView.as_view(), name="atlas-contact-detail"),
    path("birthday-occurrences/", BirthdayOccurrenceView.as_view(), name="atlas-birthday-occurrences"),
    # Search
    path("search/", AtlasSearchView.as_view(), name="atlas-search"),

    # Notes
    path("notes/", NoteListView.as_view(), name="atlas-note-list"),
    path("notes/<int:note_id>/", NoteDetailView.as_view(), name="atlas-note-detail"),

    # Grocery — the single household list (D19 §C)
    path("grocery/", GroceryListView.as_view(), name="atlas-grocery"),
    path("grocery/clear-bought/", GroceryClearBoughtView.as_view(), name="atlas-grocery-clear-bought"),
    path("grocery/suggestions/", GrocerySuggestionsView.as_view(), name="atlas-grocery-suggestions"),

    # To-dos — Household + one list per active Person (D19 §D)
    path("todos/lists/", TodoListsView.as_view(), name="atlas-todo-lists"),
    path("todos/today/", TodoTodayView.as_view(), name="atlas-todo-today"),
    path("todos/quick-create/", TodoQuickCreateView.as_view(), name="atlas-todo-quick-create"),

    # Lists
    path("lists/", ListListView.as_view(), name="atlas-list-list"),
    path("lists/<int:list_id>/", ListDetailView.as_view(), name="atlas-list-detail"),
    path("lists/<int:list_id>/items/", ListItemListView.as_view(), name="atlas-list-item-list"),
    path("lists/<int:list_id>/items/<int:item_id>/", ListItemDetailView.as_view(), name="atlas-list-item-detail"),
    path("lists/<int:list_id>/items/<int:item_id>/complete/", ListItemCompleteView.as_view(), name="atlas-list-item-complete"),
    path("lists/<int:list_id>/items/<int:item_id>/uncomplete/", ListItemUncompleteView.as_view(), name="atlas-list-item-uncomplete"),
    path("lists/<int:list_id>/items/<int:item_id>/move/", ListItemMoveView.as_view(), name="atlas-list-item-move"),
    path("lists/<int:list_id>/suggestions/", ListSuggestionListView.as_view(), name="atlas-list-suggestion-list"),
    path("lists/<int:list_id>/suggestions/<int:suggestion_id>/<str:action>/", ListSuggestionReviewView.as_view(), name="atlas-list-suggestion-review"),

    # Reminders — legacy and read-only (D19 §E, docs/11_Node_Atlas.md). Calendar's
    # quick-create "Reminder" action posts to todos/quick-create/ above; these routes exist
    # only so archival rows stay readable. Every write returns 410.
    path("reminders/", ReminderListView.as_view(), name="atlas-reminder-list"),
    path("reminders/<int:reminder_id>/", ReminderDetailView.as_view(), name="atlas-reminder-detail"),
]
