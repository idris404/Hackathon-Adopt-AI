import { env } from '../../app/env'
import { API_ENDPOINTS } from '../../constants/api'
import {
  CONSULTATION_DAY_OFFSET,
  GENDER_LABELS,
  MOCK_BLOOD_GROUP,
  MOCK_BLOOD_PRESSURE,
  MOCK_CONSULTATION_TIME,
  MOCK_CPRA_PERCENT,
  MOCK_DOPPLER,
  MOCK_HEMOGLOBIN,
  MOCK_PLANNED_LABS,
  MOCK_POSTOP_CREATININE,
  MOCK_POSTOP_DFG,
  MOCK_POSTOP_DIURESIS,
  MOCK_POSTOP_POTASSIUM,
  MOCK_POTASSIUM,
  MOCK_PREOP_CREATININE,
  MOCK_PREOP_DFG,
  MOCK_REFERRING_DOCTOR,
  MOCK_RENAL_ROWS,
  MOCK_TEMPERATURE,
  MOCK_TREATMENTS,
  POSTOP_DAY_OFFSET,
  PREOP_DAY_OFFSET,
} from '../../constants/patient-file'
import {
  patientSchema,
  syntheticPatientPageSchema,
  type PatientResponse,
  type SyntheticPatientResponse,
} from './schemas'
import { addDays, ageInYears, formatLongDate, formatShortDate, parseIsoDate } from '../../shared/utils/dates'

export { addDays, ageInYears, formatLongDate, formatShortDate }

export class SessionRequiredError extends Error {}

export class ApiRequestError extends Error {
  readonly status: number

  constructor(status: number) {
    super(`API ${status}`)
    this.status = status
  }
}

export class InvalidResponseError extends Error {}

const monthYear = new Intl.DateTimeFormat('fr-FR', { month: 'long', year: 'numeric' })

async function readJson(path: string): Promise<unknown> {
  const response = await fetch(`${env.VITE_API_URL}${path}`, { credentials: 'include' })
  if (response.status === 401) {
    throw new SessionRequiredError()
  }
  if (!response.ok) {
    throw new ApiRequestError(response.status)
  }
  return response.json() as Promise<unknown>
}

export async function getPatient(id: string): Promise<PatientResponse> {
  const parsed = patientSchema.safeParse(await readJson(API_ENDPOINTS.patient(id)))
  if (!parsed.success) {
    throw new InvalidResponseError()
  }
  return parsed.data
}

export async function getSyntheticPatient(id: string): Promise<SyntheticPatientResponse | null> {
  const parsed = syntheticPatientPageSchema.safeParse(await readJson(API_ENDPOINTS.patientSynthetic(id)))
  if (!parsed.success) {
    throw new InvalidResponseError()
  }
  return parsed.data.items[0] ?? null
}

export async function login(email: string, password: string): Promise<void> {
  const response = await fetch(`${env.VITE_API_URL}${API_ENDPOINTS.login}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!response.ok) {
    throw new ApiRequestError(response.status)
  }
}

export type PathwayStep = {
  index: number
  title: string
  dateLabel: string
  note: string | null
}

export type RenalRow = {
  dateLabel: string
  creatinine: string
  dfg: string
  diuresis: string
  emphasized: boolean
}

export type PatientFile = {
  fullName: string
  patientCode: string
  summary: string
  statusLabel: string
  graftDateLabel: string | null
  organLabel: string
  referringDoctor: string
  steps: PathwayStep[]
  disease: string | null
  dialysis: string | null
  donor: string | null
  preopDateLabel: string | null
  postopDateLabel: string | null
  consultationDateLabel: string | null
  renalRows: RenalRow[]
}

export function buildPatientFile(
  patient: PatientResponse,
  synthetic: SyntheticPatientResponse | null,
  today: Date,
): PatientFile {
  const birth = patient.birth
  const age = birth === null ? null : ageInYears(birth, today)
  const summaryParts = [
    patient.patient_id,
    `${GENDER_LABELS[patient.gender]}${age === null ? '' : `, ${age} ans`}`,
    birth === null ? null : `${patient.gender === 'M' ? 'Né' : 'Née'} le ${formatLongDate(birth)}`,
  ].filter((part) => part !== null)
  const graftDate = synthetic?.date_greffe_actuelle ?? null
  const preop = graftDate === null ? null : addDays(graftDate, PREOP_DAY_OFFSET)
  const postop = graftDate === null ? null : addDays(graftDate, POSTOP_DAY_OFFSET)
  const consultation = graftDate === null ? null : addDays(graftDate, CONSULTATION_DAY_OFFSET)

  return {
    fullName: `${patient.firstname} ${patient.lastname}`,
    patientCode: patient.patient_id,
    summary: summaryParts.join(' · '),
    statusLabel: synthetic?.statut_parcours ?? 'Identité',
    graftDateLabel: graftDate === null ? null : formatShortDate(graftDate),
    organLabel: 'Greffe rénale',
    referringDoctor: MOCK_REFERRING_DOCTOR,
    steps:
      graftDate === null || preop === null || postop === null || consultation === null
        ? []
        : [
            { index: 1, title: 'Bilan préopératoire', dateLabel: formatShortDate(preop), note: null },
            { index: 2, title: 'Greffe rénale', dateLabel: formatShortDate(graftDate), note: null },
            {
              index: 3,
              title: 'Suivi postopératoire',
              dateLabel: formatShortDate(postop),
              note: 'J+7',
            },
            {
              index: 4,
              title: 'Prochaine consultation',
              dateLabel: formatShortDate(consultation),
              note: 'J+10',
            },
          ],
    disease: synthetic?.maladie_renale_initiale ?? null,
    dialysis:
      synthetic === null
        ? null
        : synthetic.dialyse_date_debut === null
          ? synthetic.dialyse_type
          : `${synthetic.dialyse_type} depuis ${monthYear.format(parseIsoDate(synthetic.dialyse_date_debut))}`,
    donor: synthetic?.type_donneur ?? null,
    preopDateLabel: preop === null ? null : formatLongDate(preop),
    postopDateLabel: postop === null ? null : formatLongDate(postop),
    consultationDateLabel: consultation === null ? null : formatLongDate(consultation),
    renalRows:
      graftDate === null
        ? []
        : MOCK_RENAL_ROWS.map((row, index) => ({
            dateLabel: `${formatShortDate(addDays(graftDate, row.dayOffset))} · J+${row.dayOffset}`,
            creatinine: row.creatinine,
            dfg: row.dfg,
            diuresis: row.diuresis,
            emphasized: index === MOCK_RENAL_ROWS.length - 1,
          })),
  }
}

export const mockClinical = {
  bloodGroup: MOCK_BLOOD_GROUP,
  cpraPercent: MOCK_CPRA_PERCENT,
  preopCreatinine: MOCK_PREOP_CREATININE,
  preopDfg: MOCK_PREOP_DFG,
  potassium: MOCK_POTASSIUM,
  hemoglobin: MOCK_HEMOGLOBIN,
  postopCreatinine: MOCK_POSTOP_CREATININE,
  postopDfg: MOCK_POSTOP_DFG,
  postopDiuresis: MOCK_POSTOP_DIURESIS,
  bloodPressure: MOCK_BLOOD_PRESSURE,
  temperature: MOCK_TEMPERATURE,
  postopPotassium: MOCK_POSTOP_POTASSIUM,
  doppler: MOCK_DOPPLER,
  consultationTime: MOCK_CONSULTATION_TIME,
  plannedLabs: MOCK_PLANNED_LABS,
  treatments: MOCK_TREATMENTS,
}
