import { API_ENDPOINTS } from '../../constants/api'
import {
  INVALID_CREDENTIALS_CODE,
  INVALID_CREDENTIALS_MESSAGE,
  LOGIN_ERROR_MESSAGE,
} from '../../constants/auth'
import { ApiError, apiFetch } from '../../shared/utils/api'
import type { LoginFormValues } from './schemas'

// 204 sans corps : le cookie de session est posé par le navigateur à la réception de la réponse.
export async function login(credentials: LoginFormValues): Promise<void> {
  await apiFetch(API_ENDPOINTS.login, { method: 'POST', body: credentials })
}

export function getLoginErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.detail === INVALID_CREDENTIALS_CODE) {
    return INVALID_CREDENTIALS_MESSAGE
  }
  return LOGIN_ERROR_MESSAGE
}
