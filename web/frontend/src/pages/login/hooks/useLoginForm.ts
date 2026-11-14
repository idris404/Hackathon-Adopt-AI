import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { authKeys } from '../../../shared/utils/queryKeys'
import { loginSchema, type LoginFormValues } from '../schemas'
import { getLoginErrorMessage, login } from '../utils'

export function useLoginForm() {
  const queryClient = useQueryClient()
  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  const mutation = useMutation({
    mutationFn: login,
    // On attend le rafraîchissement de la session : RedirectIfAuthenticated envoie alors au tableau de bord.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: authKeys.currentUser }),
    onError: (error) => form.setError('root', { message: getLoginErrorMessage(error) }),
  })

  return {
    register: form.register,
    errors: form.formState.errors,
    isPending: mutation.isPending,
    onSubmit: form.handleSubmit((values) => mutation.mutate(values)),
  }
}
