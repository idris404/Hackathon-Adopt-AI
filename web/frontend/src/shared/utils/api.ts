import { z } from 'zod'
import { env } from '../../app/env'
import { API_V1_PREFIX, CONTENT_TYPE_HEADER, JSON_CONTENT_TYPE } from '../../constants/api'

// Un 4xx métier renvoie { detail: "CODE_STABLE" } ; un 422 renvoie une liste, qu'on ignore ici.
const errorBodySchema = z.object({ detail: z.string() })

export class ApiError extends Error {
  readonly status: number
  readonly detail: string | undefined

  constructor(status: number, detail: string | undefined) {
    super(detail ?? `HTTP ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

type ApiRequest = { method?: 'GET' | 'POST'; body?: unknown }

// Le cookie de session est HttpOnly : il est posé et envoyé par le navigateur (credentials: include).
export async function apiFetch(path: string, { method = 'GET', body }: ApiRequest = {}): Promise<Response> {
  const response = await fetch(`${env.VITE_API_URL}${API_V1_PREFIX}${path}`, {
    method,
    credentials: 'include',
    ...(body === undefined
      ? {}
      : { headers: { [CONTENT_TYPE_HEADER]: JSON_CONTENT_TYPE }, body: JSON.stringify(body) }),
  })
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response))
  }
  return response
}

async function readErrorDetail(response: Response): Promise<string | undefined> {
  try {
    const parsed = errorBodySchema.safeParse(await response.json())
    return parsed.success ? parsed.data.detail : undefined
  } catch {
    return undefined // corps absent ou qui n'est pas du JSON
  }
}
