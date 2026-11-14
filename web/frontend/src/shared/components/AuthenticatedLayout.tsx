import { Outlet } from 'react-router'
import { useCurrentUser } from '../hooks/useCurrentUser'
import { useLogout } from '../hooks/useLogout'
import { BrandMark } from './BrandMark'

// Cadre des pages connectées : barre du haut avec l'utilisateur et le bouton de déconnexion.
export function AuthenticatedLayout() {
  const { data: user } = useCurrentUser()
  const { logout, isPending, errorMessage } = useLogout()

  return (
    <div className="flex min-h-screen flex-col bg-[#f4f7f8] text-[#183b40]">
      <header className="flex h-16 items-center justify-between border-b border-[#e4ecee] bg-white px-6">
        <BrandMark />
        <div className="flex items-center gap-4">
          {errorMessage && (
            <p role="alert" className="text-[13px] text-[#9c601c]">
              {errorMessage}
            </p>
          )}
          <span className="text-[13px] text-[#687d82]">{user?.email}</span>
          <button
            type="button"
            onClick={logout}
            disabled={isPending}
            className="rounded-lg border border-[#d7e4e4] bg-white px-3.5 py-2 text-[13px] font-medium text-[#183b40] hover:bg-[#f7fafa] disabled:opacity-60"
          >
            Déconnexion
          </button>
        </div>
      </header>
      <div className="flex flex-1 flex-col">
        <Outlet />
      </div>
    </div>
  )
}
