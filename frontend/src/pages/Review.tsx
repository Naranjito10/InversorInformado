import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  approveListing,
  fetchPendingReview,
  keepNewListing,
  rejectListing,
} from "../services/api";
import type { OriginalListingInfo, PendingListing } from "../services/api";

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

type ListingSnippet = Pick<
  PendingListing,
  "titulo" | "precio_venta" | "metros_cuadrados" | "habitaciones" | "municipio" | "barrio" | "primera_deteccion" | "url"
>;

function ListingDetails({ listing }: { listing: ListingSnippet | OriginalListingInfo }) {
  return (
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
      {listing.url && (
        <a
          href={listing.url}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-blue-500 hover:underline truncate"
        >
          Ver anuncio →
        </a>
      )}
    </div>
  );
}

function ReviewCard({ listing }: { listing: PendingListing }) {
  const qc = useQueryClient();
  const removeFromCache = () => {
    qc.setQueryData<PendingListing[]>(["pending-review"], (old) =>
      old?.filter((item) => item.id !== listing.id) ?? []
    );
    qc.invalidateQueries({ queryKey: ["pending-review"] });
    qc.invalidateQueries({ queryKey: ["pending-count"] });
  };

  const approveMutation = useMutation({
    mutationFn: () => approveListing(listing.id),
    onSuccess: removeFromCache,
  });
  const rejectMutation = useMutation({
    mutationFn: () => rejectListing(listing.id),
    onSuccess: removeFromCache,
  });
  const keepNewMutation = useMutation({
    mutationFn: () => keepNewListing(listing.id),
    onSuccess: removeFromCache,
  });

  const isPending =
    approveMutation.isPending || rejectMutation.isPending || keepNewMutation.isPending;

  return (
    <div className="bg-white border border-yellow-200 rounded-xl p-5 shadow-sm flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-yellow-700 bg-yellow-100 px-2 py-0.5 rounded-full">
          ⚠️ Posible duplicado
        </span>
        <span className="text-xs text-gray-400 capitalize">{listing.fuente}</span>
      </div>

      <div className="flex flex-col gap-1.5">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Anuncio nuevo</p>
        <ListingDetails listing={listing} />
      </div>

      <div className="border-t border-dashed border-gray-200" />

      <div className="flex flex-col gap-1.5">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Original en BD</p>
        {listing.original_info ? (
          <ListingDetails listing={listing.original_info} />
        ) : (
          <p className="text-xs text-gray-300 italic">No se encontró el original</p>
        )}
      </div>

      <div className="flex flex-col gap-2 mt-auto">
        <button
          onClick={() => approveMutation.mutate()}
          disabled={isPending}
          className="w-full py-2 text-sm border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {approveMutation.isPending ? "…" : "↔ Dejar los dos"}
        </button>
        <div className="flex gap-2">
          <button
            onClick={() => rejectMutation.mutate()}
            disabled={isPending}
            className="flex-1 py-2 text-sm border border-gray-200 text-gray-500 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {rejectMutation.isPending ? "…" : "← Dejar el antiguo"}
          </button>
          <button
            onClick={() => keepNewMutation.mutate()}
            disabled={isPending}
            className="flex-1 py-2 text-sm bg-blue-700 text-white rounded-lg hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {keepNewMutation.isPending ? "…" : "→ Dejar el nuevo"}
          </button>
        </div>
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
