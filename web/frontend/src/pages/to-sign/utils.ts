import { z } from 'zod'

import { PATIENT_ALREADY_SIGNED_CODE, TO_SIGN_ERRORS } from '../../constants/to-sign'
import type { SerumEvolution } from '../../shared/schemas/serum'
import type { SignCaseResponse } from '../../shared/schemas/signQueue'
import { ApiError } from '../../shared/utils/api'
import { ageInYears } from '../../shared/utils/dates'
import { buildFichePath } from '../../shared/utils/routes'

export type SignCase = {
  id: string
  patientId: string
  name: string
  detail: string
  historyLabel: string
  evolution: SerumEvolution
  href: string
}

function historyLabel(count: number): string {
  if (count === 0) return 'Aucun événement'
  return count === 1 ? '1 événement' : `${count} événements`
}

export function toSignCase(item: SignCaseResponse, today: Date): SignCase {
  const tests = item.serum_evolution.years.length
  const age = item.birth === null ? null : `${ageInYears(item.birth, today)} ans`
  const testsLabel = tests === 1 ? '1 prélèvement' : `${tests} prélèvements`
  return {
    id: item.id,
    patientId: item.patient_id,
    name: `${item.firstname} ${item.lastname}`,
    detail: age === null ? testsLabel : `${age} · ${testsLabel}`,
    historyLabel: historyLabel(item.history.length),
    evolution: item.serum_evolution,
    href: buildFichePath(item.id),
  }
}

export function queueErrorMessage(error: unknown): string {
  return error instanceof z.ZodError ? TO_SIGN_ERRORS.invalid : TO_SIGN_ERRORS.queue
}

export function signErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.detail === PATIENT_ALREADY_SIGNED_CODE) {
    return TO_SIGN_ERRORS.alreadySigned
  }
  return TO_SIGN_ERRORS.sign
}
