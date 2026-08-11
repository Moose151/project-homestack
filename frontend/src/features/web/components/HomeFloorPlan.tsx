import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { RoomArea } from '../../../api/types'
import { Button } from '../../../components/Button'

type PlanArea = {
  key: string
  label: string
  sublabel?: string
  aliases: string[]
  shape: 'rect' | 'path'
  x?: number
  y?: number
  width?: number
  height?: number
  d?: string
  labelX: number
  labelY: number
  kind?: 'room' | 'wet' | 'outdoor' | 'utility'
}

const normalise = (value: string) => value.toLowerCase().replace(/[^a-z0-9]/g, '')

/**
 * A clean vector redraw of the supplied plans. The listing images remain reference material;
 * this is deliberately native SVG so it inherits HomeStack colours, works in dark mode and can
 * link the drawing to stable room pages without shipping real-estate branding into the product.
 */
const AREAS: PlanArea[] = [
  {
    key: 'pool', label: 'Pool', sublabel: 'Outdoor', aliases: ['pool', 'swimming pool'],
    shape: 'path', d: 'M82 76 C132 38 235 50 278 84 C326 122 318 184 270 204 C228 222 218 266 166 252 C132 244 122 211 86 204 C42 195 34 112 82 76Z',
    labelX: 176, labelY: 143, kind: 'outdoor',
  },
  { key: 'cabana', label: 'Cabana', sublabel: '3.0 × 3.0 m', aliases: ['cabana', 'pool cabana'], shape: 'rect', x: 38, y: 242, width: 112, height: 105, labelX: 94, labelY: 291, kind: 'outdoor' },
  { key: 'shed', label: 'Shed', sublabel: '4.0 × 6.0 m', aliases: ['shed', 'garden shed'], shape: 'rect', x: 148, y: 338, width: 142, height: 196, labelX: 219, labelY: 430, kind: 'utility' },

  { key: 'living', label: 'Family room', sublabel: '9.30 × 5.62 m', aliases: ['family room', 'familyroom', 'living', 'living room'], shape: 'rect', x: 440, y: 310, width: 250, height: 260, labelX: 565, labelY: 434 },
  { key: 'kitchen', label: 'Kitchen', sublabel: '3.32 × 2.82 m', aliases: ['kitchen'], shape: 'rect', x: 690, y: 445, width: 100, height: 125, labelX: 740, labelY: 504 },
  { key: 'dining', label: 'Dining', sublabel: '4.70 × 4.00 m', aliases: ['dining', 'dining room'], shape: 'rect', x: 790, y: 460, width: 85, height: 110, labelX: 832, labelY: 512 },
  { key: 'lounge', label: 'Lounge', aliases: ['lounge', 'sitting room'], shape: 'rect', x: 875, y: 460, width: 90, height: 110, labelX: 920, labelY: 518 },
  { key: 'master', label: 'Master bedroom', sublabel: '4.00 × 3.10 m', aliases: ['master bedroom', 'master', 'bedroom 1', 'bed 1'], shape: 'rect', x: 790, y: 570, width: 175, height: 110, labelX: 878, labelY: 621 },
  { key: 'ensuite', label: 'Ensuite', sublabel: '3.10 × 1.90 m', aliases: ['ensuite', 'ensuite bathroom'], shape: 'rect', x: 690, y: 570, width: 75, height: 110, labelX: 727, labelY: 621, kind: 'wet' },
  { key: 'wir', label: 'WIR', aliases: ['wir', 'walk in robe', 'walk-in robe', 'wardrobe'], shape: 'rect', x: 765, y: 570, width: 25, height: 110, labelX: 778, labelY: 627, kind: 'utility' },

  { key: 'bathroom', label: 'Bathroom', sublabel: '2.10 × 1.82 m', aliases: ['bathroom', 'bath', 'main bathroom'], shape: 'rect', x: 690, y: 370, width: 75, height: 75, labelX: 727, labelY: 404, kind: 'wet' },
  { key: 'laundry', label: 'Laundry', sublabel: '2.10 × 1.56 m', aliases: ['laundry', 'ldry'], shape: 'rect', x: 690, y: 310, width: 75, height: 60, labelX: 727, labelY: 339, kind: 'wet' },
  { key: 'bed4', label: 'Bedroom 4', sublabel: '3.01 × 2.50 m', aliases: ['bedroom 4', 'bed 4', 'fourth bedroom'], shape: 'rect', x: 690, y: 210, width: 120, height: 100, labelX: 750, labelY: 257 },
  { key: 'bed3', label: 'Bedroom 3', sublabel: '4.31 × 3.71 m', aliases: ['bedroom 3', 'bed 3', 'third bedroom'], shape: 'rect', x: 810, y: 210, width: 155, height: 130, labelX: 887, labelY: 271 },
  { key: 'bed2', label: 'Bedroom 2', sublabel: '3.50 × 2.71 m', aliases: ['bedroom 2', 'bed 2', 'second bedroom'], shape: 'rect', x: 810, y: 340, width: 155, height: 120, labelX: 887, labelY: 396 },
  { key: 'hall', label: 'Hall', aliases: ['hall', 'hallway', 'linen'], shape: 'rect', x: 765, y: 310, width: 45, height: 260, labelX: 787, labelY: 440, kind: 'utility' },
  { key: 'verandah', label: 'Verandah', sublabel: '7.00 × 1.90 m', aliases: ['verandah', 'porch', 'patio'], shape: 'rect', x: 965, y: 460, width: 65, height: 110, labelX: 997, labelY: 512, kind: 'outdoor' },
  { key: 'carport', label: 'Carport', sublabel: '6.42 × 6.00 m', aliases: ['carport', 'garage'], shape: 'rect', x: 965, y: 210, width: 197, height: 250, labelX: 1063, labelY: 329, kind: 'outdoor' },
]

