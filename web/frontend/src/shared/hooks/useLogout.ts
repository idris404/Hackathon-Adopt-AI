import { useMutation, useQueryClient } from '@tanstack/react-query'
import { LOGOUT_ERROR_MESSAGE } from '../../constants/auth'
import { logout } from '../utils/auth'
import { authKeys } from '../utils/queryKeys'

// Passer l'utilisateur courant à null suffit à rediriger : RequireAuth renvoie alors vers le login.
export function useLogout() {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      // Données de santé : rien ne doit rester en mémoire pour la prochaine session.
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== authKeys.all[0] })
      queryClient.setQueryData(authKeys.currentUser, null)
    },
  })
  return {
    logout: () => mutation.mutate(),
    isPending: mutation.isPending,
    errorMessage: mutation.isError ? LOGOUT_ERROR_MESSAGE : undefined,
  }
}
