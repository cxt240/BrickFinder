export type IngestStatus = {
  state: string;
  message: string;
  current_file: string;
  files_total: number;
  files_done: number;
  pages_done: number;
  pages_total: number;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
};

export type SetSummary = {
  id: number;
  set_num: string | null;
  name: string;
  book_count: number;
  page_count: number;
};

export type BookSummary = {
  id: number;
  set_id: number;
  set_name: string;
  book_number: number;
  source_relpath: string;
  page_count: number;
  source_missing: boolean;
  ingest_status: string;
};

export type PageSummary = {
  id: number;
  book_id: number;
  page_number: number;
  raster_path_url?: string;
  thumb_path_url?: string;
  step_number: number | null;
  bag_number: number | null;
};

export type PageDetail = PageSummary & {
  book_number: number;
  set_name: string;
  crops?: { kind: string; crop_path_url?: string }[];
  prev_page_id: number | null;
  next_page_id: number | null;
};

export type SearchHit = {
  score: number;
  kind: string;
  region_id: number;
  page_id: number;
  page_number: number;
  book_id: number;
  book_number: number;
  set_name: string;
  step_number: number | null;
  bag_number: number | null;
  raster_path_url?: string;
  thumb_path_url?: string;
  crop_path_url?: string;
};

export type SearchResponse = {
  query_id: number;
  kind: string;
  results: SearchHit[];
};

export type HealthStatus = {
  status: string;
  backend?: { status: string };
};

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => fetch("/api/health").then((r) => parse<HealthStatus>(r)),
  ingest: {
    status: () => fetch("/api/ingest/status").then((r) => parse<IngestStatus>(r)),
    run: () => fetch("/api/ingest/run", { method: "POST" }).then((r) => parse<IngestStatus>(r)),
  },
  search: (file: File, kind: string | null) => {
    const body = new FormData();
    body.append("image", file);
    if (kind) body.append("kind", kind);
    return fetch("/api/search", { method: "POST", body }).then((r) => parse<SearchResponse>(r));
  },
  catalog: {
    sets: () => fetch("/api/sets").then((r) => parse<SetSummary[]>(r)),
    books: (setId?: number) => {
      const suffix = setId ? `?set_id=${setId}` : "";
      return fetch(`/api/books${suffix}`).then((r) => parse<BookSummary[]>(r));
    },
    bookPages: (bookId: number) => fetch(`/api/books/${bookId}/pages`).then((r) => parse<PageSummary[]>(r)),
    page: (pageId: number) => fetch(`/api/pages/${pageId}`).then((r) => parse<PageDetail>(r)),
  },
  feedback: (queryId: number, pageId: number) =>
    fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query_id: queryId, correct_page_id: pageId }),
    }).then((r) => parse<{ id: number }>(r)),
};
