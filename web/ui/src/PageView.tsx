import { useEffect, useState, type CSSProperties } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, type PageCrop, type PageDetail } from "./api";

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
}

function cropKindClass(kind: string): string {
  if (kind === "assembly" || kind === "callout" || kind === "inventory") {
    return `kind-${kind}`;
  }
  return "kind-other";
}

function overlayStyle(crop: PageCrop, page: PageDetail): CSSProperties | undefined {
  const width = page.width ?? 0;
  const height = page.height ?? 0;
  if (!width || !height) return undefined;
  return {
    left: `${(crop.bbox_x / width) * 100}%`,
    top: `${(crop.bbox_y / height) * 100}%`,
    width: `${(crop.bbox_w / width) * 100}%`,
    height: `${(crop.bbox_h / height) * 100}%`,
  };
}

export function PageView() {
  const { pageId } = useParams();
  const navigate = useNavigate();
  const [page, setPage] = useState<PageDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedCropId, setSelectedCropId] = useState<number | null>(null);

  useEffect(() => {
    if (!pageId) return;
    let cancelled = false;
    setError(null);
    setLoading(true);
    setSelectedCropId(null);
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

  function selectCrop(id: number) {
    setSelectedCropId((current) => (current === id ? null : id));
  }

  if (error) return <p className="error">{error}</p>;
  if (!page) return <p className="mono">Loading page…</p>;

  const crops = page.crops ?? [];
  const canOverlay = Boolean(page.width && page.height);
  const selectedCrop = selectedCropId == null ? null : crops.find((crop) => crop.id === selectedCropId) ?? null;

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
          <div className="page-raster">
            <img src={page.raster_path_url} alt={`Instruction page ${page.page_number}`} />
            {canOverlay && selectedCrop ? (
              <div className="page-overlays">
                <button
                  type="button"
                  className={`region-overlay ${cropKindClass(selectedCrop.kind)} is-selected`}
                  style={overlayStyle(selectedCrop, page)}
                  aria-label={`Hide ${selectedCrop.kind} region`}
                  aria-pressed="true"
                  onClick={() => setSelectedCropId(null)}
                >
                  <span className="region-overlay-label">{selectedCrop.kind}</span>
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </section>
      {crops.length ? (
        <section className="card">
          <h3>Indexed views</h3>
          <div className="crop-grid">
            {crops.map((crop) => (
              <button
                key={crop.id}
                type="button"
                className={`crop-card ${cropKindClass(crop.kind)}${
                  selectedCropId === crop.id ? " is-selected" : ""
                }`}
                onClick={() => selectCrop(crop.id)}
                aria-pressed={selectedCropId === crop.id}
              >
                <span className="crop-card-frame">
                  <img src={crop.crop_path_url} alt="" />
                </span>
                <span className="crop-card-kind">{crop.kind}</span>
              </button>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
