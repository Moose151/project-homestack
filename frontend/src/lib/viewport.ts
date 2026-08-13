/**
 * Non-reactive: read once, e.g. inside a `useState` lazy initializer, to pick a sensible
 * mobile-vs-desktop starting value (a default view, a default layout mode). Matches the `sm:`
 * (640px) breakpoint already used inline throughout pages for their own mobile/desktop split —
 * not the app shell's `md:` (768px) bottom-nav breakpoint, a pre-existing inconsistency between
 * the two that this doesn't attempt to resolve.
 *
 * Deliberately not a hook: a page's initial view choice shouldn't flip mid-session just because
 * the window resized (e.g. a tablet rotating), so nothing here re-renders on resize.
 */
export const isPhoneViewport = () => typeof window !== 'undefined' && window.innerWidth < 640
