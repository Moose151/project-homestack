/**
 * Pure helpers for rendering multi-day Calendar events as continuous bars (TimeTree-style month
 * view): turning an event's start/end into the calendar days it touches, clipping that to one
 * week at a time, and packing overlapping events into stable lanes.
 */
import type { CalendarEvent } from '../api/types'

const DAY_MS = 24 * 60 * 60 * 1000

export const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate())
export const addDays = (d: Date, n: number) => { const x = new Date(d); x.setDate(x.getDate() + n); return x }

export type SpanLike = Pick<CalendarEvent, 'start_at' | 'end_at'>

/**
 * The inclusive calendar-day range an event visually occupies.
 *
 * An all-day event's `end_at` is stored as midnight of its *last included* day (the
 * DateTimeField picker's convention — picking "15 Nov" as the end stores 15 Nov 00:00, and that
 * day must still render as part of the event), so no adjustment is needed here: the start/end
 * dates are already the first/last days to show the bar on. A timed event with no end is
 * single-day; a timed event whose `end_at` falls on a later date spans every day between.
 */
export function eventDayRange(event: SpanLike): { start: Date; end: Date } {
  const start = startOfDay(new Date(event.start_at))
  if (!event.end_at) return { start, end: start }
  const end = startOfDay(new Date(event.end_at))
  return { start, end: end.getTime() < start.getTime() ? start : end }
}

export function eventOccursOnDay(event: SpanLike, day: Date): boolean {
  const { start, end } = eventDayRange(event)
  const t = startOfDay(day).getTime()
  return t >= start.getTime() && t <= end.getTime()
}

export interface WeekSegment<E> {
  key: string
  event: E
  /** 0-6, inclusive, within the given week. */
  startCol: number
  endCol: number
  /** The event's overall span starts before this week (flat/continuing left edge). */
  continuesBefore: boolean
  /** The event's overall span ends after this week (flat/continuing right edge). */
  continuesAfter: boolean
}

/**
 * Clip every event's day-range to one 7-day week and express it as 0-6 column indices, so a
 * multi-day event becomes one segment per week it touches — breaking at the week boundary and
 * continuing as its own segment on the next row.
 */
export function buildWeekSegments<E extends SpanLike & { id: number }>(
  events: E[],
  weekDays: Date[],
): WeekSegment<E>[] {
  const weekStart = startOfDay(weekDays[0])
  const weekEnd = startOfDay(weekDays[weekDays.length - 1])
  const segments: WeekSegment<E>[] = []
  for (const event of events) {
    const { start, end } = eventDayRange(event)
    if (end.getTime() < weekStart.getTime() || start.getTime() > weekEnd.getTime()) continue
    const clippedStart = start.getTime() < weekStart.getTime() ? weekStart : start
    const clippedEnd = end.getTime() > weekEnd.getTime() ? weekEnd : end
    segments.push({
      key: `${event.id}-${weekStart.toDateString()}`,
      event,
      startCol: Math.round((clippedStart.getTime() - weekStart.getTime()) / DAY_MS),
      endCol: Math.round((clippedEnd.getTime() - weekStart.getTime()) / DAY_MS),
      continuesBefore: start.getTime() < weekStart.getTime(),
      continuesAfter: end.getTime() > weekEnd.getTime(),
    })
  }
  return segments
}

export interface LanedSegment<E> extends WeekSegment<E> {
  lane: number
}

/**
 * Deterministic greedy interval-graph colouring: segments are placed left-to-right, each taking
 * the first lane whose last occupant finished before this one starts. `laneMemory` (event id ->
 * lane) is read and mutated in place, so calling this once per week of a month in order lets a
 * continuing multi-day event keep the same visual row across weeks wherever that lane is free.
 */
export function assignLanes<E extends { id: number }>(
  segments: WeekSegment<E>[],
  laneMemory: Map<number, number> = new Map(),
): LanedSegment<E>[] {
  const ordered = [...segments].sort((a, b) =>
    a.startCol - b.startCol || (b.endCol - b.startCol) - (a.endCol - a.startCol))
  const laneLastCol: number[] = []
  const free = (lane: number, col: number) => (laneLastCol[lane] ?? -Infinity) < col
  const placed: LanedSegment<E>[] = []
  for (const segment of ordered) {
    const preferred = laneMemory.get(segment.event.id)
    let lane = preferred !== undefined && free(preferred, segment.startCol) ? preferred : -1
    if (lane === -1) {
      lane = laneLastCol.findIndex((_, i) => free(i, segment.startCol))
      if (lane === -1) lane = laneLastCol.length
    }
    laneLastCol[lane] = segment.endCol
    laneMemory.set(segment.event.id, lane)
    placed.push({ ...segment, lane })
  }
  return placed
}

/** How many segments are hidden (lane >= cap) over a given day column — drives "+N more". */
export function hiddenCountForColumn<E>(laned: LanedSegment<E>[], col: number, cap: number): number {
  let count = 0
  for (const segment of laned) {
    if (segment.lane >= cap && col >= segment.startCol && col <= segment.endCol) count++
  }
  return count
}
