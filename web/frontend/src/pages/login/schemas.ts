import { z } from 'zod'
import {
  EMAIL_INVALID_MESSAGE,
  PASSWORD_MAX_LENGTH,
  PASSWORD_REQUIRED_MESSAGE,
  PASSWORD_TOO_LONG_MESSAGE,
} from '../../constants/auth'

// Aide à la saisie seulement : le backend revalide (LoginRequest) et fait foi.
export const loginSchema = z.object({
  email: z.email(EMAIL_INVALID_MESSAGE),
  password: z.string().min(1, PASSWORD_REQUIRED_MESSAGE).max(PASSWORD_MAX_LENGTH, PASSWORD_TOO_LONG_MESSAGE),
})

export type LoginFormValues = z.infer<typeof loginSchema>
