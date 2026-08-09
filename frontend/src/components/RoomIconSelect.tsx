import { ROOM_ICONS, ROOM_ICON_GROUPS } from '../config/roomIcons'

/**
 * Pick a room icon from a named list instead of typing an emoji.
 *
 * Grouped by the kind of space so the list is scannable, and an icon already saved that is not
 * on the list is kept as its own option rather than being silently replaced.
 */
export function RoomIconSelect({
  value,
  onChange,
  className = '',
  id,
}: {
  value: string
  onChange: (icon: string) => void
  className?: string
  id?: string
}) {
  const known = ROOM_ICONS.some(option => option.icon === value)

  return (
    <select
      id={id}
      value={value}
      onChange={event => onChange(event.target.value)}
      className={className || 'min-h-11 w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink'}
      aria-label="Room icon"
    >
      <option value="">No icon</option>
      {value && !known && <option value={value}>{value} (current)</option>}
      {ROOM_ICON_GROUPS.map(group => (
        <optgroup key={group.group} label={group.group}>
          {group.options.map(option => (
            <option key={option.icon} value={option.icon}>
              {option.icon}  {option.label}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  )
}
