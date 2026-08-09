/**
 * Icons offered when naming a room or area.
 *
 * Typing an emoji by hand meant knowing one existed and finding it on your keyboard, so most
 * rooms ended up unmarked. Grouped by the same area types the room form already uses, and kept
 * generic — these are rooms any household might have, not this one's (D15).
 */
export interface RoomIconOption {
  icon: string
  label: string
}

export const ROOM_ICON_GROUPS: { group: string; options: RoomIconOption[] }[] = [
  {
    group: 'Living',
    options: [
      { icon: '🛋️', label: 'Living room' },
      { icon: '📺', label: 'Lounge / TV room' },
      { icon: '🍽️', label: 'Dining room' },
      { icon: '🍳', label: 'Kitchen' },
      { icon: '🚪', label: 'Hallway / entry' },
      { icon: '🪜', label: 'Stairs / landing' },
    ],
  },
  {
    group: 'Sleeping & bathing',
    options: [
      { icon: '🛏️', label: 'Bedroom' },
      { icon: '🧸', label: "Child's room" },
      { icon: '👶', label: 'Nursery' },
      { icon: '🛁', label: 'Bathroom' },
      { icon: '🚿', label: 'Shower room' },
      { icon: '🚽', label: 'Toilet / cloakroom' },
    ],
  },
  {
    group: 'Work & hobbies',
    options: [
      { icon: '💻', label: 'Office / study' },
      { icon: '📚', label: 'Library / reading room' },
      { icon: '🎮', label: 'Games room' },
      { icon: '🎵', label: 'Music room' },
      { icon: '🏋️', label: 'Gym' },
      { icon: '🧰', label: 'Workshop' },
    ],
  },
  {
    group: 'Utility & storage',
    options: [
      { icon: '🧺', label: 'Laundry / utility' },
      { icon: '🧹', label: 'Cleaning cupboard' },
      { icon: '🥫', label: 'Pantry' },
      { icon: '📦', label: 'Storage' },
      { icon: '🪣', label: 'Boiler / plant room' },
      { icon: '🕳️', label: 'Loft / basement' },
    ],
  },
  {
    group: 'Outside',
    options: [
      { icon: '🌳', label: 'Garden' },
      { icon: '🪴', label: 'Patio / balcony' },
      { icon: '🚗', label: 'Garage' },
      { icon: '🛖', label: 'Shed / outbuilding' },
      { icon: '🚲', label: 'Bike store' },
      { icon: '🏡', label: 'Whole property' },
    ],
  },
]

/** Flat lookup so a saved icon can be named back, and to detect a custom one. */
export const ROOM_ICONS: RoomIconOption[] = ROOM_ICON_GROUPS.flatMap(group => group.options)

export const DEFAULT_ROOM_ICON = '🛋️'
