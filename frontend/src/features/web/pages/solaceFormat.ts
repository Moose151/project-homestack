let currencySymbol = '$'

export function setSolaceCurrencySymbol(value: string) {
  currencySymbol = value.trim() || '$'
}

export function solaceMoney(value: string | number): string {
  const numeric = Number(value || 0)
  const sign = numeric < 0 ? '-' : ''
  const amount = Math.abs(numeric).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  return `${sign}${currencySymbol}${amount}`
}
