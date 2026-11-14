// Miroir de backend/app/constants/pagination.py. En cas d'écart, le backend a raison.
export const DEFAULT_PAGE_SIZE = 20
export const MAX_PAGE_SIZE = 100
export const PAGE_SIZE_OPTIONS = [10, DEFAULT_PAGE_SIZE, 50, MAX_PAGE_SIZE] as const
