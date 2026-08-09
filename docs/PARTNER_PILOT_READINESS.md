# Partner household pilot readiness

**Status:** Code-ready for a controlled two-adult household pilot. Production deployment and
real-device acceptance are still required.

This is the practical release gate for inviting a trusted adult partner into HomeStack. It
separates implemented, visible destinations from future catalogue nodes and prevents “present in
the menu” being confused with “safe and useful”.

## 1. What partner-ready means

A destination is ready for the pilot when:

- its main create, find, update and complete workflow is present;
- phone and desktop navigation use the same household-facing name and shared visual controls;
- primary phone actions do not require horizontal table scrolling or hover;
- loading, empty, error and destructive states are understandable;
- the account can only discover destinations and Hub widgets it may actually open;
- a date or financial fact has one owning record and other nodes show a link or synced projection,
  rather than asking for the same information again;
- automated permission and domain tests pass; and
- any remaining limitation is recorded below instead of hidden from the household.

“Ready” does not mean every long-term feature in a node specification is complete. It means the
core daily journey is coherent enough to use and give concrete feedback on.

## 2. Account setup for a partner

From an administrator account, open **People & access** and choose **Add household login**.

1. Use **Household manager** for a trusted adult partner. This gives normal household management
   without account/system administration.
2. Set a 4–6 digit PIN for everyday sign-in and a password for protected actions.
3. Link the login to their existing Person, or let HomeStack create the Person once. Do not create
   a second Person for the same human.
4. Deliberately enable **Money and home-finance access** only if they should use Solace and linked
   Homestead costs. Child accounts cannot receive it and an adult password is required.
5. Sign in on their phone, open **More**, and choose the four daily bottom-bar destinations they
   prefer. All other available destinations remain in the More directory and global search.

Money access is an explicit per-user permission set and is audit logged. Without it, Money and
its Hub widgets are absent rather than visible as broken or forbidden destinations.

## 3. Implemented destination readiness

| Household destination | Core pilot workflow | Code gate | Household acceptance |
|---|---|---|---|
| Home | View household summaries, quick-create, tune widgets, drag desktop widgets, reorder on touch | Ready | Pending two-account use |
| Calendar | Create/edit events; month/week/day/agenda; indefinite rotating schedule; change/restore one date | Ready | Validate full care cycle on both phones |
| Lists & notes | Lists/items, completion, assignment/dates, notes, reminders, search and quick capture | Ready | Validate long real list items and reminders |
| School & study | Academic profile, courses, assignments/exams, timetable, events, notes/files and Calendar sync | Ready | Validate the current term's real records |
| Books | Personal shelves, queue/history, ratings, search, book clubs and club items | Ready | Validate labelled add/edit, queue and removal flows on phone |
| Household guide | Pages, categories, favourites, emergency/kiosk flags, visibility and search | Ready | Add/edit a real page and manage its category on phone |
| Pets | Profiles, treatment/appointment management, recurring due dates, completion, search and Calendar sync | Ready | Validate one real treatment cycle and appointment edit |
| Our home | Rooms/plans, maintenance, appliances/warranties, improvements, contacts, costs and cover | Ready | Validate a maintenance-to-Money round trip |
| Tasks & rewards | Tasks, recurrence, approvals, routines, points, rewards, allowances, goals, wishlist and leaderboard | Ready | Validate manager and participant flows on phones |
| Money | Bills/occurrences, pay cycles, buckets, subscriptions, purchases, forecast, closeout and management | Ready for controlled pilot | Real-data cutover comparison still required |

The future Inventory, non-home Assets, Hearth, Travel, Projects, Health and Home Assistant nodes
are not part of this gate. They remain disabled and do not appear in household navigation.
Enabling a node requires both an implemented destination and household choice.

## 4. Single-entry and cross-node ownership

Use this table when deciding where to enter or edit something.

| Information | Enter/edit once in | What other surfaces do |
|---|---|---|
| General household event | Calendar | Calendar displays it directly |
| List reminder | Lists & notes | Calendar and Home show the synced occurrence/source link |
| Assignment, exam, class or education event | School & study | Calendar/Home show its projection; Education remains owner |
| Pet treatment or appointment | Pets | Calendar/Home show due/upcoming state; Pets remains owner |
| Home maintenance date | Our home | Calendar/Home show it; completing a recurrence advances the source date |
| Home insurance, rates/service or paid maintenance cost | Our home for descriptive home details; Money for amount/payment state | The linked pair is created through the handoff and deep-links both ways; it is not two independent records |
| Ordinary bill, subscription, payday or purchase | Money | Calendar/Home may show protected projections; Money remains owner |
| Meridian task/reward activity | Tasks & rewards | Home, notifications and achievements present derived status |
| Person and login identity | People & access | Calendar, Lists, Education, Pets and Meridian reference the same Person |

For linked Homestead/Money records, the UI identifies the editing owner. A linked Solace bill
cannot be independently edited or deleted in a way that would drift from its Homestead source.
Calendar events generated by nodes link back to their source and are not separately editable.

## 5. Required real-device acceptance pass

Run this after rebuilding the home-server images and applying migrations:

- Sign in as each adult on a phone and as an administrator on desktop. Confirm each account sees
  only usable destinations and can edit its four phone shortcuts.
- Create a list item, Calendar event and Home maintenance task as the partner; edit and complete
  them; confirm touch actions remain visible and no primary journey scrolls sideways.
- Set the 14-night care rotation, inspect at least three future months, change one date and restore
  it. Confirm only a narrow colour strip marks each day.
- Create or hand off one home-insurance/service record and one maintenance cost. Confirm one linked
  Solace bill, one authoritative financial Calendar event and working links in both directions.
- Create, edit and approve a task and a reward request on a phone; repeat the common action on
  desktop and confirm the layouts feel like the same product. Create a routine and group goal,
  then submit and approve a wishlist request; confirm a failed action remains visible.
- With Money access off for a test manager, confirm Money and finance widgets are absent. Turn it
  on, sign in again, unlock with that user's password and confirm the destination appears. While
  it is off, also confirm Our home hides Costs & cover, Track cost and protected Money links.
- Add and edit a book, move it between shelves, manage a shared queue and deliberately cancel one
  removal confirmation. Confirm failed actions would remain visible rather than silently closing.
- Add a pet treatment and appointment, edit both, then delete a test appointment. Confirm dates
  remain linked to Calendar and all phone actions are available without hover.
- Use each implemented destination's empty state, search and primary create action at least once.
  Record friction by task and device rather than starting another broad visual rewrite.

## 6. Known gates after the invite

- Native Solace still needs comparison against the household's real standalone data for a full pay
  cycle and month before the standalone app is retired.
- The generic sensitive-node lock and remaining permission/audit maturation are still Milestone 4
  work. Solace itself retains its explicit permission and optional password-on-entry protection.
- Home Assistant is important but planned separately in Milestone 5.5; it is not required to begin
  this two-adult pilot.
- Kiosk refinement is deliberately behind responsive phone/desktop use.

## 7. Automated release evidence

For this gate, run:

```bash
cd backend
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py makemigrations --check --dry-run

cd ../frontend
npm run build
```

The household acceptance column only changes from **Pending** after the corresponding workflow is
used with real data on the actual phone/desktop deployment.
