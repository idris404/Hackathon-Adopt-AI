import { APP_NAME } from '../../constants/app'

export function BrandMark() {
  return (
    <div className="flex items-center gap-2.5">
      <span
        aria-hidden="true"
        className="flex size-9 items-center justify-center rounded-lg bg-[#c5f0d9] text-xl font-semibold text-[#0d554f]"
      >
        +
      </span>
      <span className="text-lg font-semibold text-[#183b40]">{APP_NAME}</span>
    </div>
  )
}
