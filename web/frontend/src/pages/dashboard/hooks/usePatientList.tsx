import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { getCoreRowModel, useLegacyTable, type LegacyColumnDef } from '@tanstack/react-table/legacy'
import { parseAsInteger, parseAsString, parseAsStringLiteral, useQueryStates } from 'nuqs'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'

import { GENDERS } from '../../../constants/patient-file'
import { PAGE_SIZE_OPTIONS } from '../../../constants/pagination'
import { QUERY_RETRY_COUNT } from '../../../constants/query'
import {
  DASHBOARD_ERRORS,
  DASHBOARD_PAGE_SIZE,
  DASHBOARD_SEARCH_DEBOUNCE_MS,
  DEFAULT_PATIENT_SORT,
  DEFAULT_SORT_ORDER,
  PATIENT_SORT_FIELDS,
  SORT_ORDERS,
  dashboardKeys,
} from '../../../constants/dashboard'
import { InvalidResponseError, SessionRequiredError } from '../../../shared/api'
import {
  getPatientPage,
  toPatientRow,
  type PatientRow,
} from '../utils'
import type { ListQuery } from '../schemas'

const columns: LegacyColumnDef<PatientRow>[] = [
  {
    id: 'lastname',
    header: 'Patient',
    accessorFn: (row) => row.name,
    cell: ({ row }) => (
      <span>
        <span className="block font-medium">{row.original.name}</span>
        <span className="block text-xs text-muted">{row.original.patientId}</span>
        <span className="block text-xs text-muted">{row.original.detail}</span>
      </span>
    ),
  },
  { id: 'city', accessorKey: 'city', header: 'Ville' },
  { id: 'birth', accessorKey: 'birthLabel', header: 'Naissance' },
  {
    id: 'open',
    header: '',
    enableSorting: false,
    cell: ({ row }) => (
      <Link to={row.original.href} className="font-medium text-teal">
        Ouvrir
      </Link>
    ),
  },
]

function isPageSize(value: number): value is (typeof PAGE_SIZE_OPTIONS)[number] {
  return PAGE_SIZE_OPTIONS.some((option) => option === value)
}

function isSortField(value: string): value is (typeof PATIENT_SORT_FIELDS)[number] {
  return PATIENT_SORT_FIELDS.some((field) => field === value)
}

function applyUpdate<T>(updater: T | ((current: T) => T), current: T): T {
  if (typeof updater === 'function') {
    return (updater as (current: T) => T)(current)
  }
  return updater
}

function messageFor(error: unknown): string {
  if (error instanceof SessionRequiredError) {
    return DASHBOARD_ERRORS.session
  }
  if (error instanceof InvalidResponseError) {
    return DASHBOARD_ERRORS.invalid
  }
  return DASHBOARD_ERRORS.unavailable
}

export function usePatientList() {
  const [query, setQuery] = useQueryStates({
    search: parseAsString.withDefault(''),
    gender: parseAsStringLiteral(GENDERS),
    page: parseAsInteger.withDefault(1),
    page_size: parseAsInteger.withDefault(DASHBOARD_PAGE_SIZE),
    sort_by: parseAsStringLiteral(PATIENT_SORT_FIELDS).withDefault(DEFAULT_PATIENT_SORT),
    sort_order: parseAsStringLiteral(SORT_ORDERS).withDefault(DEFAULT_SORT_ORDER),
  })
  const page = query.page < 1 ? 1 : query.page
  const pageSize = isPageSize(query.page_size) ? query.page_size : DASHBOARD_PAGE_SIZE
  const listQuery: ListQuery = {
    search: query.search,
    gender: query.gender,
    page,
    pageSize,
    sortBy: query.sort_by,
    sortOrder: query.sort_order,
  }
  const patients = useQuery({
    queryKey: dashboardKeys.patients(listQuery),
    queryFn: async () => ({ page: await getPatientPage(listQuery), today: new Date() }),
    placeholderData: keepPreviousData,
    retry: (failureCount, error) =>
      !(error instanceof SessionRequiredError) && failureCount < QUERY_RETRY_COUNT,
  })
  const rows =
    patients.data === undefined
      ? []
      : patients.data.page.items.map((item) => toPatientRow(item, patients.data.today))
  const total = patients.data?.page.total ?? 0
  const [draft, setDraft] = useState(query.search)
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => {
    return () => window.clearTimeout(timer.current)
  }, [])

  const table = useLegacyTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualFiltering: true,
    manualSorting: true,
    manualPagination: true,
    rowCount: total,
    getRowId: (row) => row.id,
    state: {
      pagination: { pageIndex: page - 1, pageSize },
      sorting: [{ id: query.sort_by, desc: query.sort_order === 'desc' }],
    },
    onPaginationChange: (updater) => {
      const next = applyUpdate(updater, { pageIndex: page - 1, pageSize })
      void setQuery({ page: next.pageIndex + 1, page_size: next.pageSize })
    },
    onSortingChange: (updater) => {
      const next = applyUpdate(updater, [{ id: query.sort_by, desc: query.sort_order === 'desc' }])
      const first = next[0]
      if (first === undefined || !isSortField(first.id)) {
        return
      }
      void setQuery({
        sort_by: first.id,
        sort_order: first.desc ? 'desc' : 'asc',
        page: 1,
      })
    },
  })

  return {
    table,
    draft,
    gender: query.gender,
    pageSize,
    total,
    page,
    isLoading: patients.isPending,
    errorMessage: patients.error == null ? null : messageFor(patients.error),
    onSearchChange: (value: string) => {
      setDraft(value)
      window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => {
        void setQuery({ search: value === '' ? null : value, page: 1 })
      }, DASHBOARD_SEARCH_DEBOUNCE_MS)
    },
    onGenderChange: (value: string) => {
      void setQuery({ gender: value === 'M' || value === 'F' ? value : null, page: 1 })
    },
    onPageSizeChange: (value: number) => {
      if (!isPageSize(value)) {
        return
      }
      void setQuery({ page_size: value, page: 1 })
    },
  }
}
