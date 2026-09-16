import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { BrowsePage } from "./BrowsePage";
import { IngestBar } from "./IngestBar";
import { PageView } from "./PageView";
import { SearchPage } from "./SearchPage";
import { SearchProvider } from "./SearchSession";

export function App() {
  return (
    <SearchProvider>
      <div className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>BrickFinder</h1>
          <p>Match a photo to a page in your indexed instruction books. Upload a file or use the camera.</p>
        </div>
        <nav className="nav">
          <NavLink to="/" end>
            Search
          </NavLink>
          <NavLink to="/books">Books</NavLink>
        </nav>
      </header>
      <IngestBar />
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/books" element={<BrowsePage />} />
        <Route path="/pages/:pageId" element={<PageView />} />
        <Route path="/browse" element={<Navigate to="/books" replace />} />
      </Routes>
    </div>
    </SearchProvider>
  );
}
