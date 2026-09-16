import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, type BookSummary, type PageSummary, type SetSummary } from "./api";

export function BrowsePage() {
  const [params, setParams] = useSearchParams();
  const setId = params.get("set") ? Number(params.get("set")) : undefined;
  const bookId = params.get("book") ? Number(params.get("book")) : undefined;
  const [sets, setSets] = useState<SetSummary[]>([]);
  const [books, setBooks] = useState<BookSummary[]>([]);
  const [pages, setPages] = useState<PageSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.catalog.sets().then(setSets).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    api.catalog.books(setId).then(setBooks).catch((err) => setError(err.message));
  }, [setId]);

  useEffect(() => {
    if (!bookId) {
      setPages([]);
      return;
    }
    api.catalog.bookPages(bookId).then(setPages).catch((err) => setError(err.message));
  }, [bookId]);

  return (
    <div className="grid">
      <section className="card">
        <h2>Sets</h2>
        {sets.length === 0 ? <p className="mono">No indexed sets yet. Run ingest first.</p> : null}
        <div className="controls">
          {sets.map((set) => (
            <button
              key={set.id}
              className={`button ${setId === set.id ? "primary" : ""}`}
              onClick={() => setParams({ set: String(set.id) })}
            >
              {set.name} · {set.page_count} pages
            </button>
          ))}
        </div>
      </section>

      <section className="card">
        <h3>Books</h3>
        {books.map((book) => (
          <button
            key={book.id}
            className={`button ${bookId === book.id ? "primary" : "ghost"}`}
            onClick={() =>
              setParams({
                ...(setId ? { set: String(setId) } : { set: String(book.set_id) }),
                book: String(book.id),
              })
            }
          >
            Book {book.book_number} · {book.page_count} pages
            {book.source_missing ? " · source missing" : ""}
          </button>
        ))}
      </section>

      {pages.length ? (
        <section className="card">
          <h3>Pages</h3>
          <div className="thumbs">
            {pages.map((page) => (
              <Link className="thumb" key={page.id} to={`/pages/${page.id}`}>
                <img src={page.thumb_path_url} alt={`Page ${page.page_number}`} />
                <span>
                  p.{page.page_number}
                  {page.step_number ? ` · step ${page.step_number}` : ""}
                </span>
              </Link>
            ))}
          </div>
        </section>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}
