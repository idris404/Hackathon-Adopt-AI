import { API_ENDPOINTS, HTTP_STATUS_UNAUTHORIZED } from '../../constants/api'
import { userSchema, type User } from '../schemas/user'
import { ApiError, apiFetch } from './api'

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === HTTP_STATUS_UNAUTHORIZED
}

// Renvoie null quand personne n'est connecté (401) : ce n'est pas une erreur, c'est un état.
export async function fetchCurrentUser(): Promise<User | null> {
  try {
    const response = await apiFetch(API_ENDPOINTS.currentUser)
    return userSchema.parse(await response.json())
  } catch (error) {
    if (isUnauthorized(error)) return null
    throw error
  }
}

// Un 401 signifie que la session n'existe déjà plus côté serveur : l'utilisateur est bien déconnecté.
export async function logout(): Promise<void> {
  try {
    await apiFetch(API_ENDPOINTS.logout, { method: 'POST' })
  } catch (error) {
    if (!isUnauthorized(error)) throw error
  }
}
