export const signKeys = {
  all: ['signatures'] as const,
  queue: ['signatures', 'queue'] as const,
}

// Code stable renvoyé par POST /signatures (backend/app/constants/signatures.py).
export const PATIENT_ALREADY_SIGNED_CODE = 'PATIENT_ALREADY_SIGNED'

export const TO_SIGN_ERRORS = {
  queue: 'La file des cas à signer est indisponible pour le moment.',
  invalid: 'La réponse du serveur est invalide.',
  alreadySigned: 'Ce cas a déjà été signé.',
  sign: 'La signature n’a pas pu être enregistrée. Réessayez.',
} as const

// Indicateurs de l'algorithme, absents de la base.
export const MOCK_SIGN_KPI = {
  yesterday: 18,
  yesterdayNote: 'Cas simples traités hier',
  week: 94,
  weekNote: 'Depuis lundi',
  agreement: '97 %',
  agreementNote: 'Validés sans correction cette semaine',
  reviewTime: '1 min 40',
  reviewTimeNote: 'Temps moyen de relecture',
} as const
