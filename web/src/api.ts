import type { EventsResponse, Stats, CategoryCount, SourceCount } from "./types";

export async function fetchEvents(params: Record<string, string>): Promise<EventsResponse> {
  const search = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v) search.set(k, v);
  }
  const res = await fetch(`/api/events?${search}`);
  if (!res.ok) throw new Error("Failed to fetch events");
  return res.json();
}

export async function fetchStats(): Promise<Stats> {
  const res = await fetch("/api/stats");
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function fetchCategories(): Promise<CategoryCount[]> {
  const res = await fetch("/api/categories");
  if (!res.ok) throw new Error("Failed to fetch categories");
  return res.json();
}

export async function fetchSources(): Promise<SourceCount[]> {
  const res = await fetch("/api/sources");
  if (!res.ok) throw new Error("Failed to fetch sources");
  return res.json();
}
