import { z } from 'zod'

import { PATIENT_SORT_FIELDS, SORT_ORDERS } from '../../constants/dashboard'
import { GENDERS } from '../../constants/patient-file'

export const genderSchema = z.enum(GENDERS)

export const patientListItemSchema = z.object({
  id: z.uuid(),
  patient_id: z.string(),
  firstname: z.string(),
  lastname: z.string(),
  birth: z.iso.date().nullable(),
  gender: genderSchema,
  city: z.string(),
})

export const patientPageSchema = z.object({
  items: z.array(patientListItemSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
})

export const listQuerySchema = z.object({
  search: z.string(),
  gender: genderSchema.nullable(),
  page: z.number().int().positive(),
  pageSize: z.number().int().positive(),
  sortBy: z.enum(PATIENT_SORT_FIELDS),
  sortOrder: z.enum(SORT_ORDERS),
})

export type PatientListItem = z.infer<typeof patientListItemSchema>
export type PatientPage = z.infer<typeof patientPageSchema>
export type ListQuery = z.infer<typeof listQuerySchema>
