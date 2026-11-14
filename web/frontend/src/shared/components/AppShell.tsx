import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router'

import { MOCK_NAV_COUNTS, MOCK_REFERRING_DOCTOR } from '../../constants/patient-file'
import { ROUTES } from '../../constants/routes'

const placeholders = [
  { label: 'Validation', count: MOCK_NAV_COUNTS.validation, alert: false },
  { label: 'Résultats douteux', count: MOCK_NAV_COUNTS.doubtful, alert: true },
  { label: 'Historique', count: null, alert: false },
  { label: 'Paramètres', count: null, alert: false },
] as const

function itemClass(active: boolean): string {
  return `flex items-center justify-between rounded-lg px-3 py-2 text-[13px] ${
    active ? 'bg-sidebar-active text-mint-active' : ''
  }`
}

function Count({ count, alert }: { count: number; alert: boolean }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[11px] ${
        alert ? 'bg-sidebar-alert text-sidebar-alert-text' : 'bg-sidebar-count text-sidebar-count-text'
      }`}
    >
      {count}
    </span>
  )
}

export function AppShell({ children, section }: { children: ReactNode; section: string }) {
  return (
    <div className="flex min-h-screen bg-canvas font-sans text-ink">
      <aside className="flex w-[232px] shrink-0 flex-col bg-sidebar px-4 py-5 text-sidebar-text">
        <NavLink to={ROUTES.dashboard} className="flex items-center gap-3 px-2">
          <span className="grid size-9 place-items-center rounded-lg bg-mint text-lg font-semibold text-teal-deep">
            +
          </span>
          <span className="text-lg font-semibold text-white">greffe</span>
        </NavLink>
        <p className="mt-8 px-2 text-[10px] font-medium tracking-[0.14em] text-sidebar-muted uppercase">
          Coordination rénale
        </p>
        <nav className="mt-3 flex flex-col gap-1" aria-label="Navigation">
          <NavLink
            to={ROUTES.dashboard}
            end
            className={({ isActive }) => itemClass(isActive)}
          >
            <span>Vue d’ensemble</span>
          </NavLink>
          <Link to={ROUTES.dashboard} className={itemClass(false)}>
            <span>Liste des patients</span>
            <Count count={MOCK_NAV_COUNTS.patients} alert={false} />
          </Link>
          {placeholders.map((item) => (
            <div key={item.label} className={itemClass(false)}>
              <span>{item.label}</span>
              {item.count === null ? null : <Count count={item.count} alert={item.alert} />}
            </div>
          ))}
        </nav>
        <div className="mt-auto rounded-xl bg-sidebar-raised p-4">
          <p className="text-sm font-medium text-sidebar-strong">Besoin d’aide ?</p>
          <p className="mt-1 text-xs text-sidebar-muted">Contacter le support</p>
        </div>
        <p className="mt-4 px-1 text-sm text-sidebar-strong">CHU Saint-Louis</p>
        <p className="px-1 text-xs text-sidebar-muted">Unité de greffe rénale</p>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-line bg-white px-8">
          <p className="text-sm whitespace-nowrap text-muted">
            Transplantation rénale <span className="px-2 text-line">/</span> {section}
          </p>
          <div className="flex shrink-0 items-center gap-4 text-sm">
            <span className="rounded-full bg-mint-ice px-3 py-1 text-xs font-medium whitespace-nowrap text-success">
              Session sécurisée
            </span>
            <span className="text-right whitespace-nowrap">
              <span className="block font-medium">{MOCK_REFERRING_DOCTOR}</span>
              <span className="block text-xs text-muted">Médecin coordinateur</span>
            </span>
          </div>
        </header>
        <main className="flex-1 px-8 py-6">{children}</main>
      </div>
    </div>
  )
}
