import { NavLink, Route, Routes } from "react-router-dom";
import SolverPage from "./pages/SolverPage";
import EditorPage from "./pages/EditorPage";

export default function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>Экспертная система</h1>
          <p>Учебный MVP по инфекционным заболеваниям</p>
        </div>
        <nav className="nav-tabs">
          <NavLink to="/" end>
            Решатель
          </NavLink>
          <NavLink to="/editor">Редактор знаний</NavLink>
        </nav>
      </header>

      <div className="disclaimer">
        Важно: система учебная, не предназначена для клинической диагностики.
      </div>

      <main>
        <Routes>
          <Route path="/" element={<SolverPage />} />
          <Route path="/editor" element={<EditorPage />} />
        </Routes>
      </main>
    </div>
  );
}
