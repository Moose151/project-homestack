import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../../api/client'
import type { RoomArea } from '../../../api/types'
import { Button } from '../../../components/Button'
import { confirmDialog } from '../../../components/Dialogs'
import { Select } from '../../../components/Field'

type PlanMode = 'inside' | 'property'
type AreaKind = 'room' | 'wet' | 'outdoor' | 'utility'
type PlanArea = {
  key: string
  label: string
  sublabel?: string
  aliases: string[]
  mode: PlanMode
  shape: 'rect' | 'path'
  x?: number
  y?: number
  width?: number
  height?: number
  d?: string
  labelX: number
  labelY: number
  kind?: AreaKind
}
type AreaMatch = { room: RoomArea; explicit: boolean }

const normalise = (value: string) => value.toLowerCase().replace(/[^a-z0-9]/g, '')
const slotFor = (room: RoomArea) => (
  typeof room.floorplan_data?.floorplan_slot === 'string'
    ? room.floorplan_data.floorplan_slot
    : ''
)

/**
 * A native redraw of the supplied plans. The listing images remain reference material: SVG
 * gives the app a coherent light/dark surface and stable interactive regions without embedding
 * real-estate branding or turning the room map into an unresponsive image.
 */
const AREAS: PlanArea[] = [
  { key: 'living', label: 'Family room', sublabel: '9.30 × 5.62 m', aliases: ['family room', 'familyroom', 'living', 'living room'], mode: 'inside', shape: 'rect', x: 440, y: 310, width: 250, height: 260, labelX: 565, labelY: 434 },
  { key: 'kitchen', label: 'Kitchen', sublabel: '3.32 × 2.82 m', aliases: ['kitchen'], mode: 'inside', shape: 'rect', x: 690, y: 445, width: 75, height: 125, labelX: 727, labelY: 504 },
  { key: 'dining', label: 'Dining', sublabel: '4.70 × 4.00 m', aliases: ['dining', 'dining room'], mode: 'inside', shape: 'rect', x: 765, y: 460, width: 110, height: 110, labelX: 820, labelY: 512 },
  { key: 'lounge', label: 'Lounge', aliases: ['lounge', 'sitting room'], mode: 'inside', shape: 'rect', x: 875, y: 460, width: 90, height: 110, labelX: 920, labelY: 518 },
  { key: 'master', label: 'Master bedroom', sublabel: '4.00 × 3.10 m', aliases: ['master bedroom', 'master', 'bedroom 1', 'bed 1'], mode: 'inside', shape: 'rect', x: 790, y: 570, width: 175, height: 110, labelX: 878, labelY: 621 },
  { key: 'ensuite', label: 'Ensuite', sublabel: '3.10 × 1.90 m', aliases: ['ensuite', 'ensuite bathroom'], mode: 'inside', shape: 'rect', x: 690, y: 570, width: 75, height: 110, labelX: 727, labelY: 621, kind: 'wet' },
  { key: 'wir', label: 'WIR', aliases: ['wir', 'walk in robe', 'walk-in robe', 'wardrobe'], mode: 'inside', shape: 'rect', x: 765, y: 570, width: 25, height: 110, labelX: 778, labelY: 627, kind: 'utility' },
  { key: 'bathroom', label: 'Bathroom', sublabel: '2.10 × 1.82 m', aliases: ['bathroom', 'bath', 'main bathroom'], mode: 'inside', shape: 'rect', x: 690, y: 370, width: 75, height: 75, labelX: 727, labelY: 404, kind: 'wet' },
  { key: 'laundry', label: 'Laundry', sublabel: '2.10 × 1.56 m', aliases: ['laundry', 'ldry'], mode: 'inside', shape: 'rect', x: 690, y: 310, width: 75, height: 60, labelX: 727, labelY: 339, kind: 'wet' },
  { key: 'bed4', label: 'Bedroom 4', sublabel: '3.01 × 2.50 m', aliases: ['bedroom 4', 'bed 4', 'fourth bedroom'], mode: 'inside', shape: 'rect', x: 690, y: 210, width: 120, height: 100, labelX: 750, labelY: 257 },
  { key: 'bed3', label: 'Bedroom 3', sublabel: '4.31 × 3.71 m', aliases: ['bedroom 3', 'bed 3', 'third bedroom'], mode: 'inside', shape: 'rect', x: 810, y: 210, width: 155, height: 130, labelX: 887, labelY: 271 },
  { key: 'bed2', label: 'Bedroom 2', sublabel: '3.50 × 2.71 m', aliases: ['bedroom 2', 'bed 2', 'second bedroom'], mode: 'inside', shape: 'rect', x: 810, y: 340, width: 155, height: 120, labelX: 887, labelY: 396 },
  { key: 'hall', label: 'Hall', aliases: ['hall', 'hallway', 'linen'], mode: 'inside', shape: 'rect', x: 765, y: 310, width: 45, height: 150, labelX: 787, labelY: 385, kind: 'utility' },
  { key: 'verandah', label: 'Verandah', sublabel: '7.00 × 1.90 m', aliases: ['verandah', 'porch', 'patio'], mode: 'inside', shape: 'rect', x: 965, y: 460, width: 65, height: 110, labelX: 997, labelY: 512, kind: 'outdoor' },

  { key: 'pool', label: 'Pool', sublabel: 'Outdoor', aliases: ['pool', 'swimming pool'], mode: 'property', shape: 'path', d: 'M116 96 C178 50 300 65 348 108 C398 152 380 232 322 252 C270 271 264 319 204 302 C164 290 153 254 110 245 C58 232 58 140 116 96Z', labelX: 226, labelY: 176, kind: 'outdoor' },
  { key: 'cabana', label: 'Cabana', sublabel: '3.0 × 3.0 m', aliases: ['cabana', 'pool cabana'], mode: 'property', shape: 'rect', x: 54, y: 290, width: 120, height: 108, labelX: 114, labelY: 340, kind: 'outdoor' },
  { key: 'shed', label: 'Shed', sublabel: '4.0 × 6.0 m', aliases: ['shed', 'garden shed'], mode: 'property', shape: 'rect', x: 176, y: 390, width: 156, height: 208, labelX: 254, labelY: 487, kind: 'utility' },
  { key: 'carport', label: 'Carport', sublabel: '6.42 × 6.00 m', aliases: ['carport', 'garage'], mode: 'property', shape: 'rect', x: 888, y: 218, width: 238, height: 272, labelX: 1007, labelY: 347, kind: 'outdoor' },
]

