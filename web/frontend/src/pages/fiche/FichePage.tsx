import { useFicheId } from './hooks/useFicheId'

export function FichePage() {
  const ficheId = useFicheId()
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-2 p-8">
      <h1 className="text-2xl font-semibold">Fiche patient</h1>
      <p>{ficheId}</p>
    </main>
  )
}
