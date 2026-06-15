import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import type { Listing, Report } from "../types";
import { createManualListing, fetchFuentes, fetchReports } from "../services/api";
import type { ManualListingIn } from "../services/api";

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

const CONDITIONS: [string, string][] = [
  ["obra_nueva", "Nuevo"],
  ["listo_para_usar", "Listo para usar"],
  ["buen_estado", "Usado pero bien"],
  ["reforma_leve", "Reforma leve necesaria"],
  ["reforma_integral", "Reforma Integral / A reformar"],
  ["reforma_estructural", "Reforma estructural necesaria"],
];

const OCUPACION_OPTIONS: [string, string][] = [
  ["libre", "Libre / Desocupado"],
  ["ocupado", "Ocupado"],
  ["alquilado", "Alquilado"],
  ["nuda_propiedad", "Nuda propiedad"],
];

const SITUACION_LEGAL_OPTIONS: [string, string][] = [
  ["libre_cargas", "Libre de cargas"],
  ["con_hipoteca", "Con hipoteca"],
  ["en_construccion", "En construcción"],
  ["renta_antigua", "Renta antigua"],
  ["vpo", "VPO / Protección oficial"],
  ["subasta", "En subasta"],
  ["litigio", "En litigio"],
  ["herencia", "Herencia / En trámite"],
];

const CEE_OPTIONS = ["A", "B", "C", "D", "E", "F", "G"];

function listingToForm(l: Listing): ManualListingIn {
  return {
    url: l.url,
    fuente: l.fuente,
    titulo: l.titulo,
    precio_venta: l.precio_venta,
    metros_cuadrados: l.metros_cuadrados,
    habitaciones: l.habitaciones,
    banos: l.banos,
    planta: l.planta,
    municipio: l.municipio,
    barrio: l.barrio,
    provincia: l.provincia,
    condition: l.condition,
    ocupacion: l.ocupacion,
    situacion_legal: l.situacion_legal,
    ascensor: l.ascensor,
    terraza: l.terraza,
    garaje: l.garaje,
    certificado_energetico: l.cee,
    alquiler_estimado: l.alquiler_estimado,
    precio_zona_m2: l.precio_zona_m2,
    balcon: l.balcon,
    trastero: l.trastero,
    armarios_empotrados: l.armarios_empotrados,
    aire_acondicionado: l.aire_acondicionado,
    calefaccion: l.calefaccion,
    cocina_equipada: l.cocina_equipada,
    amueblado: l.amueblado,
    exterior: l.exterior,
    portero: l.portero,
    puerta_blindada: l.puerta_blindada,
    doble_acristalamiento: l.doble_acristalamiento,
    adaptado_movilidad: l.adaptado_movilidad,
    jardin: l.jardin,
    piscina: l.piscina,
    piscina_comunitaria: l.piscina_comunitaria,
    zonas_verdes_comunitarias: l.zonas_verdes_comunitarias,
    vigilancia: l.vigilancia,
    garaje_incluido: l.garaje_incluido,
    num_plazas_garaje: l.num_plazas_garaje,
  };
}

function EyeIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function ExternalLinkIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function DocumentIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  );
}

interface DrawerProps {
  listing: Listing;
  onClose: () => void;
}

