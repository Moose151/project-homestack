# Brand assets

The HomeStack logo, in three pieces. These files are the **sources** — full-size renders with
transparent backgrounds and a soft glow around the artwork. Nothing here is loaded by the app.

| File | What it is | Where it is used |
|------|------------|------------------|
| `homestack-mark-source.png` | The house with the stack inside it | Sidebar header, kiosk ambient screen, favicon and app icons |
| `homestack-wordmark-source.png` | The name on its own | Kiosk ambient screen, beside the mark |
| `homestack-lockup-source.png` | Mark above the name | The sign-in screen — the one place per surface that introduces the app |

## Regenerating the web assets

The app loads the smaller, cropped versions in `frontend/public/brand/`, which are committed.
Rebuild them after replacing any source file:

```bash
python3 scripts/build_brand_assets.py   # needs Pillow
```

That crops each source to its artwork (the canvas around it is mostly empty, and a 1 MB file to
draw a 36px logo is not a trade worth making), resizes it, and writes `mark.png`, `mark-192.png`,
`wordmark.png`, `lockup.png`, `apple-touch-icon.png` and `favicon-32.png`.

## Notes for whoever changes these

- **Both themes matter.** Check any replacement against the warm paper background *and* the dark
  surface — the app has a light/dark toggle and the kiosk has its own. The current wordmark comes
  in two treatments: the standalone file is light-toned for dark backgrounds, while the one baked
  into the lockup is darker for light backgrounds. The lockup is used in both themes today; its
  navy "Home" is a little quiet on dark.
- **Transparency is deliberate**, except for the Apple touch icon — iOS fills a transparent
  home-screen icon with black, so that one is drawn on the app's paper colour.
- Sizes and alt text live in one place: `frontend/src/components/Logo.tsx`.
