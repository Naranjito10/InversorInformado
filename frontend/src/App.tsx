import { Routes, Route, NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import Dashboard from "./pages/Dashboard";
import SearchForm from "./pages/SearchForm";
import Monitor from "./pages/Monitor";
import Review from "./pages/Review";
import Carga from "./pages/Carga";
import { fetchPendingReview } from "./services/api";

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

export default function App() {
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
        <NavLink
          to="/buscar"
          className={({ isActive }) =>
            isActive ? "text-blue-600 font-medium" : "text-gray-500 hover:text-gray-800"
          }
        >
          Buscar
        </NavLink>
        <NavLink
          to="/carga"
          className={({ isActive }) =>
            isActive ? "text-blue-600 font-medium" : "text-gray-500 hover:text-gray-800"
          }
        >
          Carga
        </NavLink>
        <NavLink
          to="/revision"
          className={({ isActive }) =>
            `flex items-center ${isActive ? "text-blue-600 font-medium" : "text-gray-500 hover:text-gray-800"}`
          }
        >
          Revisión
          <PendingBadge />
        </NavLink>
        <NavLink
          to="/monitor"
          className={({ isActive }) =>
            isActive ? "text-blue-600 font-medium" : "text-gray-500 hover:text-gray-800"
          }
        >
          Monitor
        </NavLink>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/buscar" element={<SearchForm />} />
          <Route path="/monitor" element={<Monitor />} />
          <Route path="/carga" element={<Carga />} />
          <Route path="/revision" element={<Review />} />
        </Routes>
      </main>
    </div>
  );
}