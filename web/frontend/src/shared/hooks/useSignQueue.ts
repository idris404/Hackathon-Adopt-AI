import { useQuery } from '@tanstack/react-query'

import { API_ENDPOINTS } from '../../constants/api'
import { signKeys } from '../../constants/to-sign'
import { signQueueSchema, type SignQueue } from '../schemas/signQueue'
import { apiFetch } from '../utils/api'

async function fetchSignQueue(): Promise<SignQueue> {
  const response = await apiFetch(API_ENDPOINTS.signQueue)
  return signQueueSchema.parse(await response.json())
}

// Partagé : la barre latérale affiche `remaining`, la page « À signer » affiche les cas.
export function useSignQueue() {
  return useQuery({ queryKey: signKeys.queue, queryFn: fetchSignQueue })
}
