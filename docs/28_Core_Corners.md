# Core Spec — Household Corners

> **Status:** Initial slice shipped in v0.31.0; current-person routing, exact activity deep links
> and expandable Fitness session summaries shipped in v0.34.0. Roadmap 8.2. A Corner is a household-facing view of a
> `people.Person`, not the administrator-only account/PIN editor and not a public social profile.
> Global permission, visibility, source-of-truth and decoupling rules still apply.

## 1. Purpose

Give every household member one warm, recognisable place that answers:

- What have they been doing recently?
- What is assigned to them now?
- What are they saving for, considering or planning to buy?
- Which source workspace owns each item, and where can an authorised viewer act on it?

The subject is always a `Person`, never directly a login `User` (D12). This includes children
and household members who do not have their own login. `/users` remains the admin-only place for
roles, PINs, passwords and account linking; `/corners/:personId` is the normal household route.
The signed-in member sees **My Corner**; other pages use the person's real display name, such as
**Alex's Corner**. Opening the My Corner navigation entry must resolve the `Person` linked to the
current User and route directly there—never the first alphabetic household member. From that page,
a switcher/directory opens other permitted Corners. If the account is not linked to a Person, show
a clear setup message rather than silently selecting somebody else. Internal `Person` terminology
does not leak into normal navigation.

## 2. Experience

Avatar/name links throughout HomeStack open that member's Corner. A household directory may live
at `/corners`; a stable detail route lives at `/corners/:personId`.

```text
┌──────────────────────────────────────────────────────────────────┐
│ 🦊 Finn                         4 active assignments · 2 wishes  │
│ Household member                                                │
├──────────┬──────────┬──────────────┬─────────────────────────────┤
│ Overview │ Activity │ Assigned     │ Lists & wishes              │
├──────────┴──────────┴──────────────┴─────────────────────────────┤
│ Recent activity                                                 │
│ 🏋 Completed Upper body · Fitness · yesterday                   │
│ ⭐ Completed Take bins out · Meridian · Monday                  │
│ 🛋 Added desk option to Bedroom plan · Homestead · last week    │
│                                                        Open →   │
└──────────────────────────────────────────────────────────────────┘
```

### Overview

Avatar, preferred name, colour and a small non-sensitive summary; recent activity; nearest active
assignments; recent personal/room/wish items. Profile biography/status fields are optional later.
Do not show login role, date of birth, administrative notes, PIN/password state or private totals.

### Activity

A reverse-chronological, paginated feed of meaningful actions, not every database edit. Initial
view is the latest 30 days, followed by an explicit **Load more** action. Initial
providers should include:

- Fitness sessions completed and household-visible personal bests.
- Meridian tasks/routines completed, rewards received, badges earned and wishlist milestones.
- Atlas list/to-do items added or completed by the person.
- Homestead room-plan items/products added, chosen, purchased or completed.
- Later nodes may contribute their own deliberately safe activity summaries.

Every row carries a human verb, timestamp, source node, icon/colour and stable source link. The
primary action opens the exact source record, not merely the node landing page: a completed Fitness
session, the relevant list/item, room plan entry, reward or other authoritative detail. Providers
may also return a bounded, permission-safe expandable summary. For Fitness this is the completed
session snapshot (workout name, duration, exercises and completed sets/reps/weight/time/distance),
not the program template, because a live session may have been changed. Notifications generated
from the same activity carry the same deep link and may expose the same safe expansion after a
fresh visibility check. A row
appears only when the viewer can see both the node and its source record. Private Fitness, Health,
finance, sensitive attachments and protected notes must never become visible merely because the
subject has a Corner. Source deletion/removal removes the projection.

### Assigned

One active-work view contributed by enabled nodes: Meridian tasks/routines, Fitness programs,
Atlas list items/reminders, Education work, Homestead room-plan items and future Project tasks.
Group by **Due soon**, **No date** and source, with source links and only the small actions that the
owning node explicitly exposes. Completed/archived work belongs in Activity, not the active list.
“Created by this person” and “assigned to this person” are distinct filters and labels.

### Lists & wishes

Present several source-owned collections together without copying records:

- **Personal** — the person's Atlas shopping/wish lists. Add `owner_person` to `AtlasList` and a
  `wishlist` list type. Default these lists to household-visible, matching the owner's request
  that others can see them, while retaining a Private option.
- **Room plans** — Homestead room-plan items/products assigned to the person, labelled with the
  room and plan item that owns them.
- **Meridian wishes** — the existing child request → approval → point saving → fulfilment
  workflow. It remains Meridian-owned and appears here as a projection, including its progress
  only where the viewer already has permission.
- **Shopping** — the person's active owned/assigned Atlas shopping items, suitable for using in
  a shop. This is not a second cart or purchase ledger.

Adults can therefore keep a normal, point-free personal wish list in Atlas. A child's Meridian
wishlist remains the points/reward workflow; it is displayed here rather than duplicated into an
Atlas record.

### Household interaction

Keep interaction useful and attached to visible records rather than creating a general social
network or private messaging system:

- **Suggest an item** — another household member may propose a product for someone's personal
  shopping/wish list. The owner sees who suggested it and may accept (with edits), dismiss or
  leave it pending. Suggestions never silently alter the owner's list.
