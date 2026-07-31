import type {
  FixturesQuery,
  FixturesResponse,
} from "@/types/fixtures"

function addQueryValue(
  params: URLSearchParams,
  key: string,
  value: string | number | undefined,
) {
  if (value === undefined || value === null || value === "") {
    return
  }

  params.set(key, String(value))
}

export async function getFixtures(
  query: FixturesQuery = {},
): Promise<FixturesResponse> {
  const params = new URLSearchParams()

  addQueryValue(params, "page", query.page ?? 1)
  addQueryValue(params, "page_size", query.page_size ?? 20)
  addQueryValue(params, "search", query.search?.trim())
  addQueryValue(params, "status", query.status)
  addQueryValue(params, "competition_id", query.competition_id)
  addQueryValue(params, "team_id", query.team_id)
  addQueryValue(params, "date", query.date)
  addQueryValue(params, "sort", query.sort ?? "upcoming")

  const response = await fetch(`/api/v1/fixtures?${params.toString()}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
  })

  if (!response.ok) {
    const message = await response.text()

    throw new Error(
      message || `تعذر تحميل المباريات، رمز الخطأ: ${response.status}`,
    )
  }

  const data = await response.json()

  const items = Array.isArray(data.items)
    ? data.items
    : Array.isArray(data.results)
      ? data.results
      : []

  const total = Number(data.total ?? data.count ?? items.length)
  const page = Number(data.page ?? query.page ?? 1)
  const pageSize = Number(
    data.page_size ??
      data.pageSize ??
      query.page_size ??
      20,
  )

  const totalPages = Number(
    data.total_pages ??
      data.pages ??
      Math.max(1, Math.ceil(total / pageSize)),
  )

  return {
    items,
    total,
    page,
    page_size: pageSize,
    total_pages: totalPages,
  }
}
