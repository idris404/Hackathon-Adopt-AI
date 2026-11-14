import { useQuery } from '@tanstack/react-query'
import { fetchCurrentUser } from '../utils/auth'
import { authKeys } from '../utils/queryKeys'

// `data` vaut null quand personne n'est connecté, l'utilisateur sinon.
export function useCurrentUser() {
  return useQuery({ queryKey: authKeys.currentUser, queryFn: fetchCurrentUser })
}