- **React/encourage (owner-approved)** — every visible activity row has a quick reaction control.
  Start with a friendly fixed set such as ❤️, 👍, 🎉, 💪 and 👏, plus an emoji-picker route to a
  broader safe set if the fixed choices prove too limiting. Reactions group by emoji with counts;
  an authorised viewer may open the group to see which household members reacted. One reaction of
  each emoji per person is allowed, tapping it again removes it, and a person may use more than
  one different emoji. Reactions are encouragement, not Meridian points, leaderboard score or
  task approval.
- **Comment** — short household comments on visible activity and list/wish items. Authors can edit
  or delete their own comment; the profile subject can hide comments from their space; managers
  can moderate. Do not allow attachments or rich HTML initially.
- **Offer to help** — on eligible assigned work, another person may offer help or request to join.
  The current assignee/author accepts before the owning node changes assignment. Never silently
  take or complete somebody else's work.
- **Watch a list or wish** — subscribe to meaningful changes or price-drop notifications without
  becoming an editor. Bundle notifications so ordinary activity cannot become noisy.

An optional later **gift reservation** could let another adult mark “I’m getting this” while
hiding that reservation from the wish owner and showing it to other eligible adults. This needs a
specific child/privacy design and is not part of the first interaction slice. Do not add pokes,
public follower counts, competitive engagement metrics or household direct messages.

## 3. Interaction ownership

List suggestions belong with the Atlas list/item workflow because accepting one creates an Atlas
item. Reactions/comments may use a small shared household-scoped interaction model with a stable
source node/type/id, author Person and target Person. Before every read or write, resolve the
source through its provider and prove the viewer can still see it. Source deletion/visibility
change must hide or clean up its interactions. Interactions notify the profile subject/source
owner through the shared Notifications service, excluding self-actions and bundling bursts. A
single notification may say “Alex and 2 others reacted to your workout”; it deep-links to the
activity instead of emitting one alert per emoji. Removing a reaction does not notify.

## 4. Aggregation architecture

Do not make `people` import every node model and do not copy all source records into a new social
table. Add a small provider registry, following the existing Hub/search pattern. Enabled nodes
may register permission-aware providers such as:

```text
get_person_activity(viewer, person, cursor, filters)
get_person_assignments(viewer, person)
get_person_collections(viewer, person)
```

Providers return a normalised projection (`key`, `kind`, `title`, `summary`, `occurred_at`,
`source_node`, `source_record_type`, `source_record_id`, `action_url`, optional `detail_summary`,
display metadata). The
source record remains authoritative. Merge/sort/paginate at the aggregation boundary and apply a
per-provider limit so one noisy node cannot dominate. If durable notification/event history later
proves insufficient for a desired activity, add a narrowly scoped activity projection consumer;
do not treat signals alone as permanent history.

Suggested read APIs:

- `GET /api/v1/corners/{personId}/?days=30` — bounded header, activity, assignments and collections.
- `POST /api/v1/corners/{personId}/reactions/` — toggle a permitted reaction after visibility re-check.

Writes continue through the owning node APIs. The Corner frontend may open an owning form
or issue an explicitly supported source action, but it never creates an alternative write path.

## 5. Identity, permissions and privacy

- Resolve creator activity from `created_by`/`completed_by` User to its linked Person; assignments
  continue to use explicit Person relations.
- The subject being household-visible does not make all of their records household-visible.
- Apply node access and record visibility before normalising, not after combining results.
- A person sees their own permitted private records; other members see household-visible records;
  managers/admins do not automatically bypass sensitive-node or re-authentication contracts.
- Child profiles omit administrative details and use the existing child/kiosk permission rules.
- Do not publish competitive rankings by default. This is a useful household history, not an
  engagement feed, surveillance log or performance score.

## 6. Delivery slices

1. **Person shell and overview:** household directory, stable route, profile header, node-provider
   registry and visibility-contract tests.
2. **Assigned:** Meridian, Atlas, Fitness, Education and Homestead providers; due/source filters;
   links to authoritative records.
3. **Lists & wishes:** Atlas `owner_person` + `wishlist`, personal add/edit, Homestead projections
   and the existing Meridian wishlist projection.
4. **Activity:** bounded provider feeds, useful verbs, pagination/filtering and notification-safe
   source links; add other nodes only when each can define meaningful visible activity.
5. **Interaction:** suggestions and owner-approved emoji reactions first, then comments and
   offer-to-help approval;
   visibility re-checks, moderation, notification bundling and abuse/duplicate tests.
6. **Polish:** avatar links across the app, Hub “My Corner” shortcut, phone layout, empty states and
   partner/child acceptance.

## 7. Acceptance gate

Two adults and one child can open one another's Corners. They see only permitted activity,
all currently assigned work, and correctly labelled personal/room/Meridian collections. A child
wish is still one Meridian record; a room item is still one Homestead record. Renaming a person,
disabling a node, making a record private or deleting a source updates the space without stale or
leaked content. The workflow works on phone and laptop and does not expose account administration.
Another member can suggest an item without editing the list, the owner can accept/dismiss it, and
permitted reactions/comments/help offers notify without bypassing source visibility or assignment
approval.

## 8. Settled owner decisions (2026-08-11)

1. New personal wish/shopping lists default to **Household visible**, with Private available.
2. Activity defaults to the **latest 30 days**, with explicit loading of older activity.
3. Other people **suggest** items; they do not directly modify someone else's personal list.
4. Household members can react to visible activity with hearts, thumbs-up and other friendly
   emoji. Reactions are removable, grouped and notification-bundled.

The initial reaction set is ❤️ 👍 🎉 💪 👏. Comments, offer-to-help and hidden-from-recipient
gift reservation remain deliberately deferred.
