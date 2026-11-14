import { Outlet } from 'react-router'

// Les pages connectées dessinent leur propre cadre (AppShell), déconnexion comprise.
export function AuthenticatedLayout() {
  return <Outlet />
}
