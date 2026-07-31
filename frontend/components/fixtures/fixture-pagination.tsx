import {
  ChevronLeft,
  ChevronRight,
} from "lucide-react"

interface FixturePaginationProps {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
}

function createPageNumbers(
  page: number,
  totalPages: number,
) {
  const start = Math.max(
    1,
    Math.min(page - 2, totalPages - 4),
  )

  const end = Math.min(totalPages, start + 4)

  return Array.from(
    { length: Math.max(0, end - start + 1) },
    (_, index) => start + index,
  )
}

export function FixturePagination({
  page,
  totalPages,
  onPageChange,
}: FixturePaginationProps) {
  if (totalPages <= 1) {
    return null
  }

  const pages = createPageNumbers(page, totalPages)

  return (
    <nav
      className="flex flex-wrap items-center justify-center gap-2"
      aria-label="التنقل بين الصفحات"
    >
      <button
        type="button"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        className="inline-flex h-10 items-center gap-1 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm font-semibold text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <ChevronRight className="h-4 w-4" />
        السابق
      </button>

      {pages[0] > 1 && (
        <>
          <button
            type="button"
            onClick={() => onPageChange(1)}
            className="h-10 min-w-10 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200 hover:bg-slate-800"
          >
            1
          </button>

          {pages[0] > 2 && (
            <span className="px-1 text-slate-500">…</span>
          )}
        </>
      )}

      {pages.map((pageNumber) => (
        <button
          type="button"
          key={pageNumber}
          onClick={() => onPageChange(pageNumber)}
          aria-current={
            pageNumber === page ? "page" : undefined
          }
          className={
            pageNumber === page
              ? "h-10 min-w-10 rounded-xl border border-blue-500 bg-blue-500 px-3 text-sm font-bold text-white"
              : "h-10 min-w-10 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200 transition hover:bg-slate-800"
          }
        >
          {pageNumber}
        </button>
      ))}

      {pages[pages.length - 1] < totalPages && (
        <>
          {pages[pages.length - 1] < totalPages - 1 && (
            <span className="px-1 text-slate-500">…</span>
          )}

          <button
            type="button"
            onClick={() => onPageChange(totalPages)}
            className="h-10 min-w-10 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200 hover:bg-slate-800"
          >
            {totalPages}
          </button>
        </>
      )}

      <button
        type="button"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
        className="inline-flex h-10 items-center gap-1 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm font-semibold text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
      >
        التالي
        <ChevronLeft className="h-4 w-4" />
      </button>
    </nav>
  )
}
