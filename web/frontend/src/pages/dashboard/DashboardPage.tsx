import { flexRender } from '@tanstack/react-table'

import { MOCK_KPI } from '../../constants/dashboard'
import { GENDER_LABELS } from '../../constants/patient-file'
import { PAGE_SIZE_OPTIONS } from '../../constants/pagination'
import { AppShell } from '../../shared/components/AppShell'
import { usePatientList } from './hooks/usePatientList'

function Kpi({
  label,
  value,
  note,
  noteClass,
}: {
  label: string
  value: number
  note: string
  noteClass: string
}) {
  return (
    <article className="rounded-xl border border-line bg-white p-4">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-3xl font-semibold">{value}</p>
      <p className={`mt-1 text-xs ${noteClass}`}>{note}</p>
    </article>
  )
}

export function DashboardPage() {
  const list = usePatientList()
  const from = list.total === 0 ? 0 : (list.page - 1) * list.pageSize + 1
  const to = Math.min(list.page * list.pageSize, list.total)

  return (
    <AppShell section="Vue d’ensemble">
      <div className="flex flex-col gap-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-medium tracking-[0.14em] text-teal uppercase">
              Suivi des greffes rénales
            </p>
            <h1 className="mt-1 text-[26px] font-semibold">Chaque dossier, une vie en attente.</h1>
            <p className="mt-1 text-sm text-muted">
              Centralisez le suivi et priorisez les dossiers qui nécessitent votre attention.
            </p>
          </div>
          <button
            type="button"
            className="rounded-lg bg-teal px-4 py-2 text-sm font-medium text-white"
          >
            Ajouter un patient
          </button>
        </div>

        <div className="grid gap-3 md:grid-cols-4">
          <Kpi
            label="Patients en attente"
            value={MOCK_KPI.waiting}
            note={MOCK_KPI.waitingNote}
            noteClass="text-muted"
          />
          <Kpi
            label="Dossiers à valider"
            value={MOCK_KPI.toValidate}
            note={MOCK_KPI.toValidateNote}
            noteClass="text-muted"
          />
          <Kpi
            label="Résultats douteux"
            value={MOCK_KPI.doubtful}
            note={MOCK_KPI.doubtfulNote}
            noteClass="text-amber"
          />
          <Kpi
            label="Dossiers à jour"
            value={MOCK_KPI.upToDate}
            note={MOCK_KPI.upToDateNote}
            noteClass="text-success"
          />
        </div>

        <section className="flex max-h-[40rem] flex-col overflow-hidden rounded-xl border border-line bg-white">
          <header className="flex shrink-0 items-center justify-between gap-3 px-5 pt-5">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold">Liste des patients</h2>
              <span className="rounded-full bg-chip px-2 py-0.5 text-xs text-muted">{list.total}</span>
            </div>
            <button
              type="button"
              className="rounded-lg border border-button-line bg-white px-3 py-2 text-sm"
            >
              Exporter
            </button>
          </header>

          <div className="mt-4 flex shrink-0 flex-wrap items-center gap-2 px-5">
            <label className="sr-only" htmlFor="patient-search">
              Rechercher un patient
            </label>
            <input
              id="patient-search"
              value={list.draft}
              onChange={(event) => list.onSearchChange(event.target.value)}
              placeholder="Rechercher un identifiant, un nom…"
              className="h-10 min-w-64 flex-1 rounded-lg border border-line px-3 text-sm"
            />
            <label className="sr-only" htmlFor="patient-gender">
              Sexe
            </label>
            <select
              id="patient-gender"
              value={list.gender ?? ''}
              onChange={(event) => list.onGenderChange(event.target.value)}
              className="h-10 rounded-lg border border-line bg-white px-3 text-sm"
            >
              <option value="">Tous les sexes</option>
              <option value="F">{GENDER_LABELS.F}</option>
              <option value="M">{GENDER_LABELS.M}</option>
            </select>
            <span className="flex items-center gap-2">
              <select
                aria-label="Type de suppléance"
                disabled
                className="h-10 rounded-lg border border-line bg-white px-3 text-sm text-muted"
              >
                <option>Toute suppléance</option>
              </select>
              <select
                aria-label="Statut du dossier"
                disabled
                className="h-10 rounded-lg border border-line bg-white px-3 text-sm text-muted"
              >
                <option>Tous les statuts</option>
              </select>
            </span>
          </div>

          <div className="mt-4 min-h-0 overflow-auto">
            {list.isLoading ? <p className="px-5 py-6 text-sm text-muted">Chargement des patients…</p> : null}
            {list.errorMessage ? (
              <p role="alert" className="px-5 py-6 text-sm text-amber">
                {list.errorMessage}
              </p>
            ) : null}
            {list.errorMessage === null && !list.isLoading && list.total === 0 ? (
              <p className="px-5 py-6 text-sm text-muted">Aucun patient ne correspond à cette recherche.</p>
            ) : null}

            {list.errorMessage === null && list.total > 0 ? (
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 z-10 bg-header text-xs text-muted">
                  {list.table.getHeaderGroups().map((group) => (
                    <tr key={group.id}>
                      {group.headers.map((header) => (
                        <th key={header.id} className="px-5 py-2 font-medium">
                          {header.column.getCanSort() ? (
                            <button
                              type="button"
                              className="font-medium"
                              onClick={header.column.getToggleSortingHandler()}
                            >
                              {flexRender(header.column.columnDef.header, header.getContext())}
                              {header.column.getIsSorted() === 'asc' ? ' ↑' : null}
                              {header.column.getIsSorted() === 'desc' ? ' ↓' : null}
                            </button>
                          ) : (
                            flexRender(header.column.columnDef.header, header.getContext())
                          )}
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody>
                  {list.table.getRowModel().rows.map((row) => (
                    <tr key={row.id} className="border-t border-line">
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-5 py-3">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : null}
          </div>

          <footer className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-4 text-sm text-muted">
            <p>
              {from}–{to} sur {list.total}
            </p>
            <div className="flex items-center gap-2">
              <label htmlFor="page-size">Afficher</label>
              <select
                id="page-size"
                value={list.pageSize}
                onChange={(event) => list.onPageSizeChange(Number(event.target.value))}
                className="h-9 rounded-lg border border-line bg-white px-2"
              >
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <option key={size} value={size}>
                    {size} par page
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="rounded-lg border border-button-line px-3 py-1 disabled:opacity-40"
                onClick={() => list.table.previousPage()}
                disabled={!list.table.getCanPreviousPage()}
              >
                Précédent
              </button>
              <button
                type="button"
                className="rounded-lg border border-button-line px-3 py-1 disabled:opacity-40"
                onClick={() => list.table.nextPage()}
                disabled={!list.table.getCanNextPage()}
              >
                Suivant
              </button>
            </div>
          </footer>
        </section>

        <div className="grid gap-4 lg:grid-cols-2">
          <article className="rounded-xl border border-line bg-white p-5">
            <header className="flex items-center justify-between">
              <h2 className="text-base font-semibold">Validation</h2>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-chip px-2 py-0.5 text-xs text-muted">{MOCK_KPI.toValidate}</span>
              </div>
            </header>
            <p className="mt-2 text-sm text-muted">Les dossiers prêts pour votre revue médicale.</p>
            <ul className="mt-4 divide-y divide-line text-sm">
              <li className="flex items-center justify-between py-3">
                <span>
                  <span className="block font-medium">PT-2026-0148</span>
                  <span className="text-xs text-muted">Bilan pré-greffe complet</span>
                </span>
                <span className="text-xs text-muted">Reçu à 09:42</span>
              </li>
              <li className="flex items-center justify-between py-3">
                <span>
                  <span className="block font-medium">PT-2026-0144</span>
                  <span className="text-xs text-muted">Mise à jour du dossier clinique</span>
                </span>
                <span className="text-xs text-muted">Reçu à 08:15</span>
              </li>
            </ul>
          </article>
          <article className="rounded-xl border border-amber-line bg-white p-5">
            <header className="flex items-center justify-between">
              <h2 className="text-base font-semibold">Résultats douteux</h2>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-amber-soft px-2 py-0.5 text-xs text-amber">{MOCK_KPI.doubtful}</span>
              </div>
            </header>
            <p className="mt-2 text-sm text-muted">Une interprétation biologique est nécessaire.</p>
            <ul className="mt-4 divide-y divide-line text-sm">
              <li className="flex items-center justify-between py-3">
                <span>
                  <span className="block font-medium">PT-2026-0147</span>
                  <span className="text-xs text-muted">Sérologie CMV · Résultat équivoque</span>
                </span>
              </li>
              <li className="flex items-center justify-between py-3">
                <span>
                  <span className="block font-medium">PT-2026-0142</span>
                  <span className="text-xs text-muted">Typage HLA · Discordance à vérifier</span>
                </span>
              </li>
            </ul>
          </article>
        </div>
      </div>
    </AppShell>
  )
}
