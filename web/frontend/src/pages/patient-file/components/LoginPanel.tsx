import { PATIENT_FILE_ERRORS } from '../../../constants/patient-file'
import { useLoginForm } from '../hooks/useLoginForm'

export function LoginPanel() {
  const { form, onSubmit, formError } = useLoginForm()
  const { register, formState } = form

  return (
    <form
      onSubmit={onSubmit}
      className="mx-auto mt-16 max-w-md rounded-xl border border-line bg-white p-6"
    >
      <h1 className="text-xl font-semibold">Ouvrir une session</h1>
      <p className="mt-2 text-sm text-muted">{PATIENT_FILE_ERRORS.session}</p>
      <label className="mt-5 block text-sm font-medium" htmlFor="email">
        Email
      </label>
      <input
        id="email"
        type="email"
        autoComplete="username"
        className="mt-1 w-full rounded-lg border border-button-line px-3 py-2 text-sm"
        {...register('email')}
      />
      {formState.errors.email ? (
        <p className="mt-1 text-xs text-amber">{formState.errors.email.message}</p>
      ) : null}
      <label className="mt-4 block text-sm font-medium" htmlFor="password">
        Mot de passe
      </label>
      <input
        id="password"
        type="password"
        autoComplete="current-password"
        className="mt-1 w-full rounded-lg border border-button-line px-3 py-2 text-sm"
        {...register('password')}
      />
      {formState.errors.password ? (
        <p className="mt-1 text-xs text-amber">{formState.errors.password.message}</p>
      ) : null}
      {formError ? (
        <p role="alert" className="mt-3 text-sm text-amber">
          {formError}
        </p>
      ) : null}
      <button
        type="submit"
        disabled={formState.isSubmitting}
        className="mt-5 rounded-lg bg-teal px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
      >
        Se connecter
      </button>
    </form>
  )
}
