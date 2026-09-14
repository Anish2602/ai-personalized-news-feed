export function relativeTime(iso: string | null): string {
  if (!iso) return 'unknown time'
  const then = new Date(iso).getTime()
  const diffSeconds = Math.max(0, (Date.now() - then) / 1000)

  const steps: [number, string][] = [
    [60, 'second'],
    [60, 'minute'],
    [24, 'hour'],
    [7, 'day'],
    [4.345, 'week'],
    [12, 'month'],
    [Number.POSITIVE_INFINITY, 'year'],
  ]

  let value = diffSeconds
  for (const [factor, unit] of steps) {
    if (value < factor) {
      const rounded = Math.max(1, Math.round(value))
      return `${rounded} ${unit}${rounded === 1 ? '' : 's'} ago`
    }
    value /= factor
  }
  return 'a while ago'
}
