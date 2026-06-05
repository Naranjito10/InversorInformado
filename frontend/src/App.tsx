import { Routes, Route, NavLink, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useRef, useState, useEffect } from "react";
import ScraperToast from "./components/ScraperToast";
import Dashboard from "./pages/Dashboard";
import SearchForm from "./pages/SearchForm";
import Monitor from "./pages/Monitor";
import Review from "./pages/Review";
import Carga from "./pages/Carga";
import Informes from "./pages/Informes";
import InformeNuevo from "./pages/InformeNuevo";
import InformeDetalle from "./pages/InformeDetalle";
import Comunicaciones from "./pages/Comunicaciones";
import Login from "./pages/Login";
import ProtectedRoute from "./components/ProtectedRoute";
import { fetchPendingReview, logout } from "./services/api";

function PendingBadge() {
  const { data } = useQuery({
    queryKey: ["pending-review"],
    queryFn: fetchPendingReview,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
  const count = data?.length ?? 0;
  if (count === 0) return null;
  return (
    <span className="ml-1.5 bg-yellow-400 text-yellow-900 text-xs font-bold px-1.5 py-0.5 rounded-full">
      {count}
    </span>
  );
}

function CargaDropdown() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const isActive = location.pathname === "/buscar" || location.pathname === "/carga";

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1 transition-colors ${
          isActive ? "text-blue-600 font-medium" : "text-gray-500 hover:text-gray-800"
        }`}
      >
        Carga
        <svg className={`w-3.5 h-3.5 transition-transform ${open ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-2 w-36 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50">
          <NavLink
            to="/buscar"
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              `block px-4 py-2 text-sm ${isActive ? "text-blue-600 font-medium" : "text-gray-700 hover:bg-gray-50"}`
            }
          >
            Automática
          </NavLink>
          <NavLink
            to="/carga"
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              `block px-4 py-2 text-sm ${isActive ? "text-blue-600 font-medium" : "text-gray-700 hover:bg-gray-50"}`
            }
          >
            Manual
          </NavLink>
        </div>
      )}
    </div>
  );
}

function MonitoreoDropdown() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const isActive = location.pathname === "/monitor" || location.pathname === "/revision";

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1 transition-colors ${
          isActive ? "text-blue-600 font-medium" : "text-gray-500 hover:text-gray-800"
        }`}
      >
        Monitoreo
        <PendingBadge />
        <svg className={`w-3.5 h-3.5 transition-transform ${open ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-2 w-36 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50">
          <NavLink
            to="/monitor"
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              `block px-4 py-2 text-sm ${isActive ? "text-blue-600 font-medium" : "text-gray-700 hover:bg-gray-50"}`
            }
          >
            Logs
          </NavLink>
          <NavLink
            to="/revision"
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              `flex items-center px-4 py-2 text-sm ${isActive ? "text-blue-600 font-medium" : "text-gray-700 hover:bg-gray-50"}`
            }
          >
            Revisión
            <PendingBadge />
          </NavLink>
        </div>
      )}
    </div>
  );
}

function AppLayout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-8 shadow-sm">
        <span className="font-bold text-lg text-blue-700">Inversor Informado</span>
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            isActive ? "text-blue-600 font-medium" : "text-gray-500 hover:text-gray-800"
          }
        >
          Dashboard
        </NavLink>
        <CargaDropdown />
        <MonitoreoDropdown />
        <NavLink
          to="/informes"
          className={({ isActive }) =>
            isActive ? "text-blue-600 font-medium" : "text-gray-500 hover:text-gray-800"
          }
        >
          Informes
        </NavLink>
        <NavLink
          to="/comunicaciones"
          className={({ isActive }) =>
            isActive ? "text-blue-600 font-medium" : "text-gray-500 hover:text-gray-800"
          }
        >
          Comunicaciones
        </NavLink>

        <button
          onClick={logout}
          className="ml-auto text-xs text-gray-400 hover:text-gray-700 transition-colors"
        >
          Cerrar sesión
        </button>
      </nav>

      <ScraperToast />
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/buscar" element={<SearchForm />} />
          <Route path="/monitor" element={<Monitor />} />
          <Route path="/carga" element={<Carga />} />
          <Route path="/revision" element={<Review />} />
          <Route path="/informes" element={<Informes />} />
          <Route path="/informes/nuevo" element={<InformeNuevo />} />
          <Route path="/informes/:id" element={<InformeDetalle />} />
          <Route path="/comunicaciones" element={<Comunicaciones />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
