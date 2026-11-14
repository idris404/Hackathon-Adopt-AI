import { z } from 'zod'

import { serumEvolutionSchema } from './serum'

// Sortie de GET /signatures/queue (backend/app/signatures/schemas.py : SignQueueRead).
// Seuls les champs affichés sont lus ; chaque élément est un `Patient` complet côté serveur.
const signCaseSchema = z.object({
  id: z.uuid(),
  patient_id: z.string(),
  firstname: z.string(),
  lastname: z.string(),
  birth: z.iso.date().nullable(),
  history: z.array(z.object({ id: z.uuid() })),
  serum_evolution: serumEvolutionSchema,
})

export const signQueueSchema = z.object({
  items: z.array(signCaseSchema),
  remaining: z.number().int(),
})

export type SignCaseResponse = z.infer<typeof signCaseSchema>
export type SignQueue = z.infer<typeof signQueueSchema>
