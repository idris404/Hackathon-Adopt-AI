// Miroir de backend/app/constants/http.py : toutes les routes métier sont sous /api/v1.
// L'origine du backend change selon l'environnement : elle vient de VITE_API_URL (app/env.ts).
export const API_V1_PREFIX = '/api/v1'

// Chemins relatifs à API_V1_PREFIX. Miroir de backend/app/auth/router.py et users/router.py.
export const API_ENDPOINTS = {
  login: '/auth/login',
  logout: '/auth/logout',
  currentUser: '/users/me',
} as const

export const HTTP_STATUS_UNAUTHORIZED = 401
export const CONTENT_TYPE_HEADER = 'Content-Type'
export const JSON_CONTENT_TYPE = 'application/json'
