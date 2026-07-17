from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.books.models import BookClubBook, BookClubQueueItem, BookRating, PersonalBookEntry


def _make_user(username, role=User.Role.ADMIN, is_child=False) -> User:
    user = User.objects.create_user(
        username=username, display_name=username.capitalize(), role=role, password="pass123!"
    )
    user.set_pin("1234")
    user.is_child_account = is_child
    user.colour = "#123456"
    user.save()
    return user


def _login(client, username, pin="1234"):
    client.post(
        reverse("auth-pin-login"),
        {"username": username, "pin": pin},
        content_type="application/json",
    )


class BooksPermissionTests(TestCase):
    def setUp(self):
        self.user = _make_user("user", User.Role.USER)
        self.guest = _make_user("guest", User.Role.GUEST)
        self.child = _make_user("child", User.Role.USER, is_child=True)

    def test_unauthenticated_rejected(self):
        self.assertIn(self.client.get(reverse("books-personal")).status_code, [401, 403])

    def test_user_can_create_personal_entry(self):
        _login(self.client, "user")
        resp = self.client.post(
            reverse("books-personal"),
            {"book": {"title": "Piranesi", "author": "Susanna Clarke"}, "status": "backlog"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_guest_cannot_create_personal_entry(self):
        _login(self.client, "guest")
        resp = self.client.post(
            reverse("books-personal"),
            {"book": {"title": "Piranesi"}, "status": "backlog"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_child_cannot_create_club(self):
        _login(self.client, "child")
        resp = self.client.post(
            reverse("books-clubs"),
            {"name": "Kids picks", "colour": "#22c55e"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


class BooksCrudTests(TestCase):
    def setUp(self):
        self.alex = _make_user("alex", User.Role.USER)
        self.sam = _make_user("sam", User.Role.USER)
        _login(self.client, "alex")

    def _create_personal(self, title="Piranesi", status="backlog"):
        return self.client.post(
            reverse("books-personal"),
            {"book": {"title": title, "author": "Susanna Clarke", "pages": 272, "genre": "Fantasy"}, "status": status},
            content_type="application/json",
        )

    def test_personal_shelves_can_move_rate_note_and_remove(self):
        resp = self._create_personal()
        self.assertEqual(resp.status_code, 201)
        entry_id = resp.json()["id"]
        book_id = resp.json()["book"]["id"]

        resp = self.client.patch(
            reverse("books-personal-detail", args=[entry_id]),
            {"status": "reading", "position": 2},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "reading")

        resp = self.client.post(
            reverse("books-rating"),
            {"book_id": book_id, "rating": 9, "notes": "Quietly brilliant."},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["rating"], 9)

        resp = self.client.get(reverse("books-personal"))
        item = resp.json()["personal"][0]
        self.assertEqual(item["rating"], 9)
        self.assertEqual(item["notes"], "Quietly brilliant.")

        resp = self.client.delete(reverse("books-personal-detail", args=[entry_id]))
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(PersonalBookEntry.objects.count(), 0)

    def test_club_members_can_add_reorder_rate_and_remove_books(self):
        club = self.client.post(
            reverse("books-clubs"),
            {"name": "Friday Readers", "colour": "#f97316"},
            content_type="application/json",
        ).json()
        self.client.post(
            reverse("books-club-members", args=[club["id"]]),
            {"user_id": self.sam.id},
            content_type="application/json",
        )
        first = self.client.post(
            reverse("books-club-books", args=[club["id"]]),
            {"book": {"title": "The Left Hand of Darkness", "author": "Ursula K. Le Guin"}, "status": "backlog", "position": 1},
            content_type="application/json",
        )
        second = self.client.post(
            reverse("books-club-books", args=[club["id"]]),
            {"book": {"title": "A Wizard of Earthsea", "author": "Ursula K. Le Guin"}, "status": "backlog", "position": 2},
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        first_id = first.json()["id"]
        second_id = second.json()["id"]
        first_book_id = first.json()["book"]["id"]

        self.client.post(
            reverse("books-club-queue", args=[club["id"]]),
            {"club_book_id": second_id, "position": 1},
            content_type="application/json",
        )
        self.client.post(
            reverse("books-club-queue", args=[club["id"]]),
            {"club_book_id": first_id, "position": 2},
            content_type="application/json",
        )
        queue = self.client.get(reverse("books-club-queue", args=[club["id"]])).json()
        self.assertEqual([q["club_book"]["book"]["title"] for q in queue], ["A Wizard of Earthsea", "The Left Hand of Darkness"])

        self.client.patch(
            reverse("books-club-book-detail", args=[club["id"], first_id]),
            {"status": "history"},
            content_type="application/json",
        )
        self.client.post(
            reverse("books-rating"),
            {"book_id": first_book_id, "rating": 10, "notes": "Still sharp."},
            content_type="application/json",
        )

        _login(self.client, "sam")
        self.client.post(
            reverse("books-rating"),
            {"book_id": first_book_id, "rating": 8, "notes": "Loved the world."},
            content_type="application/json",
        )
        history = self.client.get(reverse("books-club-books", args=[club["id"]]) + "?status=history").json()
        self.assertEqual(history[0]["my_rating"], 8)
        self.assertEqual(len(history[0]["ratings"]), 2)
        self.assertEqual(history[0]["average_rating"], 9.0)

        resp = self.client.delete(reverse("books-club-book-detail", args=[club["id"], first_id]))
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(BookClubBook.objects.filter(pk=first_id).count(), 0)

    def test_club_books_show_on_personal_page_and_can_be_filtered_out(self):
        club = self.client.post(
            reverse("books-clubs"),
            {"name": "Shared shelf", "colour": "#0ea5e9"},
            content_type="application/json",
        ).json()
        self.client.post(
            reverse("books-club-books", args=[club["id"]]),
            {"book": {"title": "Station Eleven"}, "status": "reading"},
            content_type="application/json",
        )
        with_clubs = self.client.get(reverse("books-personal")).json()
        self.assertEqual(len(with_clubs["club"]), 1)
        self.assertEqual(with_clubs["club"][0]["club_id"], club["id"])
        without_clubs = self.client.get(reverse("books-personal") + "?include_clubs=0").json()
        self.assertEqual(without_clubs["club"], [])

    def test_removing_queue_item_does_not_remove_backlog_book(self):
        club = self.client.post(
            reverse("books-clubs"),
            {"name": "Queue club"},
            content_type="application/json",
        ).json()
        entry = self.client.post(
            reverse("books-club-books", args=[club["id"]]),
            {"book": {"title": "Kindred"}, "status": "backlog"},
            content_type="application/json",
        ).json()
        queue_item = self.client.post(
            reverse("books-club-queue", args=[club["id"]]),
            {"club_book_id": entry["id"], "position": 1},
            content_type="application/json",
        ).json()
        resp = self.client.delete(reverse("books-club-queue-detail", args=[club["id"], queue_item["id"]]))
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(BookClubQueueItem.objects.count(), 0)
        self.assertEqual(BookClubBook.objects.count(), 1)

    def test_one_rating_per_user_book_shared_between_personal_and_club(self):
        personal = self._create_personal("The Dispossessed", status="history").json()
        book_id = personal["book"]["id"]
        club = self.client.post(reverse("books-clubs"), {"name": "SF club"}, content_type="application/json").json()
        self.client.post(
            reverse("books-club-books", args=[club["id"]]),
            {"book_id": book_id, "status": "history"},
            content_type="application/json",
        )
        self.client.post(
            reverse("books-rating"),
            {"book_id": book_id, "rating": 10, "notes": "No duplicate ratings."},
            content_type="application/json",
        )
        self.client.post(
            reverse("books-rating"),
            {"book_id": book_id, "rating": 9, "notes": "One row updated."},
            content_type="application/json",
        )
        self.assertEqual(BookRating.objects.filter(user=self.alex, book_id=book_id).count(), 1)
        personal_payload = self.client.get(reverse("books-personal")).json()["personal"][0]
        club_payload = self.client.get(reverse("books-club-books", args=[club["id"]]) + "?status=history").json()[0]
        self.assertEqual(personal_payload["rating"], 9)
        self.assertEqual(club_payload["my_rating"], 9)
