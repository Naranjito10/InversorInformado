import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchReports } from "../services/api";
import type { Report } from "../types";

function ScoreBadge({ score }: { score?: number }) {
  if (score === undefined || score === null) return null;
  const color =
    score >= 80 ? "bg-green-100 text-green-700" :
    score >= 60 ? "bg-yellow-100 text-yellow-700" :
    "bg-red-100 text-red-700";
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {score}/100
    </span>
  );
}

export default function Informes() {
  const navigate = useNavigate();
  const { data: reports = [], isLoading } = useQuery<Report[]>({
    queryKey: ["reports"],
    queryFn: fetchReports,
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Informes de análisis</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Análisis de inversión generados para propiedades concretas
          </p>
        </div>
        <button
          onClick={() => navigate("/informes/nuevo")}
          className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          + Nuevo análisis
        </button>
      </div>

      {isLoading && (
        <p className="text-sm text-gray-400">Cargando informes...</p>
      )}

      {!isLoading && reports.length === 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-10 text-center shadow-sm">
          <p className="text-gray-400 text-sm">Aún no hay informes generados.</p>
          <button
            onClick={() => navigate("/informes/nuevo")}
            className="mt-4 bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Crear el primero
          </button>
        </div>
      )}

      {reports.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Propiedad</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Ubicación</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Score</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Fecha</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {reports.map((r) => (
                <tr
                  key={r.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/informes/${r.id}`)}
                >
                  <td className="px-4 py-3 font-medium text-gray-900">{r.title}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {r.data?.property?.barrio}, {r.data?.property?.municipio}
                  </td>
                  <td className="px-4 py-3">
                    <ScoreBadge score={r.data?.scores?.global} />
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(r.created_at).toLocaleDateString("es-ES")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
