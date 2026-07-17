from django.contrib import admin

from apps.books.models import Book, BookClub, BookClubBook, BookClubMembership, BookClubQueueItem, BookRating, PersonalBookEntry


admin.site.register(Book)
admin.site.register(BookRating)
admin.site.register(PersonalBookEntry)
admin.site.register(BookClub)
admin.site.register(BookClubMembership)
admin.site.register(BookClubBook)
admin.site.register(BookClubQueueItem)
