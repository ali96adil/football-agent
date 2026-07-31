"use client"

import { useQuery } from "@tanstack/react-query"

import { getFixtures } from "@/lib/fixtures"
import type { FixturesQuery } from "@/types/fixtures"

export function useFixtures(query: FixturesQuery) {
  return useQuery({
    queryKey: ["fixtures", query],
    queryFn: () => getFixtures(query),
    placeholderData: (previousData) => previousData,
    staleTime: 30_000,
  })
}
