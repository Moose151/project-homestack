# Node Spec — Books

> **Status:** shipped opt-in node. Books owns personal reading shelves and shared household book
> clubs. It was already implemented and registered in HomeStack but was missing from the older
> canonical node-model documentation; this spec corrects that documentation gap.

## 1. Purpose

Books answers two related household questions:

- **What am I reading / what do I want to read?**
- **What is our book club reading next?**

It provides one household catalogue of Book records, personal reading-state entries and shared club
shelves/queues without turning Education or Atlas into a library system.

## 2. Ownership boundaries

**Books owns:**

- household Book catalogue metadata;
- each User's personal reading shelf/status;
- each User's rating/notes for a Book;
- book clubs and membership;
- books on a club shelf and their club reading status;
- ordered club up-next queue.

**Belongs elsewhere:**

- course/required-reading context tied to structured study → Education can link/reference a Book;
- ordinary product/shopping wish → Atlas/Corner as appropriate;
- reward purchase/economy → Meridian;
- files/documents → shared Attachments where later linked;
- general household notes → Atlas.

Books should remain independently useful as a reading domain rather than being merged into
Education merely because some books are used for study.

## 3. Shared Book catalogue

`Book` is the shared household representation of a title/edition and currently supports the
implemented metadata including:

- title;
- author;
- pages;
- genre;
- ISBN;
- publication date text;
- description;
- cover URL;
- source URL.

Personal shelves and club shelves point to the same Book record rather than each storing a private
copy of metadata.

Search covers title, author, genre, ISBN and description through PostgreSQL FTS with the established
SQLite fallback.

## 4. Personal shelves

A `PersonalBookEntry` belongs to one User and one Book.

Current personal reading states are:

- `backlog` — Want to Read;
- `reading` — Reading;
- `history` — Read.

Each User can have one personal entry for a given Book. Position/order can be retained within the
shelf state.

The personal shelf endpoint returns the User's own entries and can also include club books relevant
to that User for a combined reading view without changing ownership.

## 5. Ratings and notes

`BookRating` is unique per **User + Book** and stores the User's optional rating and notes.

Current rating scale is 0–10 where a numeric rating is supplied.

The same personal rating/notes follow the Book across contexts. If a User has rated a Book from
their personal history, that is also their rating when the same Book appears in a club. Do not
create separate personal-versus-club ratings that drift.

Club views can show member ratings and derived average rating for the Book while preserving each
member's individual rating.

## 6. Book clubs

A `BookClub` is a household-scoped shared reading group with the implemented basics such as name,
colour and description.

Membership is explicit through `BookClubMembership`.

Important visibility rule: club lists/details are filtered to clubs the current User belongs to.
Knowing a club ID is not authority to view or edit a club outside the User's membership/permission
boundary.

## 7. Club shelves

`BookClubBook` links a Book to one Club and records the club-level reading state.

Current states are:

- `backlog`;
- `reading`;
- `history`.

A Book appears at most once on a given club shelf. The club entry may retain position and the User
who originally added it.

The club state is shared by club members; individual ratings/notes remain per User + Book.

## 8. Up-next queue

`BookClubQueueItem` gives a Club an ordered next-reading queue over existing club-book entries.

A queue item references the `BookClubBook` rather than duplicating Book metadata. Position changes
reorder the shared queue.

Queue access follows club membership/Books permissions.

## 9. Book discovery / URL and ISBN enrichment — shipped

Books reuses the shared safe Link Import capability (`29_Core_Link_Import.md`).

The user can provide a public book URL or ISBN. The importer prefers public structured metadata and
can enrich a specific edition using the configured public catalogue source (currently including
Open Library behavior described in doc 29).

It can attempt useful fields such as:

- title;
- authors;
- ISBN/edition metadata;
- publication date;
- page count;
- genre/subjects;
- description;
- cover;
- source URL.

The preview is reviewed before save. External metadata is provenance/enrichment, not the durable
source of truth after the household has confirmed or edited the Book.

Do not add a Books-specific arbitrary scraper or bypass retailer/catalogue anti-bot controls.

## 10. API ownership

Routes live under the Books API namespace and currently cover the implemented families:

- available HomeStack Users for club membership UI;
- Book list/create/detail/update/delete;
- User rating upsert;
- personal shelf list/create/update/delete;
- club list/create/detail/update/delete;
- club membership add/remove;
- club-book list/add/update/remove;
- club queue list/add/reorder/remove.

Exact route names are defined by `backend/apps/books/urls.py` and tests.

## 11. Permissions

Books uses the central `books` resource permission through `HomeStackPermission`.

In addition to global role/action permission:

- personal shelf mutations are scoped to the authenticated User's own `PersonalBookEntry`;
- club list/detail/member/book/queue reads resolve only through clubs the User belongs to;
- edit actions continue through the central permission action contract;
- direct-ID requests must not bypass those User/club selector boundaries.

Books is not a sensitive-node-by-default domain, but ordinary authentication/household/permission
rules still apply.

## 12. Hub / Calendar / Notifications

Books is primarily a reading-management node rather than a scheduling domain.

Possible/current useful shared projections include reading/club summaries and Books notification
categories where implemented. Do not create Calendar events merely because a Book changes shelf
state.

Future club due dates/meeting dates should be Calendar-owned or Book-owned only if a real workflow
needs them and should follow D7.

Web Push uses the shared Notifications preference/device infrastructure; Books does not own a push
channel.

## 13. Search

Books catalogue search uses permission-safe household Book data and supports the implemented FTS
fields.

A future global HomeStack Search provider should return only safe Book/club context and must not
expose a club relationship the User cannot access.

## 14. Responsive experience

The current Books experience supports:

- personal Want to Read / Reading / Read shelves;
- club-highlighted books and filtering;
- adding/editing Books with duplicate-avoidance/search assistance;
- rating/notes;
- club creation/editing and membership management;
- shared club backlog/reading/history;
- ordered up-next queue;
- URL/ISBN enrichment followed by user review.

Phone layouts should remain shelf/card oriented rather than depend on dense tables.

## 15. Data ownership

Exact schema is defined by current Django models/migrations. The principal families are:

- `Book`;
- `BookRating`;
- `PersonalBookEntry`;
- `BookClub`;
- `BookClubMembership`;
- `BookClubBook`;
- `BookClubQueueItem`.

All current rows use the HomeStack household/base-model conventions as implemented.

## 16. Relationship to future consolidation

`31_Core_Manage_HomeStack.md` notes Books could someday be reconsidered if actual usage shows its
navigation can be simplified. That is **not a decision to remove or merge the shipped Books node**.

Do not force the existing personal/club reading model into Atlas or Education solely to reduce the
node count. Any consolidation would need to preserve shelves, clubs, queue, ratings, stable routes
and permissions without data loss.

## 17. Completion state

The current Books baseline is shipped:

- shared catalogue;
- personal backlog/reading/history;
- one personal rating/notes record per User + Book;
- shared Book Clubs with membership;
- club backlog/reading/history;
- ordered club up-next queue;
- searchable catalogue;
- URL/ISBN enrichment;
- responsive UI and central permissions.

Future work should be based on household reading use, such as richer reading goals/history,
notifications or Education linking—not another rebuild of the core Books data model.