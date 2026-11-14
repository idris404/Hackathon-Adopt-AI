import { flexRender } from '@tanstack/react-table'
import type { LegacyReactTable } from '@tanstack/react-table/legacy'

import { mockClinical, type PatientFile, type RenalRow } from '../utils'
import { SerumProfile } from '../../../shared/components/SerumEvolution'

export function Dossier({ file, table }: { file: PatientFile; table: LegacyReactTable<RenalRow> }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-medium tracking-[0.14em] text-teal uppercase">
            Dossier de transplantation rénale
          </p>
          <h1 className="mt-1 text-[26px] font-semibold">Fiche patient</h1>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className="rounded-lg border border-button-line bg-white px-3 py-2 text-sm"
          >
            Exporter le dossier
          </button>
          <button type="button" className="rounded-lg bg-teal px-3 py-2 text-sm font-semibold text-white">
            Modifier le dossier
          </button>
        </div>
      </div>

      <section className="rounded-xl border border-line bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-[23px] font-semibold">{file.fullName}</h2>
              <span className="rounded-full bg-success-soft px-2 py-0.5 text-[11px] font-medium text-success">
                {file.statusLabel}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted">{file.summary}</p>
          </div>
          <dl className="grid shrink-0 grid-cols-3 gap-x-8 gap-y-2 text-sm">
            <div>
              <dt className="text-xs text-muted">Groupe sanguin</dt>
              <dd className="font-medium">{mockClinical.bloodGroup}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">{file.organLabel}</dt>
              <dd className="font-medium">{file.graftDateLabel ?? 'Date inconnue'}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">Référent</dt>
              <dd className="font-medium">{file.referringDoctor}</dd>
            </div>
          </dl>
        </div>
      </section>

      {file.steps.length === 0 ? null : (
        <ol className="grid grid-cols-4 gap-3 rounded-xl border border-line bg-white px-6 py-4">
          {file.steps.map((step, index) => (
            <li key={step.index} className="relative">
              {index < file.steps.length - 1 ? (
                <span className="absolute top-4 left-8 right-0 h-px bg-step-line" />
              ) : null}
              <div className="relative flex items-start gap-3">
                <span
                  className={`grid size-8 shrink-0 place-items-center rounded-full text-sm font-semibold ${
                    step.note === 'J+7'
                      ? 'bg-teal text-white'
                      : 'bg-mint-soft text-teal'
                  }`}
                >
                  {step.index}
                </span>
                <span>
                  <span className="block text-sm font-medium">{step.title}</span>
                  <span className="block text-xs text-muted">
                    {step.dateLabel}
                    {step.note ? ` · ${step.note}` : ''}
                  </span>
                </span>
              </div>
            </li>
          ))}
        </ol>
      )}

      <SerumProfile evolution={file.serumEvolution} />

      <div className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-xl border border-line bg-white p-5">
          <header className="flex items-center justify-between">
            <h2 className="text-base font-semibold">01 Données préopératoires</h2>
            <span className="rounded bg-chip px-2 py-0.5 text-[11px] text-muted">Archivé</span>
          </header>
          <p className="mt-1 text-xs text-muted">
            {file.preopDateLabel === null
              ? 'Pas de date de greffe dans le dossier'
              : `Bilan du ${file.preopDateLabel} · Avant transplantation`}
          </p>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <Fact label="Néphropathie initiale" value={file.disease} />
            <Fact label="Suppléance rénale" value={file.dialysis} />
            <Fact label="Donneur" value={file.donor} />
          </dl>
          <div className="mt-4 rounded-lg bg-metric p-3 text-sm">
            <p>
              Créatinine / DFGe{' '}
              <strong>
                {mockClinical.preopCreatinine} µmol/L / {mockClinical.preopDfg} mL/min/1,73 m²
              </strong>
            </p>
            <p className="mt-1">
              Groupe / cPRA{' '}
              <strong>
                {mockClinical.bloodGroup} / {mockClinical.cpraPercent} %
              </strong>
            </p>
            <p className="mt-1">
              Bilan biologique{' '}
              <strong>
                K+ {mockClinical.potassium} · Hb {mockClinical.hemoglobin}
              </strong>
            </p>
          </div>
        </article>

        <article className="rounded-xl border border-line bg-white p-5">
          <h2 className="text-base font-semibold">02 Données postopératoires</h2>
          <p className="mt-1 text-xs text-muted">
            {file.postopDateLabel === null ? 'J+7' : `${file.postopDateLabel} · J+7`}
          </p>
          <div className="mt-4 grid grid-cols-3 gap-3">
            <Metric label="Créatinine" value={String(mockClinical.postopCreatinine)} unit="µmol/L" />
            <Metric label="DFGe" value={String(mockClinical.postopDfg)} unit="mL/min/1,73 m²" />
            <Metric label="Diurèse" value={mockClinical.postopDiuresis} unit="mL / 24 h" />
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <Fact label="Pression artérielle" value={mockClinical.bloodPressure} />
            <Fact label="Température" value={mockClinical.temperature} />
            <Fact label="Kaliémie" value={mockClinical.postopPotassium} />
            <Fact label="Écho-Doppler du greffon" value={mockClinical.doppler} />
          </dl>
        </article>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <article className="rounded-xl border border-line bg-white p-5">
          <h2 className="text-base font-semibold">Évolution de la fonction rénale</h2>
          <table className="mt-4 w-full text-left text-sm">
            <thead className="bg-header text-xs text-muted">
              {table.getHeaderGroups().map((group) => (
                <tr key={group.id}>
                  {group.headers.map((header) => (
                    <th key={header.id} className="px-3 py-2 font-medium">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr key={row.id} className={row.original.emphasized ? 'bg-mint-soft' : undefined}>
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-[11px] text-muted">DFGe estimé · valeurs fictives calées sur la date de greffe.</p>
        </article>

        <article className="rounded-xl border border-line bg-white p-5">
          <h2 className="text-base font-semibold">Traitement et vigilance</h2>
          <ul className="mt-4 flex flex-col gap-3 text-sm">
            {mockClinical.treatments.map((treatment) => (
              <li key={treatment.name}>
                <p className="font-medium">{treatment.name}</p>
                <p className="text-xs text-muted">{treatment.detail}</p>
              </li>
            ))}
          </ul>
          <p className="mt-4 rounded-lg border border-amber-line bg-amber-soft px-3 py-2 text-sm text-amber">
            Dosage résiduel en attente
          </p>
        </article>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-xl border border-line bg-white p-5">
          <h2 className="text-base font-semibold text-teal">Prochain suivi</h2>
          <p className="mt-2 text-lg font-semibold">
            {file.consultationDateLabel ?? 'Date inconnue'} · {mockClinical.consultationTime}
          </p>
          <p className="text-sm text-muted">Consultation de néphrologie · J+10</p>
          <p className="mt-2 text-sm">Bilan prévu : {mockClinical.plannedLabs}</p>
        </article>
        <article className="rounded-xl border border-line bg-white p-5">
          <h2 className="text-base font-semibold">Revue et traçabilité</h2>
          <p className="mt-3 text-sm text-muted">
            Dernière revue : {file.referringDoctor}
            {file.postopDateLabel ? ` · ${file.postopDateLabel}` : ''}
          </p>
          <p className="mt-3 inline-block rounded bg-blue-soft px-2 py-1 text-xs font-medium text-blue">
            Compte rendu à signer
          </p>
        </article>
      </div>
    </div>
  )
}

function Fact({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="font-medium">{value ?? 'Non renseigné'}</dd>
    </div>
  )
}

function Metric({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="rounded-lg bg-metric px-3 py-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
      <p className="text-[11px] text-muted">{unit}</p>
    </div>
  )
}
