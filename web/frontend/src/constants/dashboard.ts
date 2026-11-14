import { PAGE_SIZE_OPTIONS } from './pagination'

export const DASHBOARD_PAGE_SIZE = PAGE_SIZE_OPTIONS[0]
export const DASHBOARD_SEARCH_DEBOUNCE_MS = 300

export const PATIENT_SORT_FIELDS = ['patient_id', 'lastname', 'birth', 'gender', 'city'] as const
export const SORT_ORDERS = ['asc', 'desc'] as const
export const DEFAULT_PATIENT_SORT = 'lastname' as const
export const DEFAULT_SORT_ORDER = 'asc' as const

export const dashboardKeys = {
  all: ['dashboard'] as const,
  patients: (query: {
    search: string
    gender: 'M' | 'F' | null
    page: number
    pageSize: number
    sortBy: string
    sortOrder: string
  }) => ['dashboard', 'patients', query] as const,
}

export const DASHBOARD_ERRORS = {
  session: 'Une session est requise pour afficher la liste.',
  invalid: 'La réponse du serveur est invalide.',
  unavailable: 'La liste des patients est indisponible pour le moment.',
} as const

// Chiffres de la maquette, absents de la base.
export const MOCK_KPI = {
  waiting: 128,
  waitingNote: 'En attente d’un greffon rénal',
  toValidate: 12,
  toValidateNote: '4 reçus aujourd’hui',
  doubtful: 5,
  doubtfulNote: 'À examiner en priorité',
  upToDate: 111,
  upToDateNote: '86,7 % des patients',
} as const
