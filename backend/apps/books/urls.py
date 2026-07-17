from django.urls import path

from apps.books import views

urlpatterns = [
    path("users/", views.BooksUsersView.as_view(), name="books-users"),
    path("books/", views.BookListView.as_view(), name="books-list"),
    path("books/<int:book_id>/", views.BookDetailView.as_view(), name="books-detail"),
    path("ratings/", views.RatingView.as_view(), name="books-rating"),
    path("personal/", views.PersonalShelfView.as_view(), name="books-personal"),
    path("personal/<int:entry_id>/", views.PersonalShelfDetailView.as_view(), name="books-personal-detail"),
    path("clubs/", views.ClubListView.as_view(), name="books-clubs"),
    path("clubs/<int:club_id>/", views.ClubDetailView.as_view(), name="books-club-detail"),
    path("clubs/<int:club_id>/members/", views.ClubMemberView.as_view(), name="books-club-members"),
    path("clubs/<int:club_id>/members/<int:membership_id>/", views.ClubMemberView.as_view(), name="books-club-member-detail"),
    path("clubs/<int:club_id>/books/", views.ClubBookListView.as_view(), name="books-club-books"),
    path("clubs/<int:club_id>/books/<int:book_entry_id>/", views.ClubBookDetailView.as_view(), name="books-club-book-detail"),
    path("clubs/<int:club_id>/queue/", views.QueueListView.as_view(), name="books-club-queue"),
    path("clubs/<int:club_id>/queue/<int:item_id>/", views.QueueDetailView.as_view(), name="books-club-queue-detail"),
]
