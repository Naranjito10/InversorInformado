import { useState, useEffect } from "react";
import type { Listing } from "../types";

interface Props {
  listings: Listing[];
  isLoading: boolean;
}

const PAGE_SIZE = 10;

const LABEL_STYLES: Record<string, string> = {
  alto: "bg-green-100 text-green-800",
  medio: "bg-yellow-100 text-yellow-800",
  normal: "bg-gray-100 text-gray-600",
  incompleto: "bg-red-100 text-red-700",
};

const fmt = (n?: number) =>
  n != null ? n.toLocaleString("es-ES") + " €" : "—";

export default function ListingsTable({ listings, isLoading }: Props) {
  const [page, setPage] = useState(1);

  // Resetear a página 1 cuando cambia el listado (nuevo filtro)
  useEffect(() => {
    setPage(1);
  }, [listings]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-20 text-gray-400">
        Cargando anuncios...
      </div>
    );
  }

  if (!listings.length) {
    return (
      <div className="flex justify-center items-center py-20 text-gray-400">
        No hay anuncios con estos filtros.
      </div>
    );
  }

  const totalPages = Math.ceil(listings.length / PAGE_SIZE);
  const start = (page - 1) * PAGE_SIZE;
  const end = Math.min(start + PAGE_SIZE, listings.length);
  const paginated = listings.slice(start, end);

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto rounded-xl border border-gray-200 shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              <th className="px-4 py-3 text-left">Score</th>
              <th className="px-4 py-3 text-left">Portal</th>
              <th className="px-4 py-3 text-left">Título</th>
              <th className="px-4 py-3 text-left">Precio</th>
              <th className="px-4 py-3 text-left">€/m²</th>
              <th className="px-4 py-3 text-left">m²</th>
              <th className="px-4 py-3 text-left">Hab.</th>
              <th className="px-4 py-3 text-left">Planta</th>
              <th className="px-4 py-3 text-left">Zona</th>
              <th className="px-4 py-3 text-left">Rent. bruta</th>
              <th className="px-4 py-3 text-left">Bajada</th>
              <th className="px-4 py-3 text-left">Días</th>
              <th className="px-4 py-3 text-left">Enlace</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {paginated.map((l, i) => (
              <tr key={l.id ?? i} className="bg-white hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3">
                  <span
                    className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${
                      LABEL_STYLES[l.score_label ?? "normal"] ?? LABEL_STYLES.normal
                    }`}
                  >
                    {l.score ?? "—"}
                  </span>
                </td>
                <td className="px-4 py-3 capitalize text-gray-600">{l.fuente}</td>
                <td className="px-4 py-3 max-w-xs truncate text-gray-800">{l.titulo ?? "—"}</td>
                <td className="px-4 py-3 font-medium text-gray-800">{fmt(l.precio_venta)}</td>
                <td className="px-4 py-3 text-gray-600">
                  {l.precio_m2 != null ? l.precio_m2.toLocaleString("es-ES") + " €/m²" : "—"}
                </td>
                <td className="px-4 py-3 text-gray-600">{l.metros_cuadrados ?? "—"}</td>
                <td className="px-4 py-3 text-gray-600">{l.habitaciones ?? "—"}</td>
                <td className="px-4 py-3 text-gray-600">{l.planta ?? "—"}</td>
                <td className="px-4 py-3 text-gray-600">
                  {[l.barrio, l.municipio].filter(Boolean).join(", ") || "—"}
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {l.rentabilidad_bruta != null ? `${l.rentabilidad_bruta}%` : "—"}
                </td>
                <td className="px-4 py-3">
                  {l.bajada_precio ? (
                    <span className="text-purple-600 font-medium">↓ Bajada</span>
                  ) : (
                    <span className="text-gray-300">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-600">{l.dias_en_mercado ?? "—"}</td>
                <td className="px-4 py-3">
                  <a
                    href={l.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    Ver →
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      <div className="flex items-center justify-between px-1">
        <p className="text-xs text-gray-400">
          Mostrando {start + 1}–{end} de {listings.length} anuncios
        </p>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            ← Anterior
          </button>

          {/* Números de página */}
          <div className="flex gap-1">
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
              .reduce<(number | "...")[]>((acc, p, idx, arr) => {
                if (idx > 0 && (arr[idx - 1] as number) + 1 < p) acc.push("...");
                acc.push(p);
                return acc;
              }, [])
              .map((item, idx) =>
                item === "..." ? (
                  <span key={`ellipsis-${idx}`} className="px-2 py-1.5 text-xs text-gray-400">
                    …
                  </span>
                ) : (
                  <button
                    key={item}
                    onClick={() => setPage(item as number)}
                    className={`px-3 py-1.5 text-xs border rounded-lg transition-colors ${
                      page === item
                        ? "bg-blue-600 text-white border-blue-600"
                        : "border-gray-300 text-gray-600 hover:bg-gray-50"
                    }`}
                  >
                    {item}
                  </button>
                )
              )}
          </div>

          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Siguiente →
          </button>
        </div>
      </div>
    </div>
  );
}