import { z } from 'zod'

// Sortie de GET /users/me (backend/app/users/schemas.py : UserRead). Jamais de mot de passe ni de hash.
export const userSchema = z.object({
  id: z.uuid(),
  email: z.email(),
  is_active: z.boolean(),
  is_superuser: z.boolean(),
  is_verified: z.boolean(),
})

export type User = z.infer<typeof userSchema>
