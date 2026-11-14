import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { API_ENDPOINTS } from '../../../constants/api'
import { signKeys } from '../../../constants/to-sign'
import { useSignQueue } from '../../../shared/hooks/useSignQueue'
import { apiFetch } from '../../../shared/utils/api'
import { queueErrorMessage, signErrorMessage, toSignCase } from '../utils'

async function signPatient(patientId: string): Promise<void> {
  await apiFetch(API_ENDPOINTS.signatures, { method: 'POST', body: { patient_id: patientId } })
}

export function useToSign() {
  const queryClient = useQueryClient()
  const queue = useSignQueue()
  const sign = useMutation({
    mutationFn: signPatient,
    // Après un succès comme après un 409 : la file a changé côté serveur.
    onSettled: () => queryClient.invalidateQueries({ queryKey: signKeys.queue }),
  })

  const [today] = useState(() => new Date())
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const cases = useMemo(
    () => (queue.data?.items ?? []).map((item) => toSignCase(item, today)),
    [queue.data, today],
  )

  return {
    cases,
    remaining: queue.data?.remaining ?? 0,
    isLoading: queue.isLoading,
    errorMessage: queue.isError ? queueErrorMessage(queue.error) : null,
    onSign: (id: string) => sign.mutate(id),
    expandedId,
    onToggle: (id: string) => setExpandedId((current) => (current === id ? null : id)),
    pendingId: sign.isPending ? sign.variables : null,
    failedId: sign.isError ? sign.variables : null,
    signError: sign.isError ? signErrorMessage(sign.error) : null,
  }
}
