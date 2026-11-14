import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router'

import { QUERY_RETRY_COUNT } from '../../../constants/query'
import { PATIENT_FILE_ERRORS, patientFileKeys } from '../../../constants/patient-file'
import { FICHE_ID_PARAM } from '../../../constants/routes'
import {
  ApiRequestError,
  InvalidResponseError,
  SessionRequiredError,
  buildPatientFile,
  getPatient,
  getSyntheticPatient,
  type PatientFile,
} from '../utils'

function messageFor(error: unknown): string {
  if (error instanceof ApiRequestError && error.status === 404) {
    return PATIENT_FILE_ERRORS.notFound
  }
  if (error instanceof InvalidResponseError) {
    return PATIENT_FILE_ERRORS.invalid
  }
  return PATIENT_FILE_ERRORS.unavailable
}

function withoutSessionRetry(failureCount: number, error: Error): boolean {
  if (error instanceof SessionRequiredError) {
    return false
  }
  return failureCount < QUERY_RETRY_COUNT
}

export function usePatientFile(): {
  file: PatientFile | null
  isLoading: boolean
  needsSession: boolean
  errorMessage: string | null
} {
  const patientId = useParams()[FICHE_ID_PARAM]
  const patient = useQuery({
    queryKey: patientFileKeys.patient(patientId ?? ''),
    queryFn: async () => ({ patient: await getPatient(patientId ?? ''), today: new Date() }),
    enabled: patientId !== undefined,
    retry: withoutSessionRetry,
  })
  const synthetic = useQuery({
    queryKey: patientFileKeys.synthetic(patientId ?? ''),
    queryFn: () => getSyntheticPatient(patientId ?? ''),
    enabled: patient.isSuccess,
    retry: withoutSessionRetry,
  })

  const needsSession =
    patient.error instanceof SessionRequiredError || synthetic.error instanceof SessionRequiredError
  const error = patient.error ?? synthetic.error
  const isLoading =
    patientId !== undefined && (patient.isPending || (patient.isSuccess && synthetic.isPending))

  return {
    file:
      patient.data === undefined || synthetic.data === undefined
        ? null
        : buildPatientFile(patient.data.patient, synthetic.data, patient.data.today),
    isLoading,
    needsSession,
    errorMessage:
      patientId === undefined
        ? PATIENT_FILE_ERRORS.notFound
        : needsSession || error == null
          ? null
          : messageFor(error),
  }
}
