import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, type PageDetail } from "./api";

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
}

export function PageView() {
  const { pageId } = useParams();
  const navigate = useNavigate();
  const [page, setPage] = useState<PageDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!pageId) return;
    let cancelled = false;
    setError(null);
    setLoading(true);
    api.catalog
      .page(Number(pageId))
      .then((data) => {
        if (!cancelled) setPage(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setPage(null);
          setError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [pageId]);

  const prevId = loading || !page ? null : page.prev_page_id;
  const nextId = loading || !page ? null : page.next_page_id;

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      if (isEditableTarget(event.target)) return;
      if (event.key === "ArrowLeft" && prevId != null) {
        event.preventDefault();
        navigate(`/pages/${prevId}`);
        return;
      }
      if (event.key === "ArrowRight" && nextId != null) {
        event.preventDefault();
        navigate(`/pages/${nextId}`);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [navigate, prevId, nextId]);

  if (error) return <p className="error">{error}</p>;
  if (!page) return <p className="mono">Loading page…</p>;

  return (
    <div className="grid">
      <section className="card">
        <p className="mono">
          <Link to={`/books?book=${page.book_id}`}>Back to book {page.book_number}</Link>
        </p>
        <h2>
          {page.set_name} · book {page.book_number} · page {page.page_number}
        </h2>
        <p className="page-meta mono">
          {page.step_number ? `step ${page.step_number}` : "step unknown"}
          {page.bag_number ? ` · bag ${page.bag_number}` : ""}
        </p>
        <nav className="page-nav" aria-label="Instruction page">
          {prevId ? (
            <Link className="button" to={`/pages/${prevId}`}>
              Previous page
            </Link>
          ) : (
            <span className="button" aria-disabled="true">
              Previous page
            </span>
          )}
          <span className="mono">page {page.page_number}</span>
          {nextId ? (
            <Link className="button primary" to={`/pages/${nextId}`}>
              Next page
            </Link>
          ) : (
            <span className="button" aria-disabled="true">
              Next page
            </span>
          )}
        </nav>
        <div className="page-hero">
          <img src={page.raster_path_url} alt={`Instruction page ${page.page_number}`} />
        </div>
      </section>
      {page.crops?.length ? (
        <section className="card">
          <h3>Indexed views</h3>
          <div className="thumbs">
            {page.crops.map((crop, index) => (
              <article className="thumb" key={`${crop.kind}-${index}`}>
                <img src={crop.crop_path_url} alt={crop.kind} />
                <span>{crop.kind}</span>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
