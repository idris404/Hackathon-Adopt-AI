import { z } from 'zod'

// Seul module qui lit import.meta.env. Tout VITE_* est public : aucun secret ici.
const envSchema = z.object({
  VITE_API_URL: z.url(),
})

export const env = envSchema.parse(import.meta.env)