const insideAreas = AREAS.filter(area => area.mode === 'inside')
const propertyAreas = AREAS.filter(area => area.mode === 'property')

const fillFor = (area: PlanArea, room?: RoomArea, selected = false) => {
  if (selected) return 'var(--hs-primary-soft)'
  if (room?.colour?.startsWith('#')) return `${room.colour}1f`
  if (area.kind === 'wet') return 'color-mix(in srgb, var(--hs-primary-soft) 65%, var(--hs-surface))'
  if (area.kind === 'outdoor') return 'color-mix(in srgb, var(--hs-success-soft) 72%, var(--hs-surface))'
  if (area.kind === 'utility') return 'var(--hs-surface-muted)'
  return 'var(--hs-surface)'
}

function linkMap(rooms: RoomArea[]): Map<string, AreaMatch> {
  const result = new Map<string, AreaMatch>()
  const explicitlyPlaced = new Set<number>()
  for (const room of rooms) {
    const slot = slotFor(room)
    if (slot && AREAS.some(area => area.key === slot)) {
      result.set(slot, { room, explicit: true })
      explicitlyPlaced.add(room.id)
    }
  }
  for (const area of AREAS) {
    if (result.has(area.key)) continue
    const aliases = new Set(area.aliases.map(normalise))
    const room = rooms.find(candidate => (
      !explicitlyPlaced.has(candidate.id) && aliases.has(normalise(candidate.name))
    ))
    if (room) result.set(area.key, { room, explicit: false })
  }
  return result
}

