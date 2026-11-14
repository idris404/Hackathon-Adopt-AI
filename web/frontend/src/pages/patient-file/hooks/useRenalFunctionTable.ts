import { getCoreRowModel, useLegacyTable, type LegacyColumnDef } from '@tanstack/react-table/legacy'

import type { RenalRow } from '../utils'

const columns: LegacyColumnDef<RenalRow>[] = [
  { accessorKey: 'dateLabel', header: 'Date / suivi' },
  { accessorKey: 'creatinine', header: 'Créatinine' },
  { accessorKey: 'dfg', header: 'DFGe' },
  { accessorKey: 'diuresis', header: 'Diurèse' },
]

export function useRenalFunctionTable(rows: RenalRow[]) {
  return useLegacyTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })
}
