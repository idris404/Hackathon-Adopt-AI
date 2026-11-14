import { APP_NAME } from '../../constants/app'
import { BrandMark } from '../../shared/components/BrandMark'
import { useLoginForm } from './hooks/useLoginForm'

const INPUT_CLASS =
  'w-full rounded-lg border border-[#e4ecee] bg-white px-3 py-2.5 text-sm text-[#183b40] placeholder:text-[#849599] focus:border-[#087f74] focus:outline-none focus:ring-2 focus:ring-[#087f74]/20 aria-invalid:border-[#9c601c]'

export function LoginPage() {
  const { register, errors, isPending, onSubmit } = useLoginForm()

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f4f7f8] p-6">
      <div className="w-full max-w-sm rounded-xl border border-[#e4ecee] bg-white p-8">
        <BrandMark />
        <p className="mt-6 text-[10px] font-semibold tracking-wider text-[#087f74] uppercase">
          Suivi des greffes rénales
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-[#183b40]">Connexion</h1>
        <p className="mt-1 text-[13px] text-[#687d82]">Accédez à votre espace {APP_NAME}.</p>

        <form onSubmit={onSubmit} noValidate className="mt-6 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="email" className="text-[13px] font-medium text-[#183b40]">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              aria-invalid={errors.email ? true : undefined}
              aria-describedby={errors.email ? 'email-error' : undefined}
              className={INPUT_CLASS}
              {...register('email')}
            />
            {errors.email && (
              <p id="email-error" className="text-xs text-[#9c601c]">
                {errors.email.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="password" className="text-[13px] font-medium text-[#183b40]">
              Mot de passe
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              aria-invalid={errors.password ? true : undefined}
              aria-describedby={errors.password ? 'password-error' : undefined}
              className={INPUT_CLASS}
              {...register('password')}
            />
            {errors.password && (
              <p id="password-error" className="text-xs text-[#9c601c]">
                {errors.password.message}
              </p>
            )}
          </div>

          {errors.root && (
            <p role="alert" className="rounded-lg bg-[#fff5e5] px-3 py-2 text-[13px] text-[#9c601c]">
              {errors.root.message}
            </p>
          )}

          <button
            type="submit"
            disabled={isPending}
            className="rounded-lg bg-[#087f74] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#06655c] disabled:opacity-60"
          >
            {isPending ? 'Connexion…' : 'Se connecter'}
          </button>
        </form>
      </div>
    </main>
  )
}