function AreaShape({
  area,
  match,
  selected,
  onSelect,
}: {
  area: PlanArea
  match?: AreaMatch
  selected: boolean
  onSelect: () => void
}) {
  const room = match?.room
  const label = room?.name || area.label
  const common = {
    fill: fillFor(area, room, selected),
    stroke: selected ? 'var(--hs-primary)' : room?.colour || 'var(--hs-border-strong)',
    strokeWidth: selected ? 4 : room ? 2.5 : 1.6,
    vectorEffect: 'non-scaling-stroke' as const,
    filter: selected ? 'url(#selected-room-glow)' : undefined,
  }
  const compact = ['wir', 'hall'].includes(area.key)
  return (
    <g
      role="button"
      tabIndex={0}
      aria-label={`Select ${label}${match ? ', linked to a room page' : ', not linked'}`}
      aria-pressed={selected}
      onClick={onSelect}
      onKeyDown={event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onSelect()
        }
      }}
      className="group cursor-pointer outline-none"
    >
      <title>{`Select ${label}`}</title>
      {area.shape === 'rect' ? (
        <rect x={area.x} y={area.y} width={area.width} height={area.height} {...common} className="transition-all group-hover:brightness-95 group-focus:stroke-[4]" />
      ) : (
        <path d={area.d} {...common} className="transition-all group-hover:brightness-95 group-focus:stroke-[4]" />
      )}
      <text x={area.labelX} y={area.labelY - (area.sublabel ? 7 : 0)} textAnchor="middle" fill="var(--hs-text)" fontSize={compact ? 10 : 13} fontWeight="750" pointerEvents="none">
        {room?.icon ? `${room.icon} ` : ''}{label}
      </text>
      {area.sublabel && !compact && (
        <text x={area.labelX} y={area.labelY + 12} textAnchor="middle" fill="var(--hs-muted)" fontSize="10.5" pointerEvents="none">{area.sublabel}</text>
      )}
      {match?.explicit && (
        <circle cx={(area.x ?? area.labelX) + 10} cy={(area.y ?? area.labelY) + 10} r="4" fill={room?.colour || 'var(--hs-primary)'} pointerEvents="none" />
      )}
    </g>
  )
}

function DoorAndWindowDetails() {
  return (
    <g pointerEvents="none" fill="none">
      {/* Calm architectural cues: openings break the shared wall; arcs show the door swing. */}
      <g stroke="var(--hs-surface)" strokeWidth="7">
        <line x1="690" y1="476" x2="690" y2="507" />
        <line x1="810" y1="300" x2="842" y2="300" />
        <line x1="810" y1="430" x2="842" y2="430" />
        <line x1="790" y1="592" x2="790" y2="623" />
        <line x1="965" y1="490" x2="965" y2="522" />
      </g>
      <g stroke="var(--hs-muted)" strokeWidth="1.4" opacity="0.72">
        <path d="M690 507 A31 31 0 0 1 721 476" />
        <path d="M810 300 A32 32 0 0 1 842 268" />
        <path d="M810 430 A32 32 0 0 1 842 398" />
        <path d="M790 623 A31 31 0 0 1 821 592" />
        <path d="M965 522 A32 32 0 0 1 997 490" />
      </g>
      <g stroke="var(--hs-primary)" strokeWidth="4" opacity="0.42">
        <line x1="488" y1="570" x2="548" y2="570" />
        <line x1="852" y1="210" x2="918" y2="210" />
        <line x1="965" y1="365" x2="965" y2="420" />
        <line x1="840" y1="680" x2="916" y2="680" />
      </g>
    </g>
  )
}

