// Nom du segment dynamique de ROUTES.fiche : l'identifiant du patient (UUID, jamais son patient_id).
export const FICHE_ID_PARAM = 'id'

export const ROUTES = {
  login: '/',
  dashboard: '/dashboard',
  fiche: `/fiche/:${FICHE_ID_PARAM}`,
  toSign: '/a-signer',
} as const
