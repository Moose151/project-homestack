# 39 — Quick Launch

Personal shortcuts to the places a person actually goes, without walking the tree every time.

---

## 1. Purpose

HomeStack's navigation is broad by design: a node, then a tab, then a list, then the thing. That
is right for finding something, and wrong for the fifteenth time you open the same grocery list
this week.

Quick Launch is shared infrastructure — not a Lists & Notes feature. Nodes advertise the
destinations they consider safe to point at, and Quick Launch does the rest: storage, ordering,
authorisation, resolution and failure handling, once, for all of them.

---

## 2. Three navigation systems, deliberately distinct

| | What it is | Whose | Scope |
| --- | --- | --- | --- |
| **Desktop sidebar** | Normal navigation | Everyone's | Node roots |
| **Mobile bottom nav** | Two configurable dock slots | Per user | Node roots |
| **Quick Launch** | Personal shortcuts | Per user | May point **deeper** than a node root |

They do not share storage and must not overwrite each other. The dock's `mobile_nav` preference
is a pair of node keys; a Quick Launch shortcut is a row that can name one particular list, room
or screen. Collapsing the two would make the dock unable to express "Groceries" and Quick Launch
unable to express "the two things I tap most".

---

## 3. Terminology

- **Target** — a registered destination (`core.calendar`, `atlas.list`). Defined in code.
- **Shortcut** — one person's saved instance of a target, optionally naming a record.
- **Resolution** — what a shortcut means *right now*: `ok`, `locked` or `unavailable`.
- **Launch** — following `/launch/<uuid>`, which resolves and then navigates.

---

## 4. Target registry

`apps/quicklaunch/registry.py` + `targets.py`.

Each `Target` declares:

| Field | Purpose |
| --- | --- |
| `key` | stable identifier, e.g. `atlas.list` |
| `label` / `description` / `icon` | what the picker shows |
| `node_key` | owning node, or `""` for a core surface |
| `target_type` | `open` or `action` |
| `route(user, obj)` | builds the destination **at launch time** |
| `requires_object` | whether a record must be chosen |
| `list_objects(user)` / `get_object(user, id)` | the node's own selectors |
| `sensitive` | whether the node sits behind the re-auth gate |
| `launch_modes` | which modes this destination supports |
| `extra_available(user)` | any further availability rule |

Two properties matter above all:

**A shortcut stores intent, not a route.** No field can hold a path or a URL. The client sends a
registered key; this module decides what that means. Internal routes can therefore change without
breaking saved shortcuts, and there is nowhere to smuggle `/admin/` or an external address.

**A shortcut grants nothing.** Availability is evaluated per user at launch, and object-backed
targets re-fetch through the node's own selectors, so household scoping and visibility remain the
node's rules rather than a second copy that could drift.

Adding a target is one entry in `targets.py`. No change to the model, the API, the UI or the
launch route.

---

## 5. Persistence — a model, not the preference store

`quicklaunch.QuickLaunchShortcut`: `public_id` (UUID), `user`, `target_key`,
`target_object_id`, `custom_label`, `display_order`, `launch_mode`.

The generic `UserPreference` JSON store was considered and rejected. Its own contract is that its
values are ordering hints and "never authority", and its validators accept only capped lists of
slugs. A shortcut carries a referenced object id, a user-authored label, a launch mode and a UUID
that appears in a URL and must be authorised per user — relational data behind an authorisation
boundary. It gets a row.

(The desktop **sidebar collapse** flag went the other way, into `UserPreference`, because it
genuinely is a single presentation boolean. Same reasoning, opposite answer.)

Limits: 20 shortcuts per person; label 60 characters; one shortcut per (target, object).

---

## 6. Launch contract

```
/launch/<public_id>
```

The client resolves, then obeys:

1. identify the shortcut — **scoped to the requesting user in the lookup itself**;
2. check the target still exists in the registry;
3. check availability (node enabled, permission held);
4. re-fetch the referenced record through the node's selectors;
5. check the sensitive gate;
6. build and return the current canonical route.

`GET /api/v1/quick-launch/shortcuts/<uuid>/resolve/` answers `ok` (with `route`), `locked` (with
`route`, so the destination survives the unlock) or `unavailable` (**no route at all**).

Because the route is produced rather than stored, a bookmark or a home-screen tile keeps working
across internal route changes.

---

## 7. Security model

A shortcut is a faster route, never extra access. Opening one still enforces authentication, the
household boundary, node-enabled state, the user's permission, record visibility and the
sensitive re-auth gate.

- **Ownership is part of the lookup**, not a check afterwards, so a forged or altered UUID
  produces the same "not found" as one that never existed.
- **Someone else's identifier and an unknown one answer identically** — a different response
  would itself confirm that a shortcut exists.
