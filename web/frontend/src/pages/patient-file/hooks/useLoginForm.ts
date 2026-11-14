import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'

import { PATIENT_FILE_ERRORS, patientFileKeys } from '../../../constants/patient-file'
import { loginSchema, type LoginValues } from '../schemas'
import { login } from '../utils'

export function useLoginForm() {
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  const onSubmit = form.handleSubmit(async (values) => {
    setFormError(null)
    try {
      await login(values.email, values.password)
      await queryClient.invalidateQueries({ queryKey: patientFileKeys.all })
    } catch {
      setFormError(PATIENT_FILE_ERRORS.credentials)
    }
  })

  return { form, onSubmit, formError }
}
