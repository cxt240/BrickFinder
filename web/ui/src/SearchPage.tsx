import { useState } from "react";
import { Link } from "react-router-dom";
import { api, type SearchHit } from "./api";
import { useSearchSession } from "./SearchSession";

export function SearchPage() {
  const session = useSearchSession();
  const canSearch = Boolean(session.file);

  return (
    <div className="grid">
      <section className="card">
        <h2>Find the page</h2>
        <p className="mono">Photograph a loose brick or a still-together chunk. Best from a roughly isometric angle.</p>
        <div className="controls">
          <input
            type="file"
            accept="image/*,.heic,.heif,image/heic,image/heif"
            capture="environment"
            onChange={(event) => {
              const next = event.target.files?.[0];
              if (!next) return;
              session.setFile(next);
            }}
          />
          <select value={session.kind} onChange={(event) => session.setKind(event.target.value)}>
            <option value="">Auto detect</option>
            <option value="subassembly">Subassembly</option>
            <option value="loose_part">Loose part</option>
          </select>
          <button
            className="button primary"
            disabled={!canSearch || session.busy}
            onClick={async () => {
              if (!session.file) return;
              session.setBusy(true);
              session.setError(null);
              try {
                session.setResult(await api.search(session.file, session.kind || null));
              } catch (err) {
                session.setError(err instanceof Error ? err.message : "Search failed");
              } finally {
                session.setBusy(false);
              }
            }}
          >
            {session.busy ? "Matching…" : "Search"}
          </button>
        </div>
        {session.preview ? (
          <img className="preview" src={session.preview} alt="Query preview" />
        ) : session.file ? (
          <div className="drop">Decoding photo…</div>
        ) : session.fileName ? (
          <div className="drop">Last photo: {session.fileName}. Choose the file again only if you need a new search.</div>
        ) : (
          <div className="drop">Drop a photo or use the camera</div>
        )}
        {session.error ? <p className="error">{session.error}</p> : null}
      </section>

      {session.result ? (
        <section className="card">
          <h3>
            {session.result.results.length} guesses · treated as {session.result.kind.replace("_", " ")}
          </h3>
          {session.result.results.length === 0 ? (
            <p className="mono">No indexed views yet. Run ingest, then search again.</p>
          ) : (
            <div className="results">
              {session.result.results.map((hit) => (
                <ResultCard
                  key={hit.region_id}
                  hit={hit}
                  confirmed={session.confirmed === hit.page_id}
                  onConfirm={async () => {
                    await api.feedback(session.result!.query_id, hit.page_id);
                    session.setConfirmed(hit.page_id);
                  }}
                />
              ))}
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}

function ResultCard({
  hit,
  confirmed,
  onConfirm,
}: {
  hit: SearchHit;
  confirmed: boolean;
  onConfirm: () => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  return (
    <article className="result">
      <Link to={`/pages/${hit.page_id}`}>
        <img src={hit.crop_path_url || hit.thumb_path_url} alt={`Book ${hit.book_number} page ${hit.page_number}`} />
      </Link>
      <div className="meta">
        <strong>
          {hit.set_name} · book {hit.book_number} · p.{hit.page_number}
        </strong>
        <span>
          score {hit.score.toFixed(3)}
          {hit.step_number ? ` · step ${hit.step_number}` : ""}
          {hit.bag_number ? ` · bag ${hit.bag_number}` : ""}
        </span>
        <button
          className="button ghost"
          disabled={saving || confirmed}
          onClick={async () => {
            setSaving(true);
            try {
              await onConfirm();
            } finally {
              setSaving(false);
            }
          }}
        >
          {confirmed ? "Marked correct" : "This is the page"}
        </button>
      </div>
    </article>
  );
}