export function HomeFloorPlan({
  rooms,
  canEdit,
  onRoomsChanged,
  onError,
  fullScreen = false,
}: {
  rooms: RoomArea[]
  canEdit: boolean
  onRoomsChanged: () => Promise<unknown>
  onError: (message: string) => void
  fullScreen?: boolean
}) {
  const navigate = useNavigate()
  const [mode, setMode] = useState<PlanMode>('inside')
  const [selectedKey, setSelectedKey] = useState('living')
  const [zoom, setZoom] = useState(1)
  const [chosenRoomId, setChosenRoomId] = useState('')
  const [saving, setSaving] = useState(false)
  const matches = useMemo(() => linkMap(rooms), [rooms])
  const selectedArea = AREAS.find(area => area.key === selectedKey && area.mode === mode)
  const selectedMatch = selectedArea ? matches.get(selectedArea.key) : undefined
  const savedCount = [...matches.values()].filter(match => match.explicit).length
  const suggestedCount = [...matches.values()].filter(match => !match.explicit).length
  const visibleAreas = mode === 'inside' ? insideAreas : propertyAreas

  useEffect(() => {
    setChosenRoomId(selectedMatch?.room.id.toString() || '')
  }, [selectedKey, selectedMatch?.room.id])

  const selectArea = (area: PlanArea) => {
    setSelectedKey(area.key)
    setChosenRoomId(matches.get(area.key)?.room.id.toString() || '')
  }
  const changeMode = (next: PlanMode) => {
    setMode(next)
    setZoom(1)
    const first = next === 'inside' ? insideAreas[0] : propertyAreas[0]
    setSelectedKey(first.key)
    setChosenRoomId(matches.get(first.key)?.room.id.toString() || '')
  }

  const saveLink = async () => {
    if (!selectedArea || !chosenRoomId) return
    const room = rooms.find(candidate => candidate.id === Number(chosenRoomId))
    if (!room) return
    setSaving(true)
    try {
      const updates: Promise<unknown>[] = []
      for (const existing of rooms) {
        if (existing.id !== room.id && slotFor(existing) === selectedArea.key) {
          const nextData = { ...existing.floorplan_data }
          delete nextData.floorplan_slot
          updates.push(api.updateRoom(existing.id, { floorplan_data: nextData }))
        }
      }
      updates.push(api.updateRoom(room.id, {
        floorplan_data: { ...room.floorplan_data, floorplan_slot: selectedArea.key },
      }))
      await Promise.all(updates)
      await onRoomsChanged()
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Could not link that room.')
    } finally {
      setSaving(false)
    }
  }

  const unlink = async () => {
    if (!selectedMatch?.explicit) return
    if (!(await confirmDialog({
      title: `Unlink ${selectedMatch.room.name} from this space?`,
      message: 'The room and its plan stay in HomeStack; only its position on the floor plan is removed.',
      confirmLabel: 'Unlink room',
    }))) return
    setSaving(true)
    try {
      const nextData = { ...selectedMatch.room.floorplan_data }
      delete nextData.floorplan_slot
      await api.updateRoom(selectedMatch.room.id, { floorplan_data: nextData })
      setChosenRoomId('')
      await onRoomsChanged()
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Could not unlink that room.')
    } finally {
      setSaving(false)
    }
  }

  const viewBox = mode === 'inside' ? '420 185 630 520' : '20 34 1135 600'
  const minWidth = mode === 'inside' ? 680 : 760

  return (
    <div
      data-floor-plan-viewer={fullScreen ? 'fullscreen' : 'inline'}
      className={`overflow-hidden border border-line bg-surface shadow-soft ${fullScreen ? 'flex h-full min-h-0 flex-col rounded-xl' : 'rounded-2xl'}`}
    >
      <div className="flex flex-col gap-3 border-b border-line px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 className="font-bold text-ink">Home</h3>
          <p className="text-sm text-muted">Select a space to highlight, link or open it · {savedCount} saved{suggestedCount ? ` · ${suggestedCount} suggested` : ''}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-xl border border-line bg-sunken/70 p-1" aria-label="Floor plan view">
            {([
              ['inside', 'Inside the house'],
              ['property', 'Whole property'],
            ] as const).map(([key, label]) => (
              <button key={key} type="button" onClick={() => changeMode(key)} className={`min-h-9 rounded-lg px-3 text-xs font-semibold transition ${mode === key ? 'bg-raised text-ink shadow-soft' : 'text-muted hover:text-ink'}`}>{label}</button>
            ))}
          </div>
          <Button size="sm" variant="ghost" onClick={() => setZoom(1)} disabled={zoom === 1}>Fit</Button>
          <Button size="sm" variant="ghost" onClick={() => setZoom(value => Math.max(0.8, value - 0.2))} disabled={zoom <= 0.8} aria-label="Zoom floor plan out">−</Button>
          <Button size="sm" variant="ghost" onClick={() => setZoom(value => Math.min(1.8, value + 0.2))} disabled={zoom >= 1.8} aria-label="Zoom floor plan in">+</Button>
        </div>
      </div>

      <div className={`grid lg:grid-cols-[minmax(0,1fr)_280px] ${fullScreen ? 'min-h-0 flex-1 overflow-y-auto' : ''}`}>
        <div className={`overflow-auto bg-paper-soft p-3 sm:p-5 ${fullScreen ? 'min-h-[48dvh] lg:min-h-0' : ''}`}>
          <svg
            viewBox={viewBox}
            role="img"
            aria-labelledby="home-floorplan-title home-floorplan-description"
            className="mx-auto block h-auto transition-[width] duration-200"
            style={{ width: `${zoom * 100}%`, minWidth }}
          >
            <title id="home-floorplan-title">Interactive floor plan of our home</title>
            <desc id="home-floorplan-description">Choose Inside the house or Whole property, then select an area to highlight and link it to a Homestead room.</desc>
            <defs>
              <pattern id="plan-paving" width="18" height="18" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <line x1="0" y1="0" x2="0" y2="18" stroke="var(--hs-border)" strokeWidth="1" />
              </pattern>
              <filter id="selected-room-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="2" stdDeviation="5" floodColor="var(--hs-primary)" floodOpacity="0.32" />
              </filter>
            </defs>

            {mode === 'inside' ? (
              <>
                <path d="M440 310 H690 V210 H965 V460 H1030 V570 H965 V680 H690 V570 H440 Z" fill="var(--hs-bg-soft)" stroke="var(--hs-text)" strokeWidth="5" vectorEffect="non-scaling-stroke" />
                {visibleAreas.map(area => <AreaShape key={area.key} area={area} match={matches.get(area.key)} selected={selectedKey === area.key} onSelect={() => selectArea(area)} />)}
                <DoorAndWindowDetails />
              </>
            ) : (
              <>
                <path d="M38 58 H406 V338 L338 382 H176 L38 330 Z" fill="var(--hs-success-soft)" stroke="var(--hs-border-strong)" strokeWidth="2" strokeDasharray="7 7" />
                <path d="M414 190 H888 V218 H1126 V490 H1030 V570 H965 V606 H690 V570 H414 Z" fill="var(--hs-surface)" stroke="var(--hs-text)" strokeWidth="4" vectorEffect="non-scaling-stroke" />
                <path d="M888 218 H1126 V490 H888 Z" fill="url(#plan-paving)" opacity="0.55" />
                <text x="650" y="375" textAnchor="middle" fill="var(--hs-text)" fontSize="22" fontWeight="800">House</text>
                <text x="650" y="402" textAnchor="middle" fill="var(--hs-muted)" fontSize="13">Choose “Inside the house” for rooms</text>
                {visibleAreas.map(area => <AreaShape key={area.key} area={area} match={matches.get(area.key)} selected={selectedKey === area.key} onSelect={() => selectArea(area)} />)}
                <g transform="translate(1090 62)" aria-label="North points to the upper left">
                  <path d="M0 45 L18 0 L36 45 L18 34 Z" fill="var(--hs-accent-homestead)" />
                  <text x="18" y="61" textAnchor="middle" fill="var(--hs-muted)" fontSize="12" fontWeight="800">N</text>
                </g>
              </>
            )}
          </svg>
        </div>

        <aside className="border-t border-line bg-surface p-4 lg:border-l lg:border-t-0" aria-live="polite">
          {selectedArea ? (
            <div className="flex h-full flex-col gap-4">
              <div>
                <p className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-muted">Selected space</p>
                <div className="mt-2 flex items-start gap-3">
                  <div className="flex h-11 w-11 flex-none items-center justify-center rounded-xl bg-primary-soft text-xl">{selectedMatch?.room.icon || (selectedArea.kind === 'outdoor' ? '🌿' : '🚪')}</div>
                  <div className="min-w-0">
                    <h4 className="font-bold text-ink">{selectedMatch?.room.name || selectedArea.label}</h4>
                    <p className="text-xs text-muted">{selectedArea.sublabel || 'Plan reference'}</p>
                    {selectedMatch && <p className="mt-1 text-xs font-semibold text-primary">{selectedMatch.explicit ? 'Linked room' : 'Suggested from its name'}</p>}
                  </div>
                </div>
              </div>

              {selectedMatch && (
                <Button variant="secondary" size="sm" onClick={() => navigate(`/homestead/rooms/${selectedMatch.room.id}`)}>Open room plan →</Button>
              )}

              {canEdit && (
                <div className="mt-auto border-t border-line pt-4">
                  <label className="text-xs font-semibold text-muted-strong" htmlFor="floorplan-room-link">Link to existing room</label>
                  <Select id="floorplan-room-link" className="mt-1.5" value={chosenRoomId} onChange={event => setChosenRoomId(event.target.value)}>
                    <option value="">Choose a room…</option>
                    {rooms.map(room => <option key={room.id} value={room.id}>{room.name}{slotFor(room) && slotFor(room) !== selectedArea.key ? ' · currently elsewhere' : ''}</option>)}
                  </Select>
                  <p className="mt-2 text-xs text-muted">The plan will adopt that room’s saved name, icon and colour.</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button size="sm" onClick={saveLink} loading={saving} disabled={!chosenRoomId}>Save link</Button>
                    {selectedMatch?.explicit && <Button size="sm" variant="ghost" onClick={unlink} disabled={saving}>Unlink</Button>}
                  </div>
                </div>
              )}
            </div>
          ) : <p className="text-sm text-muted">Select a space on the plan.</p>}
        </aside>
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-2 border-t border-line px-4 py-3 text-xs text-muted">
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border-2 border-primary bg-primary-soft" /> Selected</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border border-line-strong bg-surface" /> Selectable space</span>
        <span className="ml-auto">Approximate layout · not for construction</span>
      </div>
    </div>
  )
}