const fillFor = (area: PlanArea, room?: RoomArea) => {
  if (room?.colour?.startsWith('#')) return `${room.colour}24`
  if (area.kind === 'wet') return 'var(--hs-primary-soft)'
  if (area.kind === 'outdoor') return 'var(--hs-success-soft)'
  if (area.kind === 'utility') return 'var(--hs-surface-muted)'
  return 'var(--hs-surface)'
}

export function HomeFloorPlan({ rooms }: { rooms: RoomArea[] }) {
  const navigate = useNavigate()
  const [zoom, setZoom] = useState(1)
  const roomByArea = useMemo(() => {
    const result = new Map<string, RoomArea>()
    for (const area of AREAS) {
      const aliases = new Set(area.aliases.map(normalise))
      const room = rooms.find(candidate => aliases.has(normalise(candidate.name)))
      if (room) result.set(area.key, room)
    }
    return result
  }, [rooms])
  const linkedCount = roomByArea.size

  const open = (area: PlanArea) => {
    const room = roomByArea.get(area.key)
    if (room) navigate(`/homestead/rooms/${room.id}`)
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-soft">
      <div className="flex flex-col gap-3 border-b border-line px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="font-bold text-ink">Our home</h3>
          <p className="text-sm text-muted">Tap a highlighted space to open its room plan · {linkedCount} linked</p>
        </div>
        <div className="flex items-center gap-2" aria-label="Floor plan zoom">
          <Button size="sm" variant="ghost" onClick={() => setZoom(value => Math.max(0.8, value - 0.2))} disabled={zoom <= 0.8} aria-label="Zoom floor plan out">−</Button>
          <span className="min-w-12 text-center text-xs font-semibold text-muted">{Math.round(zoom * 100)}%</span>
          <Button size="sm" variant="ghost" onClick={() => setZoom(value => Math.min(1.8, value + 0.2))} disabled={zoom >= 1.8} aria-label="Zoom floor plan in">+</Button>
        </div>
      </div>
      <div className="overflow-auto bg-paper-soft p-3 sm:p-5">
        <svg
          viewBox="0 0 1200 720"
          role="img"
          aria-labelledby="home-floorplan-title home-floorplan-description"
          className="mx-auto block h-auto transition-[width] duration-200"
          style={{ width: `${zoom * 100}%`, minWidth: zoom <= 1 ? 700 : undefined }}
        >
          <title id="home-floorplan-title">Interactive floor plan of our home</title>
          <desc id="home-floorplan-description">House, bedrooms, living spaces, pool, cabana, shed, verandah and carport. Linked rooms can be opened.</desc>
          <defs>
            <pattern id="plan-grid" width="18" height="18" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="18" stroke="var(--hs-border)" strokeWidth="1" />
            </pattern>
            <filter id="plan-shadow" x="-10%" y="-10%" width="120%" height="130%">
              <feDropShadow dx="0" dy="5" stdDeviation="7" floodColor="#000" floodOpacity="0.08" />
            </filter>
          </defs>

          <path d="M18 28 H346 V310 L298 338 H148 L18 294 Z" fill="var(--hs-success-soft)" stroke="var(--hs-border-strong)" strokeWidth="2" strokeDasharray="7 7" />
          <text x="32" y="52" fill="var(--hs-muted)" fontSize="13" fontWeight="700" letterSpacing="1.5">POOL &amp; YARD</text>
          <path d="M404 180 Q404 166 418 166 H1092 Q1106 166 1106 180 V694 H404 Z" fill="var(--hs-bg-soft)" stroke="var(--hs-border)" strokeWidth="2" filter="url(#plan-shadow)" />
          <text x="421" y="194" fill="var(--hs-muted)" fontSize="12" fontWeight="700" letterSpacing="1.4">HOUSE</text>
          <path d="M920 462 H1162 V678 H920 Z" fill="url(#plan-grid)" opacity="0.65" />

          {AREAS.map(area => {
            const room = roomByArea.get(area.key)
            const interactive = Boolean(room)
            const common = {
              fill: fillFor(area, room),
              stroke: room?.colour || 'var(--hs-border-strong)',
              strokeWidth: room ? 3 : 2,
              vectorEffect: 'non-scaling-stroke' as const,
            }
            return (
              <g
                key={area.key}
                role={interactive ? 'link' : undefined}
                tabIndex={interactive ? 0 : undefined}
                aria-label={interactive ? `Open ${room!.name}` : `${area.label}, not linked to a room page`}
                onClick={() => open(area)}
                onKeyDown={event => {
                  if (interactive && (event.key === 'Enter' || event.key === ' ')) {
                    event.preventDefault()
                    open(area)
                  }
                }}
                className={interactive ? 'group cursor-pointer outline-none' : ''}
              >
                <title>{interactive ? `Open ${room!.name}` : `${area.label} — add a matching room to link it`}</title>
                {area.shape === 'rect' ? (
                  <rect x={area.x} y={area.y} width={area.width} height={area.height} rx="5" {...common} className={interactive ? 'transition-all group-hover:brightness-95 group-focus:stroke-[5]' : ''} />
                ) : (
                  <path d={area.d} {...common} className={interactive ? 'transition-all group-hover:brightness-95 group-focus:stroke-[5]' : ''} />
                )}
                <text x={area.labelX} y={area.labelY - (area.sublabel ? 7 : 0)} textAnchor="middle" fill="var(--hs-text)" fontSize={area.key === 'hall' ? 11 : 13} fontWeight="750" pointerEvents="none">
                  {room?.icon ? `${room.icon} ` : ''}{area.label}
                </text>
                {area.sublabel && (
                  <text x={area.labelX} y={area.labelY + 12} textAnchor="middle" fill="var(--hs-muted)" fontSize="10.5" pointerEvents="none">{area.sublabel}</text>
                )}
                {room && <circle cx={(area.x ?? area.labelX) + 12} cy={(area.y ?? area.labelY) + 12} r="4" fill={room.colour || 'var(--hs-primary)'} pointerEvents="none" />}
              </g>
            )
          })}

          <g transform="translate(1128 54)" aria-label="North points to the upper left">
            <path d="M0 45 L18 0 L36 45 L18 34 Z" fill="var(--hs-accent-homestead)" />
            <text x="18" y="61" textAnchor="middle" fill="var(--hs-muted)" fontSize="12" fontWeight="800">N</text>
          </g>
        </svg>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-2 border-t border-line px-4 py-3 text-xs text-muted">
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border-2 border-primary bg-primary-soft" /> Linked room</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border border-line-strong bg-surface" /> Plan reference</span>
        <span className="ml-auto">Approximate layout · not for construction</span>
      </div>
    </div>
  )
}
