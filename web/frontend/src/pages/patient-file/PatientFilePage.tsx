import { AppShell } from '../../shared/components/AppShell'
import { Dossier } from './components/Dossier'
import { LoginPanel } from './components/LoginPanel'
import { usePatientFile } from './hooks/usePatientFile'
import { useRenalFunctionTable } from './hooks/useRenalFunctionTable'

export function PatientFilePage() {
  const { file, isLoading, needsSession, errorMessage } = usePatientFile()
  const table = useRenalFunctionTable(file?.renalRows ?? [])

  return (
    <AppShell section="Patients / Fiche patient">
      {needsSession ? <LoginPanel /> : null}
      {isLoading ? <p className="text-sm text-muted">Chargement du dossier…</p> : null}
      {errorMessage ? (
        <p role="alert" className="text-sm text-amber">
          {errorMessage}
        </p>
      ) : null}
      {file ? <Dossier file={file} table={table} /> : null}
    </AppShell>
  )
}
