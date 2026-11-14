import { SESSION_CHECK_MESSAGE, SESSION_ERROR_MESSAGE } from '../../constants/auth'

type SessionStatusScreenProps = { isError: boolean; onRetry: () => void }

// Écran plein page pendant que la session est vérifiée, ou quand la vérification a échoué.
export function SessionStatusScreen({ isError, onRetry }: SessionStatusScreenProps) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 bg-[#f4f7f8] p-8 text-center">
      {isError ? (
        <>
          <p role="alert" className="text-sm text-[#9c601c]">
            {SESSION_ERROR_MESSAGE}
          </p>
          <button
            type="button"
            onClick={onRetry}
            className="rounded-lg bg-[#087f74] px-4 py-2 text-[13px] font-semibold text-white hover:bg-[#06655c]"
          >
            Réessayer
          </button>
        </>
      ) : (
        <p role="status" className="text-sm text-[#687d82]">
          {SESSION_CHECK_MESSAGE}
        </p>
      )}
    </main>
  )
}
