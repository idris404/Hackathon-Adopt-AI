// Décalages du parcours autour de la date de greffe réelle.
export const PREOP_DAY_OFFSET = -1
export const POSTOP_DAY_OFFSET = 7
export const CONSULTATION_DAY_OFFSET = 10
export const RENAL_FOLLOW_UP_DAY_OFFSETS = [1, 3, 7] as const

export const GENDER_LABELS = {
  M: 'Homme',
  F: 'Femme',
} as const

export const patientFileKeys = {
  all: ['patient-file'] as const,
  patient: (id: string) => ['patient-file', 'patient', id] as const,
  synthetic: (id: string) => ['patient-file', 'synthetic', id] as const,
}

export const PATIENT_FILE_ERRORS = {
  session: 'Une session est requise pour ouvrir le dossier.',
  notFound: 'Ce patient est introuvable.',
  invalid: 'La réponse du serveur est invalide.',
  unavailable: 'Le dossier est indisponible pour le moment.',
  credentials: 'Email ou mot de passe incorrect.',
} as const

// Chiffres et libellés de la maquette, absents de la base. Affichés comme exemples fictifs.
export const MOCK_REFERRING_DOCTOR = 'Dr Camille Laurent'
export const MOCK_BLOOD_GROUP = 'A+'
export const MOCK_CPRA_PERCENT = 12
export const MOCK_PREOP_CREATININE = 712
export const MOCK_PREOP_DFG = 6
export const MOCK_POTASSIUM = '4,8 mmol/L'
export const MOCK_HEMOGLOBIN = '10,6 g/dL'
export const MOCK_POSTOP_CREATININE = 138
export const MOCK_POSTOP_DFG = 41
export const MOCK_POSTOP_DIURESIS = '2 200'
export const MOCK_BLOOD_PRESSURE = '128/78 mmHg'
export const MOCK_TEMPERATURE = '36,8 °C'
export const MOCK_POSTOP_POTASSIUM = '4,2 mmol/L'
export const MOCK_DOPPLER = 'Perfusion conservée'
export const MOCK_CONSULTATION_TIME = '09:00'
export const MOCK_PLANNED_LABS = 'créatinine, ionogramme, NFS et tacrolimus C0'
export const MOCK_NAV_COUNTS = {
  patients: 128,
  validation: 12,
  doubtful: 5,
} as const

export const MOCK_RENAL_ROWS = [
  { dayOffset: RENAL_FOLLOW_UP_DAY_OFFSETS[0], creatinine: '486 µmol/L', dfg: '9 mL/min/1,73 m²', diuresis: '1 250 mL/24 h' },
  { dayOffset: RENAL_FOLLOW_UP_DAY_OFFSETS[1], creatinine: '268 µmol/L', dfg: '19 mL/min/1,73 m²', diuresis: '1 850 mL/24 h' },
  { dayOffset: RENAL_FOLLOW_UP_DAY_OFFSETS[2], creatinine: '138 µmol/L', dfg: '41 mL/min/1,73 m²', diuresis: '2 200 mL/24 h' },
] as const

export const MOCK_TREATMENTS = [
  { name: 'Tacrolimus', detail: 'Suivi pharmacologique C0' },
  { name: 'Mycophénolate mofétil', detail: 'Immunosuppression d’entretien' },
  { name: 'Corticothérapie', detail: 'Selon prescription en cours' },
] as const
