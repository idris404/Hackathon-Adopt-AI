import { z } from 'zod'

// Sortie `serum_evolution` d'un patient (backend/app/patients/schemas.py : SerumEvolutionRead).
const serumAntigenSchema = z.object({
  code: z.string(),
  label: z.string(),
  value: z.number(),
  output: z.union([z.literal(0), z.literal(1)]),
})

export const serumEvolutionSchema = z.object({
  profile: z.enum(['A', 'B', 'C']).nullable(),
  label: z.string().nullable(),
  years: z.array(
    z.object({
      year: z.number().int(),
      test_date: z.iso.date(),
      antigens: z.array(serumAntigenSchema),
    }),
  ),
})

export type SerumEvolution = z.infer<typeof serumEvolutionSchema>