function ListingDrawer({ listing, onClose }: DrawerProps) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ManualListingIn>(() => listingToForm(listing));
  const [saved, setSaved] = useState(false);

  const fuentesQuery = useQuery({ queryKey: ["fuentes"], queryFn: () => fetchFuentes() });
  const fuentes = fuentesQuery.data ?? [];

  const set = (k: keyof ManualListingIn, v: unknown) =>
    setForm((f) => ({ ...f, [k]: v === "" ? undefined : v }));

  const mutation = useMutation({
    mutationFn: () => createManualListing(form),
    onSuccess: () => {
      setSaved(true);
      queryClient.invalidateQueries({ queryKey: ["listings"] });
      setTimeout(() => setSaved(false), 3000);
    },
  });

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />
      <div className="fixed top-0 right-0 h-full w-1/2 bg-white shadow-2xl z-50 flex flex-col overflow-hidden">

        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-200 bg-gray-50 flex-shrink-0">
          <div className="min-w-0 mr-4">
            <h2 className="text-base font-semibold text-gray-800 truncate">
              {listing.titulo ?? "Sin título"}
            </h2>
            <a
              href={listing.url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-blue-500 hover:underline truncate block mt-0.5"
            >
              {listing.url}
            </a>
          </div>
          <button
            onClick={onClose}
            className="flex-shrink-0 p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-200 transition-colors"
          >
            <XIcon />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <form
            id="drawer-form"
            onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}
            className="flex flex-col gap-5"
          >
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-gray-700">URL</label>
                <input
                  type="url"
                  value={form.url}
                  readOnly
                  className="border border-gray-200 rounded-lg px-3 py-2.5 text-sm bg-gray-50 text-gray-400 cursor-not-allowed"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-gray-700">Fuente</label>
                <select
                  value={form.fuente}
                  onChange={(e) => set("fuente", e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— seleccionar —</option>
                  {fuentes.map((f) => <option key={f.id} value={f.id}>{f.nombre}</option>)}
                </select>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-700">Título</label>
              <input
                placeholder="Piso en venta en..."
                value={form.titulo ?? ""}
                onChange={(e) => set("titulo", e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              {(
                [
                  ["precio_venta", "Precio venta (€)", "250000"],
                  ["metros_cuadrados", "M²", "80"],
                  ["habitaciones", "Habitaciones", "3"],
                  ["banos", "Baños", "2"],
                ] as [keyof ManualListingIn, string, string][]
              ).map(([k, label, ph]) => (
                <div key={k} className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium text-gray-700">{label}</label>
                  <input
                    type="number"
                    min={0}
                    placeholder={ph}
                    value={(form[k] as number) ?? ""}
                    onChange={(e) => set(k, e.target.value ? Number(e.target.value) : undefined)}
                    className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ))}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-gray-700">Planta</label>
                <input
                  type="text"
                  placeholder="ej: 3, Bajo, Ático"
                  value={form.planta ?? ""}
                  onChange={(e) => set("planta", e.target.value || undefined)}
                  className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              {(
                [
                  ["municipio", "Municipio", "Barcelona"],
                  ["barrio", "Barrio", "Eixample"],
                  ["provincia", "Provincia", "Barcelona"],
                ] as [keyof ManualListingIn, string, string][]
              ).map(([k, label, ph]) => (
                <div key={k} className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium text-gray-700">{label}</label>
                  <input
                    placeholder={ph}
                    value={(form[k] as string) ?? ""}
                    onChange={(e) => set(k, e.target.value)}
                    className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ))}
            </div>

            {/* Clasificación */}
            <div className="grid grid-cols-1 gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-gray-700">Condición</label>
                <select
                  value={form.condition ?? ""}
                  onChange={(e) => set("condition", e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— sin especificar —</option>
                  {CONDITIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-gray-700">Ocupación</label>
                <select
                  value={form.ocupacion ?? ""}
                  onChange={(e) => set("ocupacion", e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— sin especificar —</option>
                  {OCUPACION_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-gray-700">Situación legal</label>
                <select
                  value={form.situacion_legal ?? ""}
                  onChange={(e) => set("situacion_legal", e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— sin especificar —</option>
                  {SITUACION_LEGAL_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-gray-700">CEE</label>
                <select
                  value={form.certificado_energetico ?? ""}
                  onChange={(e) => set("certificado_energetico", e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">—</option>
                  {CEE_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-gray-700">Alquiler est. (€/mes)</label>
                <input
                  type="number"
                  min={0}
                  placeholder="1200"
                  value={form.alquiler_estimado ?? ""}
                  onChange={(e) => set("alquiler_estimado", e.target.value ? Number(e.target.value) : undefined)}
                  className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-gray-700">Precio zona (€/m²)</label>
                <input
                  type="number"
                  min={0}
                  placeholder="3500"
                  value={form.precio_zona_m2 ?? ""}
                  onChange={(e) => set("precio_zona_m2", e.target.value ? Number(e.target.value) : undefined)}
                  className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Características del edificio */}
            <div className="flex flex-wrap gap-4">
              {(
                [
                  ["ascensor", "Ascensor"], ["terraza", "Terraza"], ["garaje", "Garaje"],
                  ["exterior", "Exterior"], ["portero", "Portero"],
                  ["puerta_blindada", "Puerta blindada"], ["doble_acristalamiento", "Doble acristalamiento"],
                  ["adaptado_movilidad", "Adaptado movilidad"],
                ] as [keyof ManualListingIn, string][]
              ).map(([k, label]) => (
                <label key={k} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={Boolean(form[k])}
                    onChange={(e) => set(k, e.target.checked ? true : undefined)}
                    className="w-4 h-4 accent-blue-600"
                  />
                  {label}
                </label>
              ))}
            </div>

            {/* Amenidades interiores */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Interior</p>
              <div className="flex flex-wrap gap-4">
                {(
                  [
                    ["balcon", "Balcón"], ["trastero", "Trastero"],
                    ["armarios_empotrados", "Armarios empotrados"],
                    ["aire_acondicionado", "Aire acondicionado"],
                    ["calefaccion", "Calefacción"], ["cocina_equipada", "Cocina equipada"],
                    ["amueblado", "Amueblado"],
                  ] as [keyof ManualListingIn, string][]
                ).map(([k, label]) => (
                  <label key={k} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={Boolean(form[k])}
                      onChange={(e) => set(k, e.target.checked ? true : undefined)}
                      className="w-4 h-4 accent-blue-600"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>

            {/* Zonas comunes */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Zonas comunes</p>
              <div className="flex flex-wrap gap-4">
                {(
                  [
                    ["jardin", "Jardín"], ["piscina", "Piscina privada"],
                    ["piscina_comunitaria", "Piscina comunitaria"],
                    ["zonas_verdes_comunitarias", "Zonas verdes"],
                    ["vigilancia", "Vigilancia"],
                    ["garaje_incluido", "Garaje incluido en precio"],
                  ] as [keyof ManualListingIn, string][]
                ).map(([k, label]) => (
                  <label key={k} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={Boolean(form[k])}
                      onChange={(e) => set(k, e.target.checked ? true : undefined)}
                      className="w-4 h-4 accent-blue-600"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 p-4 bg-gray-50 rounded-xl border border-gray-100 text-sm">
              <div>
                <p className="text-xs text-gray-400 mb-0.5">Score</p>
                <p className="font-medium text-gray-700">{listing.score ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-0.5">Rent. bruta</p>
                <p className="font-medium text-gray-700">
                  {listing.rentabilidad_bruta != null ? `${listing.rentabilidad_bruta}%` : "—"}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-0.5">Días en mercado</p>
                <p className="font-medium text-gray-700">{listing.dias_en_mercado ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-0.5">€/m²</p>
                <p className="font-medium text-gray-700">
                  {listing.precio_m2 != null ? `${listing.precio_m2.toLocaleString("es-ES")} €/m²` : "—"}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-0.5">Bajada precio</p>
                <p className="font-medium text-gray-700">{listing.bajada_precio ? "Sí" : "No"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-0.5">1ª detección</p>
                <p className="font-medium text-gray-700">
                  {listing.primera_deteccion
                    ? new Date(listing.primera_deteccion).toLocaleDateString("es-ES")
                    : "—"}
                </p>
              </div>
            </div>
          </form>
        </div>

        <div className="flex-shrink-0 px-6 py-4 border-t border-gray-200 bg-white flex items-center gap-3">
          {saved && (
            <span className="text-sm text-green-600 font-medium">Guardado correctamente</span>
          )}
          {mutation.isError && (
            <span className="text-sm text-red-600">Error al guardar</span>
          )}
          <div className="ml-auto flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Cerrar
            </button>
            <button
              type="submit"
              form="drawer-form"
              disabled={mutation.isPending}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {mutation.isPending ? "Guardando…" : "Guardar cambios"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

export default function ListingsTable({ listings, isLoading }: Props) {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);

  const { data: reports = [] } = useQuery<Report[]>({
    queryKey: ["reports"],
    queryFn: fetchReports,
    staleTime: 60_000,
  });

  const reportByPropertyId = new Map<string, string>(
    reports
      .filter((r) => r.property_id)
      .map((r) => [r.property_id!, r.id])
  );

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
    <>
      {selectedListing && (
        <ListingDrawer
          listing={selectedListing}
          onClose={() => setSelectedListing(null)}
        />
      )}

      <div className="flex flex-col gap-3">
        <div className="overflow-x-auto rounded-xl border border-gray-200 shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Acciones</th>
                <th className="px-4 py-3 text-left">Score</th>
                <th className="px-4 py-3 text-left">Portal</th>
                <th className="px-4 py-3 text-left">Título</th>
                <th className="px-4 py-3 text-left">Precio</th>
                <th className="px-4 py-3 text-left">€/m²</th>
                <th className="px-4 py-3 text-left">m²</th>
                <th className="px-4 py-3 text-left">Hab.</th>
                <th className="px-4 py-3 text-left">Planta</th>
                <th className="px-4 py-3 text-left">Municipio</th>
                <th className="px-4 py-3 text-left">Barrio</th>
                <th className="px-4 py-3 text-left">Rent. bruta</th>
                <th className="px-4 py-3 text-left">Bajada</th>
                <th className="px-4 py-3 text-left">Días</th>
                <th className="px-4 py-3 text-left">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {paginated.map((l, i) => {
                const reportId = l.id ? reportByPropertyId.get(l.id) : undefined;
                const accionesTd = (
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setSelectedListing(l)}
                        title="Ver y editar"
                        className="p-1.5 rounded-md text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                      >
                        <EyeIcon />
                      </button>
                      <a
                        href={l.url}
                        target="_blank"
                        rel="noreferrer"
                        title="Abrir enlace"
                        className="p-1.5 rounded-md text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                      >
                        <ExternalLinkIcon />
                      </a>
                      {reportId ? (
                        <button
                          onClick={() => navigate(`/informes/${reportId}`, { state: { from: "/" } })}
                          title="Ver informe"
                          className="p-1.5 rounded-md text-blue-600 hover:text-blue-800 hover:bg-blue-50 transition-colors"
                        >
                          <DocumentIcon />
                        </button>
                      ) : (
                        <button
                          onClick={() => navigate("/informes/nuevo", { state: { listing: l } })}
                          title="Crear informe"
                          className="p-1.5 rounded-md text-red-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                        >
                          <DocumentIcon />
                        </button>
                      )}
                    </div>
                  </td>
                );
                return (
                  <tr key={l.id ?? i} className="bg-white hover:bg-gray-50 transition-colors">
                    {accionesTd}
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
                    <td className="px-4 py-3 font-medium text-gray-800 whitespace-nowrap">{fmt(l.precio_venta)}</td>
                    <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                      {l.precio_m2 != null ? l.precio_m2.toLocaleString("es-ES") + " €/m²" : "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{l.metros_cuadrados ?? "—"}</td>
                    <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{l.habitaciones ?? "—"}</td>
                    <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                      {l.tipo_propiedad === "Casa"
                        ? <span className="text-amber-700 font-medium">Casa</span>
                        : l.planta ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{l.municipio ?? "—"}</td>
                    <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{l.barrio ?? "—"}</td>
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
                    {accionesTd}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

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
    </>
  );
}
