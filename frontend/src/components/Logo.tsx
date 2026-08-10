/**
 * The HomeStack brand marks.
 *
 * Three files, three jobs: the `mark` (the house) where space is tight or the name is already
 * written beside it, the `wordmark` where the name has to carry itself in a wide strip, and the
 * `lockup` for the one place per surface that introduces the app.
 *
 * Sources live in `brand/`; these are the derived web assets built by
 * `scripts/build_brand_assets.py`. Intrinsic width/height are declared so a logo never reflows
 * the header it sits in while it loads.
 */

type LogoVariant = 'mark' | 'wordmark' | 'lockup'

const ASSETS: Record<LogoVariant, { src: string; width: number; height: number }> = {
  // The 192px mark is the one the UI draws — `mark.png` (512) is kept for icons and installs.
  mark: { src: '/brand/mark-192.png', width: 192, height: 192 },
  wordmark: { src: '/brand/wordmark.png', width: 867, height: 160 },
  lockup: { src: '/brand/lockup.png', width: 710, height: 512 },
}

export function Logo({
  variant = 'mark',
  className = '',
  /**
   * Leave as-is where the word "HomeStack" is already on screen next to the logo — repeating it
   * makes a screen reader say the name twice. Pass a label where the logo is the only naming.
   */
  alt = '',
}: {
  variant?: LogoVariant
  className?: string
  alt?: string
}) {
  const asset = ASSETS[variant]
  return (
    <img
      src={asset.src}
      width={asset.width}
      height={asset.height}
      alt={alt}
      aria-hidden={alt ? undefined : true}
      decoding="async"
      className={className}
    />
  )
}