- **A deleted record and an inaccessible one answer identically**, for the same reason, and the
  failure never echoes the record's name.
- Losing a permission, or the household disabling a node, makes existing shortcuts
  `unavailable` immediately. Nothing is cached.

### Sensitive destinations

Money resolves to `locked` while the household's re-authentication prompt is outstanding. The
client shows *Unlock and continue*, which navigates to the **intended destination** — the node's
own gate then prompts, and the user lands where they asked to go, not on a node root.

---

## 8. Launch modes

`normal` and `focused` are stored per shortcut and returned by the resolver.

**Focused mode ships as a contract, not yet as a visual mode.** The resolver returns
`launch_mode`, and the launch page appends `focus=1` when a shortcut asks for it, so the
plumbing and the stored intent exist. Simplifying the shell itself is deliberately deferred: the
brief allows it, and doing it properly means auditing every page's chrome rather than adding a
second shell. Any page may honour `focus=1` when it is ready; nothing depends on it today.

---

## 9. Management UI

**Settings → Quick Launch**, plus an entry in the phone More sheet.

Add (from the registry's catalogue only), rename, reorder, remove, open. Reordering uses
Move up / Move down buttons — identical with a finger, a mouse and a keyboard, unlike a drag
target. Unavailable shortcuts are shown greyed with their reason and cannot be opened.

There is no default shortcut set: HomeStack's precedent is that a person's arrangement starts
empty and they choose. A default pointing at a node someone cannot open would be worse than none.

---

## 10. Initial targets

| Area | Targets |
| --- | --- |
| Core | Dashboard, Calendar |
| Lists & Notes | node home, Grocery, To-dos, **a specific Lists & Notes list**, **a specific to-do list** |
| Tasks | node home, Task list |
| Money | node home, Upcoming bills *(sensitive)* |
| Home | node home, **a specific room** |
| Fitness | **Log run** *(action)* |

Each names a route contract the page already honours. User-facing product names only — `atlas`,
`meridian`, `solace` and `homestead` appear as `node_key` for grouping and colour, never as text.

The Atlas entries track Atlas's own tabs, which is not automatic: Quick Launch was built against
the pre-v0.40 Atlas, and its "Reminders" target went on resolving to `/atlas?tab=reminders` after
that tab was retired. Because a shortcut resolves to a route rather than storing one, the failure
was silent — the user simply landed on the default tab. `atlas.reminders` is therefore gone, and
`_list_tab()` in `targets.py` mirrors `listTabFor()` in `AtlasPage.tsx`. A test asserts that no
registered Atlas destination points at a tab the page does not have.

An object-backed target with nothing to point at is withheld from the picker rather than offered
as a dead end.

---

## 11. Unavailable targets

Deleted record, disabled node, withdrawn permission, or a target removed in a later release all
produce the same friendly state:

> **This shortcut is no longer available.**
> [Remove shortcut] [Back to HomeStack]

Never a crash, never a silent fallback to something unrelated, never a disclosure of what the
record was. A *temporarily* locked destination is not this: it uses the unlock flow instead.

---

## 12. PWA and platform reality

The manifest (`frontend/public/manifest.json`) is a static file with no `shortcuts` member, and
the service worker does not participate in navigation targets.

What is true today:

- **Manifest `shortcuts`** are static and build-time. They cannot be personalised per user, and
  support is partial — Chromium on Android and desktop honour them; iOS Safari does not.
- **Dynamic per-user home-screen icons are not available cross-platform.** iOS offers no API;
  "Add to Home Screen" bookmarks a URL, which is a manual user action, not something HomeStack
  can install.
- `navigator.setAppBadge`, Web Share Target and shortcut APIs vary widely and none of them
  provide per-user installed tiles.

So **no OS integration ships here, and none is claimed.** What ships is the thing every future
integration would need anyway: a stable, authorised `/launch/<uuid>` URL. A user can already
bookmark one or add it to their home screen manually. QR codes, NFC tags, Home Assistant buttons
and widgets are all just "something that opens a URL" — they become possible without further
Quick Launch work, and none of them are in scope now.

---

## 13. Future action targets

`target_type: "action"` exists and **Log run** uses it. The rule is that an action target opens a
bounded form — it never performs the action. Opening the Log run shortcut creates nothing; the
user still presses Save.

Candidates for later: new to-do, add grocery item, new task, new calendar event. Each must be
explicitly registered, obey normal permissions, and stay behind re-auth where the node is
sensitive. This is not, and must not become, a generic automation engine.

---

## 14. Extending

1. Add a `Target` to `apps/quicklaunch/targets.py` naming an existing stable route.
2. For an object-backed target, point `list_objects`/`get_object` at the node's own selectors.
3. Add a jurisdiction-style test proving an inaccessible record resolves to `unavailable`.

Nothing else changes.
