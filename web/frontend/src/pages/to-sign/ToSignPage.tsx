import { MOCK_SIGN_KPI } from '../../constants/to-sign'
import { AppShell } from '../../shared/components/AppShell'
import { SignCase } from './components/SignCase'
import { useToSign } from './hooks/useToSign'

function Kpi({ label, value, note }: { label: string; value: number | string; note: string }) {
  return (
    <article className="rounded-xl border border-line bg-white p-4">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-3xl font-semibold">{value}</p>
      <p className="mt-1 text-xs text-muted">{note}</p>
    </article>
  )
}

export function ToSignPage() {
  const toSign = useToSign()

  return (
    <AppShell section="À signer">
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-medium tracking-[0.14em] text-teal uppercase">
              Validation assistée
            </p>
            <h1 className="mt-1 text-[26px] font-semibold">Cas simples traités par l’algorithme</h1>
            <p className="mt-1 text-sm text-muted">
              Profil sérique constant, peu d’événements. Vérifiez puis signez.
            </p>
          </div>
          <span className="rounded-full bg-chip px-3 py-1 text-sm text-muted">
            {toSign.remaining} en attente de signature
          </span>
        </div>

        <div className="grid gap-3 md:grid-cols-4">
          <Kpi label="Traités hier" value={MOCK_SIGN_KPI.yesterday} note={MOCK_SIGN_KPI.yesterdayNote} />
          <Kpi label="Traités cette semaine" value={MOCK_SIGN_KPI.week} note={MOCK_SIGN_KPI.weekNote} />
          <Kpi
            label="Taux d’accord"
            value={MOCK_SIGN_KPI.agreement}
            note={MOCK_SIGN_KPI.agreementNote}
          />
          <Kpi
            label="Relecture"
            value={MOCK_SIGN_KPI.reviewTime}
            note={MOCK_SIGN_KPI.reviewTimeNote}
          />
        </div>

        {toSign.isLoading ? <p className="text-sm text-muted">Chargement des cas à signer…</p> : null}
        {toSign.errorMessage === null ? null : (
          <p role="alert" className="text-sm text-amber">
            {toSign.errorMessage}
          </p>
        )}
        {!toSign.isLoading && toSign.errorMessage === null && toSign.cases.length === 0 ? (
          <p className="rounded-xl border border-line bg-white p-5 text-sm text-muted">
            Aucun cas à signer.
          </p>
        ) : null}

        {toSign.cases.length === 0 ? null : (
          <section className="overflow-hidden rounded-xl border border-line bg-white">
            <header className="flex items-center gap-2 border-b border-line px-5 py-4">
              <h2 className="text-base font-semibold">Cas à signer</h2>
              <span className="rounded-full bg-chip px-2 py-0.5 text-xs text-muted">
                {toSign.cases.length}
              </span>
            </header>
            <ul>
              {toSign.cases.map((item) => (
                <SignCase
                  key={item.id}
                  item={item}
                  expanded={toSign.expandedId === item.id}
                  pending={toSign.pendingId === item.id}
                  disabled={toSign.pendingId !== null}
                  error={toSign.failedId === item.id ? toSign.signError : null}
                  onToggle={() => toSign.onToggle(item.id)}
                  onSign={() => toSign.onSign(item.id)}
                />
              ))}
            </ul>
          </section>
        )}
      </div>
    </AppShell>
  )
}
