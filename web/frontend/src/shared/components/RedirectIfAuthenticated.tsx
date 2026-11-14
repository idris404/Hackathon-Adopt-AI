import { Navigate, Outlet } from 'react-router'
import { ROUTES } from '../../constants/routes'
import { useCurrentUser } from '../hooks/useCurrentUser'
import { SessionStatusScreen } from './SessionStatusScreen'

// Enveloppe les routes réservées aux visiteurs (login) : une fois connecté, on file au tableau de bord.
// C'est aussi ce qui redirige juste après une connexion réussie, quand le cache de session est rafraîchi.
export function RedirectIfAuthenticated() {
  const { data: user, isPending, isError, refetch } = useCurrentUser()
  if (isPending || isError) {
    return <SessionStatusScreen isError={isError} onRetry={() => void refetch()} />
  }
  if (user) return <Navigate to={ROUTES.dashboard} replace />
  return <Outlet />
}
