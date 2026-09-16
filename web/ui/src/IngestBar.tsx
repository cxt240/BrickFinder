import { useEffect, useState } from "react";
import { api, type IngestStatus } from "./api";

export function IngestBar() {
  const [status, setStatus] = useState<IngestStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const next = await api.ingest.status();
        if (!cancelled) setStatus(next);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Status failed");
      }
    };
    tick();
    const id = window.setInterval(tick, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const running = status?.state === "running";
  const filePct =
    status && status.files_total > 0 ? Math.round((status.files_done / status.files_total) * 100) : 0;
  const pagePct =
    status && status.pages_total > 0 ? Math.round((status.pages_done / status.pages_total) * 100) : 0;

  return (
    <section className="ingest">
      <div className="ingest-row">
        <div>
          <strong>Instruction index</strong>
          <div className="mono">
            {status ? `${status.state}${status.current_file ? ` · ${status.current_file}` : ""}` : "checking…"}
          </div>
          {status?.message ? <div className="mono">{status.message}</div> : null}
          {status?.error || error ? <div className="error">{status?.error || error}</div> : null}
        </div>
        <button
          className="button primary"
          disabled={busy || running}
          onClick={async () => {
            setBusy(true);
            setError(null);
            try {
              setStatus(await api.ingest.run());
            } catch (err) {
              setError(err instanceof Error ? err.message : "Ingest failed to start");
            } finally {
              setBusy(false);
            }
          }}
        >
          {running ? "Indexing…" : "Index instructions"}
        </button>
      </div>
      <div className="progress" title="Files">
        <span style={{ width: `${filePct}%` }} />
      </div>
      <div className="progress" title="Pages in current file">
        <span style={{ width: `${pagePct}%` }} />
      </div>
    </section>
  );
}
