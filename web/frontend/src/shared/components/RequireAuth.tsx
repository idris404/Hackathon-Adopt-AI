import { Navigate, Outlet } from 'react-router'
import { ROUTES } from '../../constants/routes'
import { useCurrentUser } from '../hooks/useCurrentUser'
import { SessionStatusScreen } from './SessionStatusScreen'

// Protège les routes enfants : sans session, renvoie vers le login.
export function RequireAuth() {
  const { data: user, isPending, isError, refetch } = useCurrentUser()
  if (isPending || isError) {
    return <SessionStatusScreen isError={isError} onRetry={() => void refetch()} />
  }
  if (!user) return <Navigate to={ROUTES.login} replace />
  return <Outlet />
}
