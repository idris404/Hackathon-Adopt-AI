import { z } from 'zod'

import { PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH } from '../../constants/auth'
import { GENDERS } from '../../constants/patient-file'
import { serumEvolutionSchema } from '../../shared/schemas/serum'

const genderSchema = z.enum(GENDERS)

const serumTestSchema = z.object({
  id: z.uuid(),
  patient_id: z.string(),
  graft_date: z.iso.date(),
  test_date: z.iso.date(),
  b12: z.number(),
  b12_output: z.number(),
  b13: z.number(),
  b13_output: z.number(),
  dr53: z.number(),
  dr53_output: z.number(),
  dr51: z.number(),
  dr51_output: z.number(),
  dq10: z.number(),
  dq10_output: z.number(),
  profile: z.string(),
})

export const patientSchema = z.object({
  id: z.uuid(),
  patient_id: z.string(),
  firstname: z.string(),
  lastname: z.string(),
  birth: z.iso.date().nullable(),
  gender: genderSchema,
  city: z.string(),
  country: z.string(),
  created_at: z.string(),
  serum_tests: z.array(serumTestSchema),
  serum_evolution: serumEvolutionSchema,
})

export const syntheticPatientSchema = z.object({
  patient_id: z.string(),
  phase: z.string(),
  statut_parcours: z.string(),
  organe: z.string(),
  maladie_renale_initiale: z.string(),
  date_greffe_actuelle: z.iso.date().nullable(),
  type_donneur: z.string().nullable(),
  dialyse_type: z.string(),
  dialyse_date_debut: z.iso.date().nullable(),
})

export const syntheticPatientPageSchema = z.object({
  items: z.array(syntheticPatientSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
})

export const loginSchema = z.object({
  email: z.email(),
  password: z.string().min(PASSWORD_MIN_LENGTH).max(PASSWORD_MAX_LENGTH),
})

export type PatientResponse = z.infer<typeof patientSchema>
export type SyntheticPatientResponse = z.infer<typeof syntheticPatientSchema>
export type LoginValues = z.infer<typeof loginSchema>
