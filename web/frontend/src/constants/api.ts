// Miroir de backend/app/constants/http.py : toutes les routes métier sont sous /api/v1.
// L'origine du backend change selon l'environnement : elle vient de VITE_API_URL (app/env.ts).
export const API_V1_PREFIX = '/api/v1'

export const API_ENDPOINTS = {
  login: `${API_V1_PREFIX}/auth/login`,
  patient: (id: string) => `${API_V1_PREFIX}/patients/${id}`,
  patientSynthetic: (id: string) => `${API_V1_PREFIX}/patients/${id}/synthetic-patients`,
} as const
