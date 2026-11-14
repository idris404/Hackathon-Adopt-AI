import { API_ENDPOINTS } from '../../constants/api'
import { GENDER_LABELS } from '../../constants/patient-file'
import { InvalidResponseError, readJson } from '../../shared/api'
import { ageInYears, formatLongDate } from '../../shared/utils/dates'
import { buildFichePath } from '../../shared/utils/routes'
import { patientPageSchema, type ListQuery, type PatientListItem, type PatientPage } from './schemas'

export type PatientRow = {
  id: string
  patientId: string
  name: string
  detail: string
  city: string
  birthLabel: string
  href: string
}

export function toPatientRow(patient: PatientListItem, today: Date): PatientRow {
  const gender = GENDER_LABELS[patient.gender]
  const age = patient.birth === null ? null : ageInYears(patient.birth, today)
  return {
    id: patient.id,
    patientId: patient.patient_id,
    name: `${patient.firstname} ${patient.lastname}`,
    detail: age === null ? gender : `${age} ans · ${gender}`,
    city: patient.city,
    birthLabel: patient.birth === null ? 'Non renseignée' : formatLongDate(patient.birth),
    href: buildFichePath(patient.id),
  }
}

export async function getPatientPage(query: ListQuery): Promise<PatientPage> {
  const params = new URLSearchParams({
    page: String(query.page),
    page_size: String(query.pageSize),
    sort_by: query.sortBy,
    sort_order: query.sortOrder,
  })
  if (query.search !== '') {
    params.set('search', query.search)
  }
  if (query.gender !== null) {
    params.set('gender', query.gender)
  }
  const parsed = patientPageSchema.safeParse(await readJson(`${API_ENDPOINTS.patients}?${params.toString()}`))
  if (!parsed.success) {
    throw new InvalidResponseError()
  }
  return parsed.data
}
