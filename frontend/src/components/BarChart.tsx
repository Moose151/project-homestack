/**
 * A single-series column chart, built from ordinary elements so no charting library
 * (and no bundle weight) is needed for the handful of charts HomeStack shows.
 *
 * Deliberately one series and one measure: two measures on two scales in one frame is the
 * fastest way to make a chart lie, so two measures means two charts. Identity never rests on
 * colour alone — the latest column is emphasised *and* labelled, an estimated reading is
 * striped *and* named in the footnote, and every column is focusable with its full figures.
 */

export interface BarChartPoint {
  key: string | number
  /** Short axis label, e.g. "Apr–Jun 26". */
  label: string
  value: number
  /** The value written out, used for the tip label and the tooltip. */
  display: string
  /** Extra tooltip lines — the period, the total, whatever the axis cannot carry. */
  detail?: string[]
  /** Estimated rather than measured: striped, and called out under the chart. */
  hatched?: boolean
}

interface BarChartProps {
  points: BarChartPoint[]
  /** Describes the whole plot for screen readers, e.g. "Electricity used per day". */
  ariaLabel: string
  /** Named under the chart when any column is striped. */
  hatchLabel?: string
  className?: string
}

const PLOT_HEIGHT = 130
// Room above the tallest column for its value label, so a full-height bar never collides with
// whatever sits above the chart.
const LABEL_HEADROOM = 20
// Stripes for an estimated read: 45°, tone-on-tone, so it reads as texture rather than a
// second colour that would imply a second series.
const HATCH = 'repeating-linear-gradient(45deg, transparent 0 5px, rgba(255,255,255,0.45) 5px 10px)'

export function BarChart({ points, ariaLabel, hatchLabel, className = '' }: BarChartProps) {
  if (points.length === 0) return null

  const max = Math.max(...points.map(point => point.value), 0)
  const lastIndex = points.length - 1
  const anyHatched = points.some(point => point.hatched)

  return (
    <figure className={`m-0 ${className}`}>
      <div className="relative" style={{ paddingTop: LABEL_HEADROOM }}>
        {/* Recessive hairlines at the top, middle and baseline — enough to read height by. */}
        <div
          className="pointer-events-none absolute inset-x-0 flex flex-col justify-between"
          style={{ top: LABEL_HEADROOM, height: PLOT_HEIGHT }}
          aria-hidden
        >
          <div className="border-t border-line" />
          <div className="border-t border-line" />
          <div className="border-t border-line" />
        </div>

        <div className="flex items-end gap-1 sm:gap-2" role="img" aria-label={ariaLabel}>
          {points.map((point, index) => {
            const share = max > 0 ? (point.value / max) * 100 : 0
            const isLatest = index === lastIndex
            // Keep the tooltip inside the card at both ends instead of letting it clip.
            const anchor = points.length > 2 && index === 0
              ? 'left-0'
              : points.length > 2 && index === lastIndex
                ? 'right-0'
                : 'left-1/2 -translate-x-1/2'
            return (
              <div key={point.key} className="group relative flex min-w-0 flex-1 flex-col items-center">
                <div
                  className="relative flex w-full items-end justify-center rounded-t-lg focus-within:bg-primary-soft"
                  style={{ height: PLOT_HEIGHT }}
                >
                  <button type="button" className="flex h-full w-full max-w-[24px] items-end justify-center">
                    <span
                      className="block w-full rounded-t"
                      style={{
                        height: `${share}%`,
                        minHeight: point.value > 0 ? 3 : 0,
                        backgroundColor: 'var(--hs-primary)',
                        // The story is where usage is now, so older periods are context.
                        opacity: isLatest ? 1 : 0.42,
                        backgroundImage: point.hatched ? HATCH : undefined,
                      }}
                    />
                    <span className="sr-only">
                      {point.label}: {point.display}
                      {point.detail?.length ? `. ${point.detail.join('. ')}` : ''}
                      {point.hatched && hatchLabel ? `. ${hatchLabel}` : ''}
                    </span>
                  </button>

                  {/* One direct label, on the period the reader is actually asking about. */}
                  {isLatest && (
                    <span
                      className="pointer-events-none absolute left-1/2 -translate-x-1/2 whitespace-nowrap text-[11px] font-semibold text-ink"
                      style={{ bottom: Math.max((share / 100) * PLOT_HEIGHT, 3) + 4 }}
                    >
                      {point.display}
                    </span>
                  )}
                </div>

                <span className="mt-1.5 w-full truncate text-center text-[11px] text-muted">
                  {point.label}
                </span>

                {/* Visual only — the same figures are already in the button's label. */}
                <div
                  aria-hidden
                  className={`pointer-events-none absolute bottom-full z-10 mb-1 hidden w-max max-w-[12rem] rounded-xl border border-line bg-raised px-3 py-2 text-left text-xs shadow-card group-hover:block group-focus-within:block ${anchor}`}
                >
                  <p className="font-semibold text-ink">{point.label}</p>
                  <p className="text-muted-strong">{point.display}</p>
                  {point.detail?.map(line => (
                    <p key={line} className="text-muted">{line}</p>
                  ))}
                  {point.hatched && hatchLabel && <p className="text-muted">{hatchLabel}</p>}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {anyHatched && hatchLabel && (
        <figcaption className="mt-2 flex items-center gap-2 text-xs text-muted">
          <span
            className="h-3 w-3 flex-shrink-0 rounded-sm"
            style={{ backgroundColor: 'var(--hs-primary)', opacity: 0.42, backgroundImage: HATCH }}
            aria-hidden
          />
          {hatchLabel}
        </figcaption>
      )}
    </figure>
  )
}
