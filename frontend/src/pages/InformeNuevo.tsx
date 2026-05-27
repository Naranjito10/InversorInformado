import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchListings, createReport, aiEstimateMarket } from "../services/api";
import type { Listing } from "../types";
import type { ReportData, ReportMarket, ReportBuilding, ReportAmenities, ReportScores } from "../types";

const EMPTY_MARKET: ReportMarket = {
  precio_m2_zona_min: 0, precio_m2_zona_medio: 0, precio_m2_zona_max: 0,
  alquiler_estimado_mes: 0, rentabilidad_bruta: 0, rentabilidad_neta: 0,
  rentabilidad_bruta_media_zona: 0, rentabilidad_neta_media_zona: 0,
  demanda_alquiler: "media", dias_hasta_alquiler: 0, ai_estimated: false,
};

const EMPTY_SCORES: ReportScores = {
  global: 0, global_grade: "", precio: 0, precio_grade: "",
  rentabilidad: 0, rentabilidad_grade: "", edificio: 0, edificio_grade: "",
  vecindario: 0, vecindario_grade: "", resumen: "",
};

export default function InformeNuevo() {
  const navigate = useNavigate();
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const [search, setSearch] = useState("");
  const [market, setMarket] = useState<ReportMarket>(EMPTY_MARKET);
  const [building, _setBuilding] = useState<ReportBuilding>({});
  const [amenities, _setAmenities] = useState<ReportAmenities>({});
  const [scores, setScores] = useState<ReportScores>(EMPTY_SCORES);
  const [verdict, setVerdict] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiEstimated, setAiEstimated] = useState(false);

  const { data: listings = [] } = useQuery<Listing[]>({
    queryKey: ["listings-search", search],
    queryFn: () => fetchListings({ limit: 20, ...(search ? { municipio: search } : {}) }),
    staleTime: 30_000,
  });

  const saveMutation = useMutation({
    mutationFn: () => {
      if (!selectedListing) throw new Error("Selecciona un piso");
      const data: ReportData = {
        property: {
          direccion: selectedListing.titulo ?? selectedListing.url,
          municipio: selectedListing.municipio ?? "",
          barrio: selectedListing.barrio ?? "",
          precio: selectedListing.precio_venta ?? 0,
          metros: selectedListing.metros_cuadrados ?? 0,
          habitaciones: selectedListing.habitaciones ?? 0,
          banos: selectedListing.banos ?? 0,
          estado: selectedListing.estado ?? "",
          url: selectedListing.url,
          cee: selectedListing.cee ?? undefined,
        },
        market,
        building,
        amenities,
        scores,
        verdict,
      };
      const title = `${data.property.barrio || data.property.municipio} · ${new Date().toLocaleDateString("es-ES")}`;
      return createReport({ title, property_id: selectedListing.id, data });
    },
    onSuccess: (report) => navigate(`/informes/${report.id}`),
  });

  const handleAiEstimate = async () => {
    if (!selectedListing) return;
    setAiLoading(true);
    try {
      const est = await aiEstimateMarket({
        municipio: selectedListing.municipio ?? "",
        barrio: selectedListing.barrio ?? "",
        precio: selectedListing.precio_venta ?? 0,
        metros: selectedListing.metros_cuadrados ?? 0,
        habitaciones: selectedListing.habitaciones ?? 0,
        estado: selectedListing.estado ?? "",
      });
      setMarket({ ...est, ai_estimated: true });
      if ((est as { verdict?: string }).verdict && !verdict) {
        setVerdict((est as { verdict?: string }).verdict ?? "");
      }
      setAiEstimated(true);
    } catch {
      alert("Error al contactar con Claude. Verifica que ANTHROPIC_API_KEY está configurada.");
    } finally {
      setAiLoading(false);
    }
  };

  const setM = (k: keyof ReportMarket, v: unknown) =>
    setMarket((m) => ({ ...m, [k]: v }));

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Nuevo análisis</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Selecciona un piso del scraper y completa los datos de mercado
        </p>
      </div>

      {/* Paso 1: selección de piso */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col gap-4">
        <p className="font-semibold text-gray-800 text-sm uppercase tracking-wide">
          1 · Seleccionar piso
        </p>
        <input
          placeholder="Buscar por municipio..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {listings.length > 0 && !selectedListing && (
          <div className="border border-gray-200 rounded-lg overflow-hidden max-h-52 overflow-y-auto">
            {listings.map((l) => (
              <button
                key={l.id}
                onClick={() => { setSelectedListing(l); setSearch(""); }}
                className="w-full text-left px-3 py-2.5 text-sm hover:bg-blue-50 border-b border-gray-100 last:border-0"
              >
                <span className="font-medium text-gray-900">{l.titulo ?? l.url}</span>
                <span className="text-gray-400 ml-2">
                  {l.barrio}, {l.municipio} · {l.precio_venta?.toLocaleString("es-ES")} €
                </span>
              </button>
            ))}
          </div>
        )}
        {selectedListing && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm flex flex-col gap-3">
            <div className="flex justify-between items-start">
              <div className="flex flex-col gap-1">
                <a
                  href={selectedListing.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-700 font-medium hover:underline break-all"
                >
                  {selectedListing.titulo ?? selectedListing.url}
                </a>
                <span className="text-gray-500 text-xs">{selectedListing.url}</span>
              </div>
              <button
                onClick={() => setSelectedListing(null)}
                className="text-blue-400 hover:text-blue-700 ml-4 flex-shrink-0"
              >
                ✕
              </button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div className="bg-white rounded-lg px-3 py-2 border border-blue-100">
                <p className="text-gray-400 uppercase tracking-wide mb-0.5">Precio</p>
                <p className="font-bold text-gray-900">{selectedListing.precio_venta?.toLocaleString("es-ES")} €</p>
              </div>
              <div className="bg-white rounded-lg px-3 py-2 border border-blue-100">
                <p className="text-gray-400 uppercase tracking-wide mb-0.5">Superficie</p>
                <p className="font-bold text-gray-900">{selectedListing.metros_cuadrados ?? "—"} m²</p>
              </div>
              <div className="bg-white rounded-lg px-3 py-2 border border-blue-100">
                <p className="text-gray-400 uppercase tracking-wide mb-0.5">Habitaciones</p>
                <p className="font-bold text-gray-900">{selectedListing.habitaciones ?? "—"} hab · {selectedListing.banos ?? "—"} baños</p>
              </div>
              <div className="bg-white rounded-lg px-3 py-2 border border-blue-100">
                <p className="text-gray-400 uppercase tracking-wide mb-0.5">€/m²</p>
                <p className="font-bold text-gray-900">
                  {selectedListing.precio_venta && selectedListing.metros_cuadrados
                    ? Math.round(selectedListing.precio_venta / selectedListing.metros_cuadrados).toLocaleString("es-ES")
                    : "—"} €
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              {selectedListing.barrio && (
                <span className="bg-white border border-blue-100 text-gray-600 px-2 py-1 rounded-full">📍 {selectedListing.barrio}, {selectedListing.municipio}</span>
              )}
              {selectedListing.estado && (
                <span className="bg-white border border-blue-100 text-gray-600 px-2 py-1 rounded-full">🏠 {selectedListing.estado}</span>
              )}
              {selectedListing.planta && (
                <span className="bg-white border border-blue-100 text-gray-600 px-2 py-1 rounded-full">🔢 Planta {selectedListing.planta}</span>
              )}
              {selectedListing.ascensor && (
                <span className="bg-white border border-blue-100 text-gray-600 px-2 py-1 rounded-full">🛗 Ascensor</span>
              )}
              {selectedListing.terraza && (
                <span className="bg-white border border-blue-100 text-gray-600 px-2 py-1 rounded-full">🌿 Terraza</span>
              )}
              {selectedListing.garaje && (
                <span className="bg-white border border-blue-100 text-gray-600 px-2 py-1 rounded-full">🚗 Garaje</span>
              )}
              {selectedListing.cee && (
                <span className="bg-white border border-blue-100 text-gray-600 px-2 py-1 rounded-full">⚡ CEE {selectedListing.cee}</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Paso 2: datos de mercado */}
      {selectedListing && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <p className="font-semibold text-gray-800 text-sm uppercase tracking-wide">
              2 · Datos de mercado
            </p>
            <button
              onClick={handleAiEstimate}
              disabled={aiLoading}
              className="text-xs bg-purple-600 text-white px-3 py-1.5 rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
            >
              {aiLoading ? "Estimando..." : "✨ Estimar con IA"}
            </button>
          </div>
          {aiEstimated && (
            <p className="text-xs text-purple-600 bg-purple-50 px-3 py-1.5 rounded-lg">
              Datos pre-rellenados por Claude — revisa y ajusta si es necesario
            </p>
          )}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {([
              ["precio_m2_zona_min", "€/m² zona min"],
              ["precio_m2_zona_medio", "€/m² zona medio"],
              ["precio_m2_zona_max", "€/m² zona max"],
              ["alquiler_estimado_mes", "Alquiler estimado (€/mes)"],
              ["rentabilidad_bruta", "Rentabilidad bruta (%)"],
              ["rentabilidad_neta", "Rentabilidad neta (%)"],
              ["rentabilidad_bruta_media_zona", "Rent. bruta media zona (%)"],
              ["rentabilidad_neta_media_zona", "Rent. neta media zona (%)"],
              ["dias_hasta_alquiler", "Días hasta alquiler"],
            ] as [keyof ReportMarket, string][]).map(([k, label]) => (
              <div key={k} className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-gray-600">{label}</label>
                <input
                  type="number"
                  value={(market[k] as number) || ""}
                  onChange={(e) => setM(k, e.target.value ? Number(e.target.value) : 0)}
                  className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            ))}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-gray-600">Demanda alquiler</label>
              <select
                value={market.demanda_alquiler}
                onChange={(e) => setM("demanda_alquiler", e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="muy_alta">Muy alta</option>
                <option value="alta">Alta</option>
                <option value="media">Media</option>
                <option value="baja">Baja</option>
              </select>
            </div>
          </div>

          {/* Veredicto */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-gray-600">Veredicto (2 frases)</label>
            <textarea
              rows={3}
              value={verdict}
              onChange={(e) => setVerdict(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder="Descripción general de la oportunidad..."
            />
          </div>

          {/* Scores */}
          <p className="font-semibold text-gray-700 text-xs uppercase tracking-wide mt-2">
            Puntuaciones (0–100)
          </p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {([
              ["global", "Global"], ["precio", "Precio"],
              ["rentabilidad", "Rentab."], ["edificio", "Edificio"],
              ["vecindario", "Vecindario"],
            ] as [keyof ReportScores, string][]).map(([k, label]) => (
              <div key={k} className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">{label}</label>
                <input
                  type="number" min={0} max={100}
                  value={(scores[k] as number) || ""}
                  onChange={(e) =>
                    setScores((s) => ({ ...s, [k]: e.target.value ? Number(e.target.value) : 0 }))
                  }
                  className="border border-gray-300 rounded-lg px-2 py-2 text-sm text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {selectedListing && (
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="self-start bg-blue-600 text-white font-medium text-sm px-6 py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {saveMutation.isPending ? "Guardando..." : "Guardar informe"}
        </button>
      )}

      {saveMutation.isError && (
        <p className="text-sm text-red-600">
          Error al guardar: {(saveMutation.error as Error).message}
        </p>
      )}
    </div>
  );
}
