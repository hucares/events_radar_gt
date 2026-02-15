export interface Event {
  id: number;
  title: string;
  description: string | null;
  url: string | null;
  venue: string;
  address: string | null;
  borough: string | null;
  start_time: string;
  end_time: string | null;
  category: string | null;
  source: string;
  source_id: string | null;
  image_url: string | null;
  price: string | null;
  is_free: number;
  created_at: string;
  updated_at: string;
}

export interface EventsResponse {
  events: Event[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface Stats {
  total_events: number;
  total_sources: number;
  total_categories: number;
  free_events: number;
  boroughs_covered: number;
}

export interface CategoryCount {
  category: string;
  count: number;
}

export interface SourceCount {
  source: string;
  count: number;
}

export interface Filters {
  q: string;
  category: string;
  borough: string;
  is_free: string;
  date_from: string;
  date_to: string;
}
