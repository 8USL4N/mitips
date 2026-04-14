import { NavLink, Route, Routes } from "react-router-dom";
import SolverPage from "./pages/SolverPage";
import EditorPage from "./pages/EditorPage";

export default function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>Экспертная система</h1>
        </div>
        <nav className="nav-tabs">
          <NavLink to="/" end>
            Решатель
          </NavLink>
          <NavLink to="/editor">Редактор знаний</NavLink>
        </nav>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<SolverPage />} />
          <Route path="/editor" element={<EditorPage />} />
        </Routes>
      </main>
    </div>
  );
}
