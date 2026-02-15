import { useCallback, useEffect, useMemo, useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type Row,
} from "@tanstack/react-table";
import { fetchEvents, fetchStats, fetchCategories } from "./api";
import type { Event, EventsResponse, Stats, CategoryCount, Filters } from "./types";

const BOROUGHS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"];

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

// --- Expanded Row Detail ---

function EventDetail({ event }: { event: Event }) {
  return (
    <div className="grid gap-4 bg-gray-50 px-6 py-4 text-sm sm:grid-cols-2">
      <div className="space-y-2">
        {event.description && (
          <p className="text-gray-700">{event.description}</p>
        )}
        {event.address && (
          <p className="text-gray-500">
            <span className="font-medium text-gray-700">Address:</span>{" "}
            {event.address}
          </p>
        )}
        {event.end_time && (
          <p className="text-gray-500">
            <span className="font-medium text-gray-700">Ends:</span>{" "}
            {formatDate(event.end_time)} at {formatTime(event.end_time)}
          </p>
        )}
      </div>
      <div className="space-y-2">
        {event.url && (
          <a
            href={event.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block rounded bg-nyc-sky px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-600"
          >
            View Event &rarr;
          </a>
        )}
        {event.image_url && (
          <img
            src={event.image_url}
            alt={event.title}
            className="mt-2 max-h-40 rounded object-cover"
          />
        )}
      </div>
    </div>
  );
}

// --- Stats Bar ---

function StatsBar({ stats }: { stats: Stats | null }) {
  if (!stats) return null;
  const items = [
    { label: "Events", value: stats.total_events },
    { label: "Sources", value: stats.total_sources },
    { label: "Categories", value: stats.total_categories },
    { label: "Free", value: stats.free_events },
    { label: "Boroughs", value: stats.boroughs_covered },
  ];
  return (
    <div className="flex flex-wrap gap-4">
      {items.map((s) => (
        <div
          key={s.label}
          className="flex items-baseline gap-1.5 rounded-full bg-white px-4 py-1.5 text-sm shadow-sm ring-1 ring-gray-200"
        >
          <span className="font-semibold text-nyc-navy">{s.value}</span>
          <span className="text-gray-500">{s.label}</span>
        </div>
      ))}
    </div>
  );
}

// --- Filter Bar ---

function FilterBar({
  filters,
  onChange,
  categories,
}: {
  filters: Filters;
  onChange: (f: Partial<Filters>) => void;
  categories: CategoryCount[];
}) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      {/* Search */}
      <div className="flex-1" style={{ minWidth: 200 }}>
        <label className="mb-1 block text-xs font-medium text-gray-500">
          Search
        </label>
        <input
          type="text"
          placeholder="Search events..."
          value={filters.q}
          onChange={(e) => onChange({ q: e.target.value })}
          className="filter-input w-full"
        />
      </div>

      {/* Category */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">
          Category
        </label>
        <select
          value={filters.category}
          onChange={(e) => onChange({ category: e.target.value })}
          className="filter-select"
        >
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c.category} value={c.category}>
              {c.category} ({c.count})
            </option>
          ))}
        </select>
      </div>

      {/* Borough */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">
          Borough
        </label>
        <select
          value={filters.borough}
          onChange={(e) => onChange({ borough: e.target.value })}
          className="filter-select"
        >
          <option value="">All Boroughs</option>
          {BOROUGHS.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
      </div>

      {/* Free / Paid */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">
          Price
        </label>
        <select
          value={filters.is_free}
          onChange={(e) => onChange({ is_free: e.target.value })}
          className="filter-select"
        >
          <option value="">All</option>
          <option value="true">Free</option>
          <option value="false">Paid</option>
        </select>
      </div>

      {/* Date From */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">
          From
        </label>
        <input
          type="date"
          value={filters.date_from}
          onChange={(e) => onChange({ date_from: e.target.value })}
          className="filter-input"
        />
      </div>

      {/* Date To */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">
          To
        </label>
        <input
          type="date"
          value={filters.date_to}
          onChange={(e) => onChange({ date_to: e.target.value })}
          className="filter-input"
        />
      </div>

      {/* Clear */}
      <button
        onClick={() =>
          onChange({
            q: "",
            category: "",
            borough: "",
            is_free: "",
            date_from: "",
            date_to: "",
          })
        }
        className="rounded px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-700"
      >
        Clear
      </button>
    </div>
  );
}

// --- Pagination ---

function Pagination({
  page,
  pages,
  total,
  onPage,
}: {
  page: number;
  pages: number;
  total: number;
  onPage: (p: number) => void;
}) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-500">
        {total} event{total !== 1 ? "s" : ""} found
      </span>
      <div className="flex items-center gap-2">
        <button
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
          className="rounded border border-gray-300 px-3 py-1 text-gray-600 hover:bg-gray-100 disabled:opacity-40"
        >
          Prev
        </button>
        <span className="text-gray-600">
          {page} / {pages}
        </span>
        <button
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
          className="rounded border border-gray-300 px-3 py-1 text-gray-600 hover:bg-gray-100 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}

// --- Sort Icon ---

function SortIcon({ dir }: { dir: false | "asc" | "desc" }) {
  if (!dir) return <span className="ml-1 text-gray-300">&uarr;&darr;</span>;
  return (
    <span className="ml-1 text-nyc-sky">
      {dir === "asc" ? "\u25B2" : "\u25BC"}
    </span>
  );
}

// --- Main App ---

const DEFAULT_FILTERS: Filters = {
  q: "",
  category: "",
  borough: "",
  is_free: "",
  date_from: "",
  date_to: "",
};

export default function App() {
  const [data, setData] = useState<EventsResponse | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [categories, setCategories] = useState<CategoryCount[]>([]);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);

  // Debounced search
  const [debouncedQ, setDebouncedQ] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(filters.q), 300);
    return () => clearTimeout(t);
  }, [filters.q]);

  // Load reference data once
  useEffect(() => {
    fetchStats().then(setStats).catch(console.error);
    fetchCategories().then(setCategories).catch(console.error);
  }, []);

  // Load events when filters/page change
  useEffect(() => {
    setLoading(true);
    const params: Record<string, string> = {
      page: String(page),
      per_page: "20",
    };
    if (debouncedQ) params.q = debouncedQ;
    if (filters.category) params.category = filters.category;
    if (filters.borough) params.borough = filters.borough;
    if (filters.is_free) params.is_free = filters.is_free;
    if (filters.date_from) params.date_from = filters.date_from;
    if (filters.date_to) params.date_to = filters.date_to;

    fetchEvents(params)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [page, debouncedQ, filters.category, filters.borough, filters.is_free, filters.date_from, filters.date_to]);

  const handleFilterChange = useCallback(
    (partial: Partial<Filters>) => {
      setFilters((prev) => ({ ...prev, ...partial }));
      setPage(1);
      setExpanded({});
    },
    [],
  );

  const toggleRow = useCallback((id: string) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  const columns = useMemo<ColumnDef<Event>[]>(
    () => [
      {
        accessorKey: "start_time",
        header: "Date",
        cell: ({ getValue }) => {
          const v = getValue<string>();
          return (
            <div className="whitespace-nowrap">
              <div className="font-medium">{formatDate(v)}</div>
              <div className="text-xs text-gray-400">{formatTime(v)}</div>
            </div>
          );
        },
        size: 130,
      },
      {
        accessorKey: "title",
        header: "Event",
        cell: ({ getValue }) => (
          <span className="font-medium text-nyc-navy">{getValue<string>()}</span>
        ),
        size: 280,
      },
      {
        accessorKey: "venue",
        header: "Venue",
        cell: ({ getValue }) => (
          <span className="text-gray-600">{getValue<string>() || "—"}</span>
        ),
        size: 180,
      },
      {
        accessorKey: "borough",
        header: "Borough",
        cell: ({ getValue }) => {
          const v = getValue<string | null>();
          return v ? (
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
              {v}
            </span>
          ) : (
            <span className="text-gray-300">—</span>
          );
        },
        size: 120,
      },
      {
        accessorKey: "category",
        header: "Category",
        cell: ({ getValue }) => {
          const v = getValue<string | null>();
          return v ? (
            <span className="rounded-full bg-nyc-yellow/20 px-2 py-0.5 text-xs font-medium text-nyc-orange">
              {v}
            </span>
          ) : (
            <span className="text-gray-300">—</span>
          );
        },
        size: 120,
      },
      {
        id: "price",
        header: "Price",
        accessorFn: (row) => (row.is_free ? "Free" : row.price || "—"),
        cell: ({ row }) => {
          const event = row.original;
          return event.is_free ? (
            <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">
              Free
            </span>
          ) : (
            <span className="text-gray-600">{event.price || "—"}</span>
          );
        },
        size: 90,
      },
      {
        accessorKey: "source",
        header: "Source",
        cell: ({ getValue }) => (
          <span className="text-xs text-gray-400">{getValue<string>()}</span>
        ),
        size: 100,
      },
    ],
    [],
  );

  const table = useReactTable({
    data: data?.events ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualPagination: true,
    pageCount: data?.pages ?? 1,
  });

  return (
    <div className="mx-auto min-h-screen max-w-7xl px-4 py-6">
      {/* Header */}
      <header className="mb-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-nyc-navy text-lg text-nyc-yellow">
            &#x26A1;
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-nyc-navy">
              NYC Events Radar
            </h1>
            <p className="text-sm text-gray-500">
              Discover what&apos;s happening across the five boroughs
            </p>
          </div>
        </div>
      </header>

      {/* Stats */}
      <section className="mb-5">
        <StatsBar stats={stats} />
      </section>

      {/* Filters */}
      <section className="mb-4 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
        <FilterBar
          filters={filters}
          onChange={handleFilterChange}
          categories={categories}
        />
      </section>

      {/* Table */}
      <section className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id} className="border-b border-gray-200 bg-gray-50">
                  {hg.headers.map((header) => (
                    <th
                      key={header.id}
                      className="cursor-pointer select-none whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500 hover:text-gray-700"
                      style={{ width: header.getSize() }}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                      <SortIcon
                        dir={header.column.getIsSorted()}
                      />
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {loading && !data ? (
                <tr>
                  <td
                    colSpan={columns.length}
                    className="py-20 text-center text-gray-400"
                  >
                    Loading events...
                  </td>
                </tr>
              ) : data && data.events.length === 0 ? (
                <tr>
                  <td
                    colSpan={columns.length}
                    className="py-20 text-center text-gray-400"
                  >
                    No events match your filters.
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row: Row<Event>) => (
                  <TableRow
                    key={row.id}
                    row={row}
                    isExpanded={!!expanded[row.id]}
                    onToggle={() => toggleRow(row.id)}
                    colCount={columns.length}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && (
          <div className="border-t border-gray-200 px-4 py-3">
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              onPage={setPage}
            />
          </div>
        )}
      </section>
    </div>
  );
}

// --- Table Row (extracted for expand/collapse) ---

function TableRow({
  row,
  isExpanded,
  onToggle,
  colCount,
}: {
  row: Row<Event>;
  isExpanded: boolean;
  onToggle: () => void;
  colCount: number;
}) {
  return (
    <>
      <tr
        className="cursor-pointer border-b border-gray-100 transition-colors hover:bg-blue-50/40"
        onClick={onToggle}
      >
        {row.getVisibleCells().map((cell) => (
          <td key={cell.id} className="px-4 py-3">
            {flexRender(cell.column.columnDef.cell, cell.getContext())}
          </td>
        ))}
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={colCount} className="p-0">
            <EventDetail event={row.original} />
          </td>
        </tr>
      )}
    </>
  );
}
