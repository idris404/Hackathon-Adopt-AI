const shortDate = new Intl.DateTimeFormat('fr-FR', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

const longDate = new Intl.DateTimeFormat('fr-FR', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
})

export function parseIsoDate(isoDate: string): Date {
  const [year, month, day] = isoDate.split('-').map(Number)
  return new Date(year ?? 0, (month ?? 1) - 1, day ?? 1)
}

export function addDays(isoDate: string, days: number): string {
  const date = parseIsoDate(isoDate)
  date.setDate(date.getDate() + days)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function ageInYears(birthIso: string, today: Date): number {
  const birth = parseIsoDate(birthIso)
  let age = today.getFullYear() - birth.getFullYear()
  const monthDelta = today.getMonth() - birth.getMonth()
  if (monthDelta < 0 || (monthDelta === 0 && today.getDate() < birth.getDate())) {
    age -= 1
  }
  return age
}

export function formatShortDate(isoDate: string): string {
  return shortDate.format(parseIsoDate(isoDate))
}

export function formatLongDate(isoDate: string): string {
  return longDate.format(parseIsoDate(isoDate))
}
