import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  approveListing,
  fetchPendingReview,
  rejectListing,
} from "../services/api";
import type { PendingListing } from "../services/api";

function formatDate(ts?: string): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return ts;
  }
}

function ReviewCard({ listing }: { listing: PendingListing }) {
  const qc = useQueryClient();

  const invalidate = () => qc.invalidateQueries({ queryKey: ["pending-review"] });

  const approveMutation = useMutation({
    mutationFn: () => approveListing(listing.id),
    onSuccess: invalidate,
  });

  const rejectMutation = useMutation({
    mutationFn: () => rejectListing(listing.id),
    onSuccess: invalidate,
  });

  const isPending = approveMutation.isPending || rejectMutation.isPending;

  return (
    <div className="bg-white border border-yellow-200 rounded-xl p-5 shadow-sm flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-yellow-700 bg-yellow-100 px-2 py-0.5 rounded-full">
          ⚠️ Posible duplicado
        </span>
        <span className="text-xs text-gray-400 capitalize">{listing.fuente}</span>
      </div>

      <div className="flex flex-col gap-1.5">
        {listing.titulo && (
          <p className="text-sm font-medium text-gray-800 truncate">{listing.titulo}</p>
        )}
        <div className="flex flex-wrap gap-3 text-xs text-gray-500">
          {listing.precio_venta != null && (
            <span className="font-semibold text-gray-700">
              {listing.precio_venta.toLocaleString("es-ES")} €
            </span>
          )}
          {listing.metros_cuadrados != null && <span>{listing.metros_cuadrados} m²</span>}
          {listing.habitaciones != null && <span>{listing.habitaciones} hab.</span>}
          {listing.municipio && (
            <span>
              {listing.municipio}
              {listing.barrio ? ` · ${listing.barrio}` : ""}
            </span>
          )}
          <span className="text-gray-300">Detectado: {formatDate(listing.primera_deteccion)}</span>
        </div>
        <a
          href={listing.url}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-blue-500 hover:underline truncate"
        >
          Ver anuncio nuevo →
        </a>
      </div>

      {listing.duplicate_candidate_of && (
        <div className="bg-gray-50 border border-gray-100 rounded-lg px-3 py-2 flex flex-col gap-1">
          <p className="text-xs text-gray-400 font-medium">Posible original en BD:</p>
          <a
            href={listing.duplicate_candidate_of}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-blue-500 hover:underline truncate"
          >
            {listing.duplicate_candidate_of}
          </a>
        </div>
      )}

      <div className="flex gap-2 mt-auto">
        <button
          onClick={() => approveMutation.mutate()}
          disabled={isPending}
          className="flex-1 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {approveMutation.isPending ? "…" : "✓ Aprobar"}
        </button>
        <button
          onClick={() => rejectMutation.mutate()}
          disabled={isPending}
          className="flex-1 py-2 text-sm border border-red-300 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {rejectMutation.isPending ? "…" : "✗ Rechazar"}
        </button>
      </div>
    </div>
  );
}

export default function Review() {
  const query = useQuery({
    queryKey: ["pending-review"],
    queryFn: fetchPendingReview,
    refetchInterval: 60_000,
  });

  const items = query.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Revisión de duplicados</h1>
        <p className="text-sm text-gray-400 mt-1">
          Anuncios detectados como posibles duplicados que requieren aprobación manual
        </p>
      </div>

      {query.isLoading ? (
        <p className="text-sm text-gray-400">Cargando…</p>
      ) : query.isError ? (
        <p className="text-sm text-red-500">Error al cargar los anuncios pendientes.</p>
      ) : items.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
          <p className="text-gray-400 text-sm">Sin anuncios pendientes de revisión</p>
          <p className="text-gray-300 text-xs mt-1">
            Los posibles duplicados aparecerán aquí durante el scraping
          </p>
        </div>
      ) : (
        <>
          <p className="text-sm text-gray-500">
            {items.length} anuncio{items.length !== 1 ? "s" : ""} pendiente
            {items.length !== 1 ? "s" : ""}
          </p>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {items.map((item) => (
              <ReviewCard key={item.id} listing={item} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
