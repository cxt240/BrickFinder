import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { SearchResponse } from "./api";

const STORAGE_KEY = "brickfinder.search";

type StoredSearch = {
  kind: string;
  result: SearchResponse | null;
  confirmed: number | null;
  fileName: string | null;
};

function readStored(): StoredSearch {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { kind: "", result: null, confirmed: null, fileName: null };
    }
    return JSON.parse(raw) as StoredSearch;
  } catch {
    return { kind: "", result: null, confirmed: null, fileName: null };
  }
}

function patchStored(patch: Partial<StoredSearch>) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ ...readStored(), ...patch }));
}

type SearchContextValue = {
  file: File | null;
  preview: string | null;
  kind: string;
  result: SearchResponse | null;
  error: string | null;
  busy: boolean;
  confirmed: number | null;
  fileName: string | null;
  setKind: (kind: string) => void;
  setError: (error: string | null) => void;
  setBusy: (busy: boolean) => void;
  setResult: (result: SearchResponse | null) => void;
  setConfirmed: (pageId: number | null) => void;
  setFile: (file: File | null) => void;
};

const SearchContext = createContext<SearchContextValue | null>(null);

export function SearchProvider({ children }: { children: ReactNode }) {
  const initial = readStored();
  const [file, setFileState] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [kind, setKindState] = useState(initial.kind);
  const [result, setResultState] = useState<SearchResponse | null>(initial.result);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmedState] = useState<number | null>(initial.confirmed);
  const [fileName, setFileName] = useState<string | null>(initial.fileName);

  const setKind = useCallback((next: string) => {
    setKindState(next);
    patchStored({ kind: next });
  }, []);

  const setResult = useCallback((next: SearchResponse | null) => {
    setResultState(next);
    patchStored({ result: next });
  }, []);

  const setConfirmed = useCallback((pageId: number | null) => {
    setConfirmedState(pageId);
    patchStored({ confirmed: pageId });
  }, []);

  const setFile = useCallback((next: File | null) => {
    setFileState(next);
    setFileName(next?.name ?? null);
    setResultState(null);
    setConfirmedState(null);
    setError(null);
    setPreview((current) => {
      if (current) URL.revokeObjectURL(current);
      return next ? URL.createObjectURL(next) : null;
    });
    patchStored({ result: null, confirmed: null, fileName: next?.name ?? null });
  }, []);

  const value = useMemo<SearchContextValue>(
    () => ({
      file,
      preview,
      kind,
      result,
      error,
      busy,
      confirmed,
      fileName,
      setKind,
      setError,
      setBusy,
      setResult,
      setConfirmed,
      setFile,
    }),
    [file, preview, kind, result, error, busy, confirmed, fileName, setKind, setResult, setConfirmed, setFile],
  );

  return <SearchContext.Provider value={value}>{children}</SearchContext.Provider>;
}

export function useSearchSession() {
  const ctx = useContext(SearchContext);
  if (!ctx) {
    throw new Error("useSearchSession must be used within SearchProvider");
  }
  return ctx;
}
