interface Props {
  name: string
  colour?: string
  /** Account picture: an emoji (e.g. "🦊") or an image URL/path. Empty → initials. */
  avatar?: string
  size?: 'sm' | 'md' | 'lg'
}

const sizes = { sm: 'w-8 h-8 text-xs', md: 'w-10 h-10 text-sm', lg: 'w-14 h-14 text-lg' }
const emojiSizes = { sm: 'text-base', md: 'text-xl', lg: 'text-3xl' }

/** True when the avatar string is an image URL/path rather than an emoji/text. */
export function isImageAvatar(avatar: string): boolean {
  const s = avatar.trim()
  return s.startsWith('http') || s.includes('/') || /\.(png|jpe?g|gif|webp|svg)$/i.test(s)
}

export function Avatar({ name, colour = '#4A90E2', avatar = '', size = 'md' }: Props) {
  const trimmed = avatar.trim()

  if (trimmed && isImageAvatar(trimmed)) {
    return <img src={trimmed} alt={name} className={`${sizes[size]} rounded-full object-cover flex-shrink-0`} />
  }

  if (trimmed) {
    return (
      <div
        className={`${sizes[size]} ${emojiSizes[size]} rounded-full flex items-center justify-center flex-shrink-0`}
        style={{ backgroundColor: colour + '33' }}
        aria-label={name}
      >
        {trimmed}
      </div>
    )
  }

  const initials = name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
  return (
    <div
      className={`${sizes[size]} rounded-full flex items-center justify-center font-semibold text-white flex-shrink-0`}
      style={{ backgroundColor: colour }}
    >
      {initials}
    </div>
  )
}
