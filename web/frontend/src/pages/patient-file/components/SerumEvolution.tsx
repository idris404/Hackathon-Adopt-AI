import type { SerumEvolution } from '../schemas'

const profileTone = {
  A: 'bg-success-soft text-success',
  B: 'bg-amber-soft text-amber',
  C: 'bg-danger-soft text-danger',
} as const

function Result({ output, value }: { output: 0 | 1; value: number }) {
  const positive = output === 1
  return (
    <span className={`font-medium tabular-nums ${positive ? 'text-danger' : 'text-success'}`}>
      {value.toLocaleString('fr-FR')}
      <span className="sr-only">{positive ? ', positif' : ', négatif'}</span>
    </span>
  )
}

export function SerumProfile({ evolution }: { evolution: SerumEvolution }) {
  const headers = evolution.years[0]?.antigens ?? []
  const tone = evolution.profile === null ? null : profileTone[evolution.profile]

  return (
    <section className="rounded-xl border border-line bg-white p-5">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-medium tracking-[0.14em] text-teal uppercase">
            Profil sérique
          </p>
          <h2 className="mt-1 text-[23px] font-semibold">Évolution des antigènes</h2>
          <p className="mt-1 text-sm text-muted">
            Un prélèvement par année. La couleur suit le résultat au seuil de 500.
          </p>
        </div>
        {evolution.profile !== null && evolution.label !== null && tone !== null ? (
          <div className={`flex items-center gap-3 rounded-xl px-4 py-3 ${tone}`}>
            <span className="text-3xl font-semibold">{evolution.profile}</span>
            <span>
              <span className="block text-[10px] font-medium tracking-[0.14em] uppercase">Profil</span>
              <span className="block text-lg font-semibold capitalize">{evolution.label}</span>
            </span>
          </div>
        ) : null}
      </header>

      <p className="mt-4 flex flex-wrap items-center gap-4 text-xs font-medium">
        <span className="text-success">Négatif</span>
        <span className="text-danger">Positif</span>
      </p>

      {evolution.years.length === 0 ? (
        <p className="mt-4 text-sm text-muted">Aucun prélèvement sérique pour ce patient.</p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full table-fixed text-left text-sm">
            <thead className="bg-header text-xs text-muted">
              <tr>
                <th className="w-20 px-3 py-2 font-medium">Année</th>
                {headers.map((antigen) => (
                  <th key={antigen.code} className="px-3 py-2 text-center font-medium">
                    {antigen.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {evolution.years.map((year) => (
                <tr key={year.test_date} className="border-t border-line">
                  <th className="px-3 py-3 text-left font-medium">{year.year}</th>
                  {year.antigens.map((antigen) => (
                    <td key={antigen.code} className="px-3 py-3 text-center">
                      <Result output={antigen.output} value={antigen.value} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
